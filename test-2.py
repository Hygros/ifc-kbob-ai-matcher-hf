import os
import re
import json
import sqlite3
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import requests

# =========================
# Konfiguration
# =========================
DB_PATH = r"C:\Users\wpx619\OneDrive - FHNW\Masterthesis\Python\Ökobilanzdaten.sqlite3"
TABLE_NAME = "Oekobilanzdaten"
COL_NAME = "Material"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_DIR = ".cache_material_index"
TOP_K = 5
MIN_SCORE = 0.1

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# =========================
# Dataclasses
# =========================
@dataclass
class NormalizedQuery:
    raw: str
    canonical: str
    extracted_attributes: Dict[str, str]
    keywords: List[str]
    method: str


# =========================
# Hilfsfunktionen
# =========================
def tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^A-Za-z0-9äöü/._-]+", text.lower()) if t]


def detect_attributes(text: str) -> Dict[str, str]:
    attrs = {}
    if re.search(r"\bC\d{2}/\d{2}\b", text):
        attrs["grade"] = re.search(r"\bC\d{2}/\d{2}\b", text).group()
    if re.search(r"\b\d{2,4}\s*mm\b", text):
        attrs["size_mm"] = re.search(r"\b\d{2,4}\s*mm\b", text).group()
    for mat in ["beton", "stahl", "holz", "asphalt", "epdm", "xps", "eps", "pur", "pvc", "pp", "pe", "pc", "ps", "pmma"]:
        if mat in text.lower():
            attrs["material_class"] = mat
            break
    return attrs


def call_local_llm(prompt: str, model: str = "mistral") -> dict:
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": os.getenv("LLM_LOCAL_MODEL", model),
        "prompt": prompt,
        "options": {"temperature": 0.2},
        "stream": False,
        "format": "json",
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        obj = response.json()
        content = obj.get("response", "")
        if not content:
            return {"canonical": "", "attributes": {}, "keywords": []}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "canonical": content.strip(),
                "attributes": {},
                "keywords": [],
            }
    except requests.RequestException as e:
        logging.warning(f"Local LLM request failed: {e}")
        return {"canonical": "", "attributes": {}, "keywords": []}


# =========================
# QueryNormalizer
# =========================
class QueryNormalizer:
    def normalize(self, query: str, corpus_labels: List[str], embed_fn) -> NormalizedQuery:
        prompt = (
            """
Analysiere den folgenden Text und gib NUR eine JSON-Antwort mit genau diesem Schema (keine Erklärungen, kein Markdown):
{
  "canonical": "sehr kurze, präzise Material-/Elementbeschreibung in der Sprache des Eingabetextes",
  "attributes": {"material_class": "...", "grade": "..."},
  "keywords": ["...", "..."]
}

Wichtige Regeln:
- Antworte ausschließlich als reines JSON ohne Markdown.
- Verwende die Sprache des Eingabetextes (keine Übersetzungen, kein Englisch, wenn der Text Deutsch ist).
- Fülle "attributes" nur mit Werten, die im Text vorkommen (z. B. Betonfestigkeitsklasse C30/37). Keine generischen Klassen wie "Inorganic".
- "keywords" sollen Synonyme und nahe Bezeichnungen für die gesuchten Materialien/Elemente sein:
  - bis zu 10 kurze Ausdrücke
  - alles in Kleinbuchstaben
  - keine Stoppwörter, keine allgemeinen Wörter
  - nur Buchstaben/Ziffern inkl. "äöü" sowie "/", "-", "_", "."
  - keine Duplikate

Text: """.strip()
            + f'"{query}"'
        )
        llm_result = call_local_llm(prompt)
        # Debug output: show raw LLM response
        print("LLM raw response:", llm_result)
        canonical = llm_result.get("canonical") or query.strip()
        raw_attrs = llm_result.get("attributes") or {}
        # sanitize attributes: keep only non-empty strings
        attrs = {k: v for k, v in raw_attrs.items() if isinstance(v, str) and v.strip()}
        if not attrs:
            attrs = detect_attributes(query)
        # Ensure sensible defaults and capitalization for known classes
        if "grade" not in attrs or not attrs.get("grade"):
            attrs["grade"] = "nicht angegeben"
        if "material_class" in attrs and isinstance(attrs["material_class"], str):
            if attrs["material_class"].lower() == "beton":
                attrs["material_class"] = "Beton"
        else:
            # Try to infer and capitalize common material names from query
            if re.search(r"\bbeton\b", query, re.IGNORECASE):
                attrs["material_class"] = "Beton"
        raw_keywords = llm_result.get("keywords") or []
        # sanitize keywords: normalize, lowercase, restrict chars, dedupe
        keywords_tmp = []
        for kw in raw_keywords:
            if not isinstance(kw, str):
                continue
            cleaned = re.sub(r"[^a-z0-9äöüÄÖÜ/._\-]+", " ", kw.lower()).strip()
            if cleaned:
                keywords_tmp.append(cleaned)
        # deduplicate while preserving order
        seen = set()
        keywords = []
        for kw in keywords_tmp:
            if kw not in seen:
                seen.add(kw)
                keywords.append(kw)
        if not keywords:
            keywords = tokenize(query)
        method = "llm-local"
        nq = NormalizedQuery(raw=query, canonical=canonical, extracted_attributes=attrs, keywords=keywords, method=method)
        # Debug output: show normalized query dataclass as dict
        print("After normalization:", asdict(nq))
        return nq


# =========================
# EmbeddingIndex
# =========================
class EmbeddingIndex:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model = SentenceTransformer(model_name)
        self.labels: List[str] = []
        self.embeddings = None

    def build(self, items: List[str]):
        self.labels = list(items)
        self.embeddings = self.model.encode(self.labels, normalize_embeddings=True)

    def query(self, query_text: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
        q_emb = self.model.encode([query_text], normalize_embeddings=True)[0]
        sims = np.dot(self.embeddings, q_emb)
        idxs = np.argsort(-sims)[:top_k]
        return [{"rank": r + 1, "score": float(sims[i]), "label": self.labels[i], "index": int(i)} for r, i in enumerate(idxs)]

    def encode(self, texts: List[str]):
        return self.model.encode(texts, normalize_embeddings=True)


# =========================
# MaterialSearch
# =========================
class MaterialSearch:
    def __init__(self, conn, table=TABLE_NAME, col=COL_NAME, model_name=MODEL_NAME):
        self.conn = conn
        self.table = table
        self.col = col
        self.index = EmbeddingIndex(model_name)
        self.labels = []

    def load_labels(self) -> List[str]:
        cur = self.conn.cursor()
        cur.execute(f"SELECT {self.col} FROM {self.table}")
        self.labels = [row[0] for row in cur.fetchall()]
        return self.labels

    def build_index(self):
        if not self.labels:
            self.load_labels()
        self.index.build(self.labels)

    def search(self, query: str, top_k: int = TOP_K, min_score: float = MIN_SCORE) -> Dict[str, Any]:
        normalizer = QueryNormalizer()
        nq = normalizer.normalize(query, self.labels, self.index.encode)
        # Build enriched query text for SBERT:
        # - include LLM-generated synonyms/keywords
        # - include context values extracted from the original query (right-hand sides of key:value pairs)
        # - DO NOT include the words "canonical", "attributes", "keywords" nor JSON keys, nor attribute names
        def extract_context_values(s: str) -> List[str]:
            values: List[str] = []
            # Parse simple key:value pairs separated by commas or semicolons
            for part in re.split(r"[,;]", s):
                if ":" in part:
                    _, val = part.split(":", 1)
                    val = val.strip()
                    if val:
                        values.append(val)
            if values:
                return values
            # Fallback: remove known key words and return remaining tokens
            tokens = [t for t in tokenize(s) if t not in {"material", "element", "canonical", "attributes", "keywords"}]
            return [" ".join(tokens)] if tokens else []

        context_values = extract_context_values(query)
        enriched_parts = []
        # add keywords first (synonyms carry most semantic weight)
        if nq.keywords:
            enriched_parts.extend(nq.keywords)
        # then add extracted context values
        enriched_parts.extend(context_values)
        enriched_query_text = " ".join(enriched_parts).strip()
        hits = self.index.query(enriched_query_text or query, top_k=top_k * 2)

        results = []
        for h in hits:
            label_tokens = set(tokenize(h["label"]))
            # tokenize keywords as well to improve overlap signal
            kw_tokens = set(t for kw in nq.keywords for t in tokenize(kw))
            keyword_overlap = len(kw_tokens & label_tokens) / (len(kw_tokens) + 1)
            # safely compute attribute bonus; ignore None/non-strings
            label_lc = h["label"].lower()
            attr_values = [v for v in nq.extracted_attributes.values() if isinstance(v, str) and v]
            attr_bonus = sum(1 for v in attr_values if v.lower() in label_lc) * 0.05
            final_score = 0.7 * h["score"] + 0.2 * keyword_overlap + attr_bonus
            if final_score >= min_score:
                results.append({"label": h["label"], "cosine": h["score"], "final_score": final_score, "rank": len(results) + 1})

        results.sort(key=lambda x: -x["final_score"])
        best_label = results[0]["label"] if results else None
        details = None
        if best_label:
            details = pd.read_sql_query(f"SELECT Material FROM {self.table} WHERE {self.col} = ?", self.conn, params=[best_label])

        return {
            "query": query,
            "normalized": asdict(nq),
            "enriched_query": enriched_query_text,
            "results": results[:top_k],
            "best_material_details": details,
        }


# =========================
# Main
# =========================
if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    ms = MaterialSearch(conn)
    ms.build_index()

    example_queries = [
        "Material: Beton, Element: Widerlagerwand",
    ]

    for q in example_queries:
        out = ms.search(q, top_k=TOP_K)
        print(f"\n=== Query: {q} ===")
        print("Normalized:", out["normalized"])
        for r in out["results"]:
            print(f"{r['rank']:>2}. final={r['final_score']:.3f} cos={r['cosine']:.3f} | {r['label']}")
        if out["best_material_details"] is not None:
            print(out["best_material_details"])

    conn.close()

# "Material: Beton C30/37, Element: Fahrbahnplatte",
# "Armierungsstahl",
# "Bewehrung",
# "Asphalt",
# "Dichtungsbahn EPDM",
# "Holz",
# "Flüssigkunststoff"