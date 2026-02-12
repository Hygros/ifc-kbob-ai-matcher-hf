import requests
from urllib.parse import quote

BEGRIFF = "Armierungsstahl"

def synonyms_from_openthesaurus(term: str,
                                limit_groups: int = 50,
                                max_synonyms: int = 10,
                                similar: bool = False,
                                substring: bool = False,
                                nouns_only: bool = False,
                                debug_wordtypes: bool = False):
    """
    similar=True: zusätzliche ähnliche Begriffe (Differenz).
    substring=True: zusätzliche Teilwort-/Komposita (Differenz).
    nouns_only=True: nur Substantive (wordType enthält 'Substantiv'/'Nomen' oder fehlt).
    debug_wordtypes=True: gibt gefundene Terms mit wordType aus.
    """
    base_url = "https://www.openthesaurus.de/synonyme/search"

    def _request(params):
        try:
            resp = requests.get(base_url, params=params, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"HTTP-Fehler bei OpenThesaurus: {e}")
        return resp.json()

    def _is_noun(term_obj):
        if not nouns_only:
            return True
        wt = term_obj.get("wordType", "")
        if not wt:  # fehlender Typ: als Nomen durchlassen
            return True
        wtl = wt.lower()
        return ("substantiv" in wtl) or ("nomen" in wtl)

    def _synset_terms(data):
        out, seen = [], set()
        for synset in data.get("synsets", []):
            for t in synset.get("terms", []):
                if not _is_noun(t):
                    continue
                s = t.get("term", "").strip()
                if s and s.lower() not in seen:
                    seen.add(s.lower())
                    out.append(s)
                    if debug_wordtypes:
                        print(f"DEBUG synset term: {s} | wordType={t.get('wordType')}")
        return out

    def _extract_terms(data, key):
        out, seen = [], set()
        for t in data.get(key, []):
            if not _is_noun(t):
                continue
            s = t.get("term", "").strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
                if debug_wordtypes:
                    print(f"DEBUG {key} term: {s} | wordType={t.get('wordType')}")
        return out

    if substring:
        sim_params = {"q": term, "format": "application/json", "limit": str(limit_groups), "similar": "true"}
        sim_data = _request(sim_params)
        similar_terms = _extract_terms(sim_data, "similarterms")

        sub_params = {"q": term, "format": "application/json", "limit": str(limit_groups), "substring": "true"}
        sub_data = _request(sub_params)
        substring_terms = _extract_terms(sub_data, "substringterms")

        similar_set = {t.lower() for t in similar_terms}
        extras = [t for t in substring_terms if t.lower() not in similar_set]
        return extras[:max_synonyms]

    base_params = {"q": term, "format": "application/json", "limit": str(limit_groups)}

    if similar:
        std_data = _request(base_params)
        standard_terms = _synset_terms(std_data)
        standard_set = {t.lower() for t in standard_terms}

        sim_params = dict(base_params)
        sim_params["similar"] = "true"
        sim_data = _request(sim_params)
        similar_terms = _extract_terms(sim_data, "similarterms")

        extras = [t for t in similar_terms if t.lower() not in standard_set]
        return extras[:max_synonyms]

    data = _request(base_params)
    syns = _synset_terms(data)
    return syns[:max_synonyms]

# Beispiel
if __name__ == "__main__":
    print(f"Synonyme (nur Nomen) zu {BEGRIFF}:", synonyms_from_openthesaurus(BEGRIFF, nouns_only=True, debug_wordtypes=True))
    similar_extra = synonyms_from_openthesaurus(BEGRIFF, similar=True)
    if similar_extra:
        print(f"Ähnliche Begriffe zu {BEGRIFF}:", similar_extra)
    substring_extra = synonyms_from_openthesaurus(BEGRIFF, substring=True)
    if substring_extra:
        print("Substring:", substring_extra)

