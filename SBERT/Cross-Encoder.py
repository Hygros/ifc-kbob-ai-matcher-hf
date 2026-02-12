import sqlite3
from typing import List, Tuple
import numpy as np
import torch
import os
from sentence_transformers import CrossEncoder

# --- Konfiguration ---
DB_PATH = r"C:\Users\wpx619\AAA_Python_MTH\Ökobilanzdaten.sqlite3"
MATERIALS_TABLE = "Oekobilanzdaten"
MATERIAL_COL = "Material"
MODEL_NAME = "cross-encoder/nli-deberta-v3-base"  # change model here only
MODEL_DIR = f"./models/{MODEL_NAME}"
TOP_K = 5
USE_CUDA = True  # set False to force CPU

example_queries = [
    "Material: Beton, Element: Widerlagerwand",
    "Beton Widerlagerwand",
    "Material: Beton C30/37, Element: Fahrbahnplatte",
    "Armierungsstahl",
    "B500B",
    "Asphalt",
    "Dichtungsbahn EPDM",
    "Holz",
    "Flüssigkunststoff",
]

# --- Materialien aus DB laden ---
def fetch_materials(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"SELECT {MATERIAL_COL} FROM {MATERIALS_TABLE}")
    return [row[0] for row in cur.fetchall()]

# --- Top-K Ranking ---
def rank_top_k(queries: List[str], materials: List[str], top_k: int) -> List[List[Tuple[str, float]]]:
    model = load_or_get_local_model()
    results = []
    for q in queries:
        pairs = [(q, m) for m in materials]
        scores = model.predict(pairs)
        idx = np.argsort(-scores)[:top_k]
        results.append([(materials[i], float(scores[i])) for i in idx])
    return results

def get_device() -> str:
    if USE_CUDA:
        if torch.cuda.is_available():
            return "cuda"
        print("CUDA nicht verfügbar (falle auf CPU zurück). Prüfe Torch-Build und Treiber.")
    return "cpu"

def load_or_get_local_model() -> CrossEncoder:
    device = get_device()
    if os.path.isdir(MODEL_DIR) and os.listdir(MODEL_DIR):
        model = CrossEncoder(MODEL_DIR, device=device)
    else:
        model = CrossEncoder(MODEL_NAME, device=device)
        os.makedirs(MODEL_DIR, exist_ok=True)
        model.save(MODEL_DIR)
    print(f"Gerät verwendet: {device}")
    return model

def main():
    print(f"Verwendetes Cross-Encoder Modell: {MODEL_NAME}")
    with sqlite3.connect(DB_PATH) as conn:
        materials = fetch_materials(conn)
    print(f"Materialien geladen: {len(materials)}")

    matches = rank_top_k(example_queries, materials, TOP_K)
    for q, hits in zip(example_queries, matches):
        print(f"\nQuery: {q}")
        for rank, (mat, score) in enumerate(hits, start=1):
            print(f"  {rank}. {mat} (Score={score:.4f})")

if __name__ == "__main__":
    main()
