import sqlite3
from typing import List
import torch
import os
from sentence_transformers import SentenceTransformer, SimilarityFunction, util
import sys
import json
from pathlib import Path
from functools import lru_cache

# --- Configuration ---
DATABASE_PATH = r"C:\Users\wpx619\AAA_Python_MTH\Ökobilanzdaten.sqlite3"
TABLE_NAME = "Oekobilanzdaten"
COLUMN_MATERIAL = "Material"
MODEL_NAME = "all-MiniLM-L6-v2"  # Change model name here

# Make model path independent from the current working directory (important when called from Streamlit/subprocess)
_BASE_DIR = Path(__file__).resolve().parent
MODEL_DIRECTORY = str(_BASE_DIR / "models" / MODEL_NAME)

TOP_K_RESULTS = 30
SIMILARITY_FUNCTION = SimilarityFunction.COSINE  # Alternatives: DOT_PRODUCT, EUCLIDEAN, MANHATTAN

# For tiny workloads (e.g., 90 short strings), CPU is often faster overall due to CUDA init overhead.
# Override via environment variable: SBERT_DEVICE=cpu|cuda
SBERT_DEVICE = os.environ.get("SBERT_DEVICE", "").strip().lower()
ENCODE_BATCH_SIZE = int(os.environ.get("SBERT_BATCH_SIZE", "64"))
NORMALIZE_EMBEDDINGS = True


# --- Database Query ---
def fetch_materials_from_db(connection: sqlite3.Connection) -> List[str]:
    cursor = connection.cursor()
    cursor.execute(f"SELECT {COLUMN_MATERIAL} FROM {TABLE_NAME} WHERE {COLUMN_MATERIAL} IS NOT NULL")
    materials = [row[0] for row in cursor.fetchall() if str(row[0]).strip() != ""]
    # Deduplicate while preserving order (reduces corpus size and speeds up encoding/search)
    return list(dict.fromkeys(materials))

# --- Load or Save Model ---
def load_or_save_model() -> SentenceTransformer:
    if SBERT_DEVICE in {"cpu", "cuda"}:
        device = SBERT_DEVICE
    else:
        device = "cpu" if torch.cuda.is_available() else "cpu"
    if os.path.isdir(MODEL_DIRECTORY) and os.listdir(MODEL_DIRECTORY):
        return SentenceTransformer(MODEL_DIRECTORY, device=device)
    model = SentenceTransformer(MODEL_NAME, device=device)
    os.makedirs(MODEL_DIRECTORY, exist_ok=True)
    model.save(MODEL_DIRECTORY)
    return model

# --- JSONL Processing ---
IFC_EXPORT_FIELDS = [
    "IfcEntity",
    "PredefinedType",
    "Name",
    "Material",
    "Description",
    "comment",
    "Durchmesser",
    "CastingMethod",
    "StructuralClass",
    "StrengthClass",
    "ReinforcementStrengthClass"
]
# "ExposureClass",
#

# Modell global initialisieren
_global_sbert_model = None
def get_global_sbert_model():
    global _global_sbert_model
    if _global_sbert_model is None:
        _global_sbert_model = load_or_save_model()
        # Warmup to reduce first-call latency in interactive runs (Streamlit dev)
        with torch.inference_mode():
            _ = _global_sbert_model.encode(["warmup"], batch_size=1, show_progress_bar=False)
    return _global_sbert_model


@lru_cache(maxsize=1)
def get_cached_corpus() -> tuple[list[str], torch.Tensor]:
    """Load materials from DB and precompute embeddings once per process."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        materials = fetch_materials_from_db(connection)

    model = get_global_sbert_model()
    model.similarity_fn_name = SIMILARITY_FUNCTION

    with torch.inference_mode():
        embeddings = model.encode(
            materials,
            batch_size=ENCODE_BATCH_SIZE,
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


def find_most_similar_db_entries(jsonl_path: str):
    print(f"Using model: {MODEL_NAME}")
    # IFC-Export als Queries laden
    entries = load_ifc_jsonl_entries(jsonl_path)
    queries = [ifc_entry_to_string(e) for e in entries]
    print(f"Number of IFC queries: {len(queries)}")

    # Load corpus (DB) once per process
    materials, material_embeddings = get_cached_corpus()
    print(f"Number of KBOB entries: {len(materials)}")

    model = get_global_sbert_model()
    model.similarity_fn_name = SIMILARITY_FUNCTION

    with torch.inference_mode():
        query_embeddings = model.encode(
            queries,
            batch_size=ENCODE_BATCH_SIZE,
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

def run_sbert_matching(jsonl_path):
    find_most_similar_db_entries(jsonl_path)


if __name__ == "__main__":
    # Erlaube Übergabe des JSONL-Pfads als Argument
    JSONL_PATH = sys.argv[1]
    # Modell nur einmal laden und global halten
    _global_sbert_model = load_or_save_model()
    run_sbert_matching(JSONL_PATH)