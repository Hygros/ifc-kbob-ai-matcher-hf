import sqlite3
from typing import List
import torch
import os
from sentence_transformers import SentenceTransformer, SimilarityFunction

# --- Configuration ---
DATABASE_PATH = r"C:\Users\wpx619\AAA_Python_MTH\Ökobilanzdaten.sqlite3"
TABLE_NAME = "Oekobilanzdaten"
COLUMN_MATERIAL = "Material"
MODEL_NAME = "all-MiniLM-L6-v2"  # Change model name here
MODEL_DIRECTORY = f"./models/{MODEL_NAME}"
TOP_K_RESULTS = 10
SIMILARITY_FUNCTION = SimilarityFunction.COSINE  # Alternatives: DOT_PRODUCT, EUCLIDEAN, MANHATTAN

SBERT_DEVICE = os.environ.get("SBERT_DEVICE", "").strip().lower()

EXAMPLE_QUERIES = [
    "IfcPile BORED Betonpfahl Beton Pfahlreihe Süd 900 Ortbeton",
    "Ortbeton IfcPile BORED Betonpfahl Beton Pfahlreihe Süd 900",
    "900 Ortbeton IfcPile BORED Betonpfahl Beton Pfahlreihe Süd",
    "Pfahlreihe Süd 900 Ortbeton IfcPile BORED Betonpfahl Beton",
    "Beton Pfahlreihe Süd 900 Ortbeton IfcPile BORED Betonpfahl",
    "Betonpfahl Beton Pfahlreihe Süd 900 Ortbeton IfcPile BORED",
    "BORED Betonpfahl Beton Pfahlreihe Süd 900 Ortbeton IfcPile",
    "IfcPile ; BORED ; Betonpfahl ; Beton ; Pfahlreihe Süd ; 900 ; Ortbeton",
    "IfcPile , BORED , Betonpfahl , Beton , Pfahlreihe Süd , 900 , Ortbeton",
    "Entity: IfcPile PredefinedType: BORED Name: Betonpfahl Material: Beton Beschrieb: Pfahlreihe Süd Durchmesser: 900 CastingMethod: Ortbeton",

]

# --- Database Query ---
def fetch_materials_from_db(connection: sqlite3.Connection) -> List[str]:
    cursor = connection.cursor()
    cursor.execute(f"SELECT {COLUMN_MATERIAL} FROM {TABLE_NAME}")
    return [row[0] for row in cursor.fetchall()]

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

# --- Main Function ---
def find_most_similar_materials():
    print(f"Using model: {MODEL_NAME}")
    with sqlite3.connect(DATABASE_PATH) as connection:
        materials = fetch_materials_from_db(connection)
    print(f"Number of KBOB entries: {len(materials)}")

    model = load_or_save_model()
    model.similarity_fn_name = SIMILARITY_FUNCTION

    queries = EXAMPLE_QUERIES
    materials_list = materials

    query_embeddings = model.encode(queries)
    material_embeddings = model.encode(materials_list)

    similarities = model.similarity(query_embeddings, material_embeddings)

    for query_index, query_text in enumerate(queries):
        print(f"Query: {query_text}\n")
        similarity_scores = similarities[query_index]
        num_results = min(TOP_K_RESULTS, len(materials_list))
        best_indices = list(similarity_scores.argsort())[::-1][:num_results]
        for rank, material_index in enumerate(best_indices, start=1):
            print(f"  {rank}. {materials_list[material_index]} (Score={similarity_scores[material_index]:.3f})")
        print("\n")

if __name__ == "__main__":
    find_most_similar_materials()
