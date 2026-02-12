
import sqlite3
from typing import List
import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score

# --- Konfiguration ---
DB_PATH = r"C:\\Users\\wpx619\\AAA_Python_MTH\\Ökobilanzdaten.sqlite3"
MATERIALS_TABLE = "Oekobilanzdaten"
MATERIAL_COL = "Material"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MODEL_DIR = f"./models/{MODEL_NAME}"
TOP_K = 1

example_queries = [
    "IfcColumn | COLUMN | S235JR | NEW",
    "IfcWall | Wand | Beton, XPS, Gipsputz | NEW",
]

expected_labels = [
    "Armierungsstahl",
    "Armierungsstahl",
    "Gussasphalt",
    "Dichtungsbahn Gummi (EPDM)",
    "Konstruktionsvollholz",
    "2K-Fliessbelag Industrie (Epoxidharz)",
    "Tiefbaubeton",
    "Tiefbaubeton",
    "Tiefbaubeton",
    "Tiefbaubeton"
]

# --- Materialien aus DB laden ---
def fetch_materials(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"SELECT {MATERIAL_COL} FROM {MATERIALS_TABLE}")
    return [row[0] for row in cur.fetchall()]

# --- Embeddings berechnen ---
def embed_texts(texts: List[str], model: SentenceTransformer) -> np.ndarray:
    emb = model.encode(texts, batch_size=64, convert_to_numpy=True, show_progress_bar=True)
    return emb / np.linalg.norm(emb, axis=1, keepdims=True)

# --- Cosine Similarity ---
def cosine_similarity_matrix(qry_emb: np.ndarray, mat_emb: np.ndarray) -> np.ndarray:
    return np.dot(qry_emb, mat_emb.T)

# --- Ranking mit Score-Ausgabe ---
def rank_top_k(queries: List[str], materials: List[str], top_k: int):
    model = load_or_get_local_model()
    mat_emb = embed_texts(materials, model)
    qry_emb = embed_texts(queries, model)
    sim = cosine_similarity_matrix(qry_emb, mat_emb)
    predictions = []
    scores = []
    for i in range(len(queries)):
        idx = np.argsort(-sim[i])[:top_k]
        predictions.append(materials[idx[0]])
        scores.append(sim[i, idx[0]])
        print(f"\nQuery: {queries[i]}")
        print(f"  Prediction: {materials[idx[0]]} (Score={sim[i, idx[0]]:.4f})")
    return predictions, scores

def load_or_get_local_model() -> SentenceTransformer:
    if os.path.isdir(MODEL_DIR) and os.listdir(MODEL_DIR):
        return SentenceTransformer(MODEL_DIR, device="cuda")
    model = SentenceTransformer(MODEL_NAME, device="cuda")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(MODEL_DIR)
    return model

def main():
    print(f"Verwendetes Modell: {MODEL_NAME}")
    with sqlite3.connect(DB_PATH) as conn:
        materials = fetch_materials(conn)
    print(f"Materialien geladen: {len(materials)}")

    predictions, scores = rank_top_k(example_queries, materials, TOP_K)


    # --- Confusion-Matrix mit kombinierten Labels ---
    combined_labels = sorted(set(expected_labels) | set(predictions))  # Vereinigung der Labels
    cm = confusion_matrix(expected_labels, predictions, labels=combined_labels)

    # Normalisierung (zeilenweise)
    row_sums = cm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    cm_normalized = cm.astype(float) / row_sums
    cm_percent = cm_normalized * 100

    # Heatmap mit Prozentwerten
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.heatmap(cm_percent, annot=True, fmt=".1f", cmap="Blues",
                xticklabels=combined_labels, yticklabels=combined_labels,
                cbar_kws={'label': 'Prozent'}, vmin=0, vmax=100)

    plt.xticks(rotation=90, fontsize=6)
    plt.yticks(rotation=0, fontsize=6)
    plt.title("Normalisierte Confusion-Matrix in Prozent (kombinierte Labels)", fontsize=12)
    plt.tight_layout()
    plt.savefig("confusion_matrix_combined_labels.png")
    print("Heatmap gespeichert als confusion_matrix_combined_labels.png")


if __name__ == "__main__":
    main()
