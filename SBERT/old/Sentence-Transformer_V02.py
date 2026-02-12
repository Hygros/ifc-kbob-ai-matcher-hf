import sqlite3
from typing import List, Tuple
import numpy as np
import os
from sentence_transformers import SentenceTransformer

# --- Konfiguration ---
DB_PATH = r"C:\Users\wpx619\AAA_Python_MTH\Ökobilanzdaten.sqlite3"
MATERIALS_TABLE = "Oekobilanzdaten"
MATERIAL_COL = "Material"
MODEL_NAME = "all-mpnet-base-v2"  # change model here only
MODEL_DIR = f"./models/{MODEL_NAME}"
TOP_K = 5

# Attribution settings
EXPLAIN = True
EXPLAIN_TOP_MATERIALS = 1     # explain the top-N matched materials per query
EXPLAIN_TOP_PHRASES = 5       # show the top-N most influential phrases
EXPLAIN_MAX_NGRAM = 2         # max n-gram size to remove during occlusion

example_queries = [
    "IfcPile ; BORED ; Betonpfahl ; Beton ; Pfahlreihe Süd ; 900 ; Ortbeton",
]



# --- Materialien aus DB laden ---
def fetch_materials(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"SELECT {MATERIAL_COL} FROM {MATERIALS_TABLE}")
    return [row[0] for row in cur.fetchall()]

# --- Embeddings berechnen ---
def embed_texts(texts: List[str], model: SentenceTransformer) -> np.ndarray:
    emb = model.encode(texts, batch_size=64, convert_to_numpy=True, show_progress_bar=True, normalize_embeddings=True)
    return emb / np.linalg.norm(emb, axis=1, keepdims=True)  # Normalisierung für Cosine Similarity

# --- Top-K Ranking ---
def rank_top_k(queries: List[str], materials: List[str], top_k: int) -> List[List[Tuple[str, float]]]:
    model = load_or_get_local_model()
    mat_emb = embed_texts(materials, model)
    qry_emb = embed_texts(queries, model)
    sim = np.dot(qry_emb, mat_emb.T)  # Cosine Similarity
    results = []
    for i in range(len(queries)):
        idx = np.argsort(-sim[i])[:top_k]
        results.append([(materials[j], float(sim[i, j])) for j in idx])
    return results

def explain_influence_occlusion(
    query: str,
    materials: List[str],
    top_materials: int = 1,
    top_phrases: int = 5,
    max_ngram: int = 2
) -> List[Tuple[str, List[Tuple[str, float]]]]:
    """
    For the given query, returns [(material_name, [(phrase, delta_score), ...]), ...]
    delta_score is the drop in cosine similarity when the phrase is removed.
    """
    model = load_or_get_local_model()
    mat_emb = embed_texts(materials, model)

    # Baseline similarities to all materials
    q_emb = embed_texts([query], model)[0]                       # (d,)
    sims_all = np.dot(mat_emb, q_emb)                            # (num_materials,)
    top_idx = np.argsort(-sims_all)[:top_materials]
    baseline = sims_all[top_idx]                                 # (top_materials,)

    # Build occlusion variants (remove 1- and up to max_ngram-grams)
    tokens = query.split()
    variants: List[str] = []
    phrases: List[str] = []
    for k in range(1, max_ngram + 1):
        for i in range(len(tokens) - k + 1):
            phrase = " ".join(tokens[i:i+k])
            remaining = tokens[:i] + tokens[i+k:]
            if not remaining:  # skip empty query
                continue
            variants.append(" ".join(remaining))
            phrases.append(phrase)

    if not variants:
        return [(materials[i], []) for i in top_idx]

    # Batch-encode all variants once
    var_emb = embed_texts(variants, model)                        # (V, d)

    # Compute similarity drops per top material
    sims_var = np.dot(mat_emb[top_idx], var_emb.T)                # (top_materials, V)
    deltas = (baseline[:, None] - sims_var)                       # positive => removal hurt score

    results: List[Tuple[str, List[Tuple[str, float]]]] = []
    for m_pos, m_idx in enumerate(top_idx):
        # Rank phrases by influence
        order = np.argsort(-deltas[m_pos])[:top_phrases]
        contribs = [(phrases[j], float(deltas[m_pos, j])) for j in order]
        results.append((materials[m_idx], contribs))
    return results

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

    matches = rank_top_k(example_queries, materials, TOP_K)
    for q, hits in zip(example_queries, matches):
        print(f"\nQuery: {q}")
        for rank, (mat, score) in enumerate(hits, start=1):
            print(f"  {rank}. {mat} (Score={score:.4f})")

        if EXPLAIN:
            explanations = explain_influence_occlusion(
                q,
                materials,
                top_materials=EXPLAIN_TOP_MATERIALS,
                top_phrases=EXPLAIN_TOP_PHRASES,
                max_ngram=EXPLAIN_MAX_NGRAM
            )
            for mat_name, contribs in explanations:
                print(f"  Influential phrases for: {mat_name}")
                for phrase, delta in contribs:
                    print(f"    - '{phrase}'  (+{delta:.4f})")

if __name__ == "__main__":
    main()
