
# 



import sqlite3
from typing import List
import torch
import os
from sentence_transformers import SentenceTransformer, SimilarityFunction, util
import sys
import json
from pathlib import Path
from functools import lru_cache

try:
    from .batch_benchmark import recommend_batch_size
except ImportError:
    from batch_benchmark import recommend_batch_size


# --- Configuration ---
DATABASE_PATH = r"C:\Users\wpx619\AAA_Python_MTH\Ökobilanzdaten.sqlite3"
TABLE_NAME = "Oekobilanzdaten"
COLUMN_MATERIAL = "Material"
MODEL_NAME = "BAAI/bge-m3"  # Change model name here

_BASE_DIR = Path(__file__).resolve().parent

TOP_K_RESULTS = 30
SIMILARITY_FUNCTION = SimilarityFunction.COSINE  # Alternatives: DOT_PRODUCT, EUCLIDEAN, MANHATTAN

# For tiny workloads (e.g., 90 short strings), CPU is often faster overall due to CUDA init overhead.
# Override via environment variable: SBERT_DEVICE=cpu|cuda
SBERT_DEVICE = os.environ.get("SBERT_DEVICE", "").strip().lower()
CUDA_QUERY_THRESHOLD = int(os.environ.get("SBERT_CUDA_QUERY_THRESHOLD", "500"))
ENCODE_BATCH_SIZE = int(os.environ.get("SBERT_BATCH_SIZE", "64"))
NORMALIZE_EMBEDDINGS = True
AUTO_BENCH_BATCH = os.environ.get("SBERT_AUTO_BENCH_BATCH", "").strip().lower() in {"1", "true", "yes", "on"}
AUTO_HEURISTIC_BATCH = os.environ.get("SBERT_AUTO_HEURISTIC_BATCH", "1").strip().lower() in {"1", "true", "yes", "on"}
HAS_MANUAL_BATCH_SIZE = "SBERT_BATCH_SIZE" in os.environ


def resolve_runtime_device(query_count: int) -> str:
    if SBERT_DEVICE in {"cpu", "cuda"}:
        return SBERT_DEVICE
    if query_count >= CUDA_QUERY_THRESHOLD and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def resolve_heuristic_batch_size(query_count: int, device: str) -> int:
    if device == "cuda" and query_count >= 500:
        return 64
    if device == "cpu" and query_count <= 200:
        return 16
    return ENCODE_BATCH_SIZE


# --- Database Query ---
def fetch_materials_from_db(connection: sqlite3.Connection) -> List[str]:
    cursor = connection.cursor()
    cursor.execute(f"SELECT {COLUMN_MATERIAL} FROM {TABLE_NAME} WHERE {COLUMN_MATERIAL} IS NOT NULL")
    materials = [row[0] for row in cursor.fetchall() if str(row[0]).strip() != ""]
    # Deduplicate while preserving order (reduces corpus size and speeds up encoding/search)
    return list(dict.fromkeys(materials))

# --- Load or Save Model ---
def _resolve_model_name(model_name: str | None = None) -> str:
    if model_name is None:
        return MODEL_NAME
    normalized = str(model_name).strip()
    return normalized if normalized else MODEL_NAME


def _model_directory_for(model_name: str) -> str:
    return str(_BASE_DIR / "models" / model_name)


def load_or_save_model(model_name: str | None = None, device: str = "cpu") -> SentenceTransformer:
    resolved_model_name = _resolve_model_name(model_name)
    model_directory = _model_directory_for(resolved_model_name)
    if os.path.isdir(model_directory) and os.listdir(model_directory):
        return SentenceTransformer(model_directory, device=device)
    model = SentenceTransformer(resolved_model_name, device=device)
    os.makedirs(model_directory, exist_ok=True)
    model.save(model_directory)
    return model

# --- JSONL Processing ---
IFC_EXPORT_FIELDS = [
    "IfcEntity",
    "PredefinedType",
    "Name",
    "Material",
    "Description",
    "Durchmesser",
    "CastingMethod",
]

# "ExposureClass",
# "ReinforcementStrengthClass"
# "StrengthClass",
# "StructuralClass",
# "comment", (nur für Tekla 2025)



# Modell global initialisieren
_global_sbert_models: dict[tuple[str, str], SentenceTransformer] = {}


def get_global_sbert_model(model_name: str | None = None, device: str = "cpu"):
    resolved_model_name = _resolve_model_name(model_name)
    key = (resolved_model_name, device)
    if key not in _global_sbert_models:
        _global_sbert_models[key] = load_or_save_model(model_name=resolved_model_name, device=device)
        # Warmup to reduce first-call latency in interactive runs (Streamlit dev)
        with torch.inference_mode():
            _ = _global_sbert_models[key].encode(["warmup"], batch_size=1, show_progress_bar=False)
    return _global_sbert_models[key]


@lru_cache(maxsize=32)
def get_cached_corpus(
    model_name: str = MODEL_NAME,
    device: str = "cpu",
    batch_size: int = ENCODE_BATCH_SIZE,
) -> tuple[list[str], torch.Tensor]:
    """Load materials from DB and precompute embeddings once per process."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        materials = fetch_materials_from_db(connection)

    model = get_global_sbert_model(model_name=model_name, device=device)
    model.similarity_fn_name = SIMILARITY_FUNCTION

    with torch.inference_mode():
        embeddings = model.encode(
            materials,
            batch_size=batch_size,
            convert_to_tensor=True,
            normalize_embeddings=NORMALIZE_EMBEDDINGS,
            show_progress_bar=False,
        )
    return materials, embeddings

def load_ifc_jsonl_entries(jsonl_path: str) -> list:
    entries = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries

def ifc_entry_to_string(entry: dict) -> str:
    # Erzeuge String wie TXT-Export: Werte mit Leerzeichen trennen, leere Felder überspringen
    values = []
    for field in IFC_EXPORT_FIELDS:
        val = entry.get(field, "")
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val if v)
        if val is not None and str(val).strip() != "" and str(val).strip() != "NOTDEFINED" and str(val).strip() != "Undefined":
            values.append(str(val).strip())
    return " ".join(values)


def benchmark_recommend_batch_size(jsonl_path: str, model_name: str | None = None, verbose: bool = True) -> int:
    resolved_model_name = _resolve_model_name(model_name)
    entries = load_ifc_jsonl_entries(jsonl_path)
    queries = [ifc_entry_to_string(e) for e in entries]
    device = resolve_runtime_device(len(queries))
    model = get_global_sbert_model(model_name=resolved_model_name, device=device)
    return recommend_batch_size(
        queries=queries,
        device=device,
        model=model,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        default_batch_size=ENCODE_BATCH_SIZE,
        verbose=verbose,
    )


def find_most_similar_db_entries(jsonl_path: str, model_name: str | None = None):
    resolved_model_name = _resolve_model_name(model_name)
    print(f"Using model: {resolved_model_name}")
    # IFC-Export als Queries laden
    entries = load_ifc_jsonl_entries(jsonl_path)
    queries = [ifc_entry_to_string(e) for e in entries]
    query_count = len(queries)
    device = resolve_runtime_device(query_count)
    if HAS_MANUAL_BATCH_SIZE:
        selected_batch_size = ENCODE_BATCH_SIZE
        batch_mode = "manual-env"
    elif AUTO_BENCH_BATCH:
        selected_batch_size = benchmark_recommend_batch_size(jsonl_path, model_name=resolved_model_name)
        batch_mode = "auto-bench"
    elif AUTO_HEURISTIC_BATCH:
        selected_batch_size = resolve_heuristic_batch_size(query_count, device)
        batch_mode = "heuristic"
    else:
        selected_batch_size = ENCODE_BATCH_SIZE
        batch_mode = "default"
    print(f"Number of IFC queries: {query_count}")
    print(f"Runtime device: {device} (threshold={CUDA_QUERY_THRESHOLD})")
    print(f"SBERT batch size: {selected_batch_size} ({batch_mode})")

    # Load corpus (DB) once per process
    materials, material_embeddings = get_cached_corpus(
        model_name=resolved_model_name,
        device=device,
        batch_size=selected_batch_size,
    )
    print(f"Number of KBOB entries: {len(materials)}")

    model = get_global_sbert_model(model_name=resolved_model_name, device=device)
    model.similarity_fn_name = SIMILARITY_FUNCTION

    with torch.inference_mode():
        query_embeddings = model.encode(
            queries,
            batch_size=selected_batch_size,
            convert_to_tensor=True,
            normalize_embeddings=NORMALIZE_EMBEDDINGS,
            show_progress_bar=False,
        )

    hits = util.semantic_search(
        query_embeddings,
        material_embeddings,
        top_k=min(TOP_K_RESULTS, len(materials)),
    )

    for query_index, query_text in enumerate(queries):
        top = hits[query_index]
        entries[query_index]["top_k_matches"] = [
            {
                "material": materials[int(h["corpus_id"])],
                "score": round(float(h["score"]), 3),
            }
            for h in top
        ]

    print(f"Query: {query_text}")
    for rank, h in enumerate(top[:10], 1):
        mat = materials[int(h["corpus_id"])]
        score = float(h["score"])
        print(f"  {rank}. {mat} (Score={score:.3f})")
    print()

    # Überschreibe die JSONL-Datei mit den neuen Feldern
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def run_sbert_matching(jsonl_path: str, model_name: str | None = None):
    find_most_similar_db_entries(jsonl_path, model_name=model_name)


if __name__ == "__main__":
    # Erlaube Übergabe des JSONL-Pfads als Argument
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python Sentence_Transformer_V00.py <path-to-jsonl> [model-name]")
        print("  python Sentence_Transformer_V00.py --benchmark-batch <path-to-jsonl> [model-name]")
        raise SystemExit(1)

    if sys.argv[1] == "--benchmark-batch":
        if len(sys.argv) < 3:
            print("Usage: python Sentence_Transformer_V00.py --benchmark-batch <path-to-jsonl> [model-name]")
            raise SystemExit(1)
        JSONL_PATH = sys.argv[2]
        CLI_MODEL_NAME = sys.argv[3] if len(sys.argv) > 3 else None
        benchmark_recommend_batch_size(JSONL_PATH, model_name=CLI_MODEL_NAME, verbose=True)
        raise SystemExit(0)

    JSONL_PATH = sys.argv[1]
    CLI_MODEL_NAME = sys.argv[2] if len(sys.argv) > 2 else None
    run_sbert_matching(JSONL_PATH, model_name=CLI_MODEL_NAME)