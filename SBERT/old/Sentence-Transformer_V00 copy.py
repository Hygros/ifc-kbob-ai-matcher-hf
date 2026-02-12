import sqlite3
from typing import List, Tuple
import numpy
import torch
import os
from sentence_transformers import SentenceTransformer

# --- Konfiguration ---
DB_PATH = r"C:\Users\wpx619\AAA_Python_MTH\Ökobilanzdaten.sqlite3"
MATERIALS_TABLE = "Oekobilanzdaten"
MATERIAL_COL = "Material"
MODEL_NAME = "all-MiniLM-L6-v2"  # change model here only
MODEL_DIR = f"./models/{MODEL_NAME}"
TOP_K = 10

example_queries = [
    "IfcPile ; BORED ; Betonpfahl ; Beton ; Pfahlreihe Süd ; 900 ; Ortbeton",
]


# --- Materialien aus DB laden ---
def fetch_materials(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"SELECT {MATERIAL_COL} FROM {MATERIALS_TABLE}")
    return [row[0] for row in cur.fetchall()]

# --- Embeddings berechnen ---
def embed_texts(texts: List[str], model: SentenceTransformer) -> numpy.ndarray:
    # Nur eine Normalisierung, da normalize_embeddings=True bereits normalisiert
    return model.encode(texts, batch_size=64, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True)

# --- Top-K Ranking ---
def rank_top_k(queries: List[str], materials: List[str], top_k: int) -> List[List[Tuple[str, float]]]:
    model = load_or_get_local_model()
    mat_emb = embed_texts(materials, model)
    qry_emb = embed_texts(queries, model)
    sim = numpy.dot(qry_emb, mat_emb.T)  # Cosine Similarity
    results = []
    for i in range(len(queries)):
        idx = numpy.argsort(-sim[i])[:top_k]
        results.append([(materials[j], float(sim[i, j])) for j in idx])
    return results

def load_or_get_local_model() -> SentenceTransformer:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if os.path.isdir(MODEL_DIR) and os.listdir(MODEL_DIR):
        return SentenceTransformer(MODEL_DIR, device=device)
    model = SentenceTransformer(MODEL_NAME, device=device)
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(MODEL_DIR)
    return model

def main():
    print(f"Verwendetes Modell: {MODEL_NAME}")
    with sqlite3.connect(DB_PATH) as conn:
        materials = fetch_materials(conn)
    print(f"Anzahl KBOB-Einträge: {len(materials)}")

    matches = rank_top_k(example_queries, materials, TOP_K)
    for q, hits in zip(example_queries, matches):
        print(f"Query: {q}\n")
        for rank, (mat, score) in enumerate(hits, start=1):
            print(f"  {rank}. {mat} (Score={score:.4f})")

if __name__ == "__main__":
    main()
