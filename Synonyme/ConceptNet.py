import requests
from typing import List
import time

BEGRIFF = "Pfahl"

def conceptnet_synonyms(
    term: str,
    lang: str = "de",
    max_synonyms: int = 10,
    include_similar: bool = False,
    same_language: bool = True,
    min_weight: float = 1.0,
    retries: int = 3,
    backoff: float = 0.5,
) -> List[str]:
    """
    Holt Synonyme (und optional SimilarTo-Begriffe) für 'term' aus ConceptNet.
    - lang: Sprachcode (z. B. 'de')
    - max_synonyms: maximale Anzahl der zurückgegebenen Begriffe
    - include_similar: True => auch Relationen /r/SimilarTo berücksichtigen
    - same_language: True => nur Begriffe in 'lang' zulassen
    - min_weight: untere Schwellwertgrenze für Kantengewicht (Qualitätsfilter)
    - retries: Anzahl der Versuche für jede API-Anfrage
    - backoff: Zeitraum zwischen den Versuchen (in Sekunden)
    """
    base_url = "https://api.conceptnet.io/query"
    base_search = "https://api.conceptnet.io/search"
    node_uri = f"/c/{lang}/{term.replace(' ', '_').lower()}"
    candidates = []
    headers = {
        "User-Agent": "AAA_Python_MTH/ConceptNetClient (+https://example.invalid)",
        "Accept": "application/json",
    }

    def _request_json(url: str, params: dict):
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                if resp.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(response=resp)
                resp.raise_for_status()
                return resp.json()
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError):
                if attempt == retries:
                    return None
                time.sleep(backoff * (2 ** (attempt - 1)))
        return None

    def collect_edges(rel: str):
        # First try the /query endpoint
        params = {"node": node_uri, "rel": rel, "limit": "100"}
        data = _request_json(base_url, params)
        edges = (data or {}).get("edges", []) if data else []

        # If no edges found, try the /search endpoint (more flexible, matches sense URIs)
        if not edges:
            data = _request_json(base_search, params)
            edges = (data or {}).get("edges", []) if data else []

        if not edges:
            return  # nothing to add

        for e in edges:
            start = e.get("start", {})
            end = e.get("end", {})
            weight = float(e.get("weight", 1.0))
            if weight < min_weight:
                continue
            # “other side” der Kante bestimmen
            if start.get("@id") == node_uri:
                other = end
            elif end.get("@id") == node_uri:
                other = start
            else:
                # also accept if label text matches the term (handles sense URIs on either side)
                start_lbl = (start.get("label") or "").strip().casefold()
                end_lbl = (end.get("label") or "").strip().casefold()
                if term.strip().casefold() in (start_lbl, end_lbl):
                    other = end if start_lbl == term.strip().casefold() else start
                else:
                    continue
            if same_language and other.get("language") != lang:
                continue
            label = (other.get("label") or other.get("term") or "").strip()
            if label:
                candidates.append((label, weight))

    # 1) echte Synonyme
    collect_edges("/r/Synonym")
    # 1b) Soft-Fallback: wenn keine Synonyme gefunden und SimilarTo nicht aktiv, dennoch SimilarTo einmal versuchen
    if not candidates and not include_similar:
        collect_edges("/r/SimilarTo")
    # 2) optional: ähnliche Begriffe (häufig nützlich, wenn wenige /r/Synonym-Kanten existieren)
    if include_similar:
        collect_edges("/r/SimilarTo")

    # Deduplizieren & nach Gewicht sortieren
    best = {}
    for label, weight in candidates:
        k = label.casefold()
        if k not in best or weight > best[k][1]:
            best[k] = (label, weight)
    sorted_labels = [v[0] for v in sorted(best.values(), key=lambda x: (-x[1], x[0].casefold()))]

    # Ursprungsbegriff entfernen (case/underscore-normalisiert)
    origin_norm = term.replace(" ", "_").lower()
    sorted_labels = [s for s in sorted_labels if s.replace(" ", "_").lower() != origin_norm]

    return sorted_labels[:max_synonyms]

# Beispielaufrufe:
if __name__ == "__main__":
    print(conceptnet_synonyms(BEGRIFF, lang="de", max_synonyms=8))
    print(conceptnet_synonyms(BEGRIFF, lang="de", include_similar=True, max_synonyms=12))
