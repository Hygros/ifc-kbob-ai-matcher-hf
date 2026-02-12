import wn
from typing import List, Optional

_BEGRIFF = "Armierungsstahl"
_ODENET_CACHE: Optional[wn.Wordnet] = None  # Cache

def setup_odenet(lexicon: str = "odenet:1.4") -> wn.Wordnet:
    """
    Stellt sicher, dass OdeNet lokal verfügbar ist und gibt ein Wordnet-Objekt zurück.
    """
    global _ODENET_CACHE
    if _ODENET_CACHE is not None:
        return _ODENET_CACHE
    try:
        # Falls noch nicht vorhanden, lädt dies das Lexikon herunter (einmalig).
        wn.download(lexicon)
    except Exception as e:
        raise RuntimeError(f"Download von {lexicon} fehlgeschlagen: {e}")
    _ODENET_CACHE = wn.Wordnet(lexicon)
    return _ODENET_CACHE

def _extract_lemma(raw) -> str:
    """
    Versucht das Lemma robust als String zu extrahieren (verschiedene wn-Versionen).
    """
    if hasattr(raw, "form"):
        return raw.form().strip()
    if hasattr(raw, "lemma"):
        # manche APIs nutzen lemma()
        try:
            return raw.lemma().strip()
        except Exception:
            pass
    return str(raw).strip()

def synonyms_from_odenet(
    term: str,
    max_synonyms: int = 10,
    include_variants: bool = True
) -> List[str]:
    """
    Liefert eine deduplizierte Liste von Synonymen (nur Nomen) aus OdeNet für den gegebenen Term.
    - term: Suchbegriff (deutsch, Nomen)
    - max_synonyms: Obergrenze der zurückgegebenen Synonyme
    - include_variants: True => Varianten/Mehrwort-Lemmata werden ebenfalls aufgenommen
    """
    de = setup_odenet()

    # Synsets zum gegebenen Lemma finden; pos kann zur Einschränkung genutzt werden.
    synsets = de.synsets(term, pos="n")  # nur Nomen-Synsets

    seen_lower = set()
    synonyms = []

    for syn in synsets:
        # Alle Lemmata (Words/Lexemes) in diesem Synset einsammeln
        for s in syn.lemmas():
            # Sicherstellen, dass das Lemma wirklich ein Nomen ist (zur Absicherung)
            if not isinstance(s, str) and hasattr(s, "pos") and s.pos != "n":
                continue
            lemma = _extract_lemma(s)
            if not lemma:
                continue
            if not include_variants and ((" " in lemma) or ("-" in lemma)):
                continue
            key = lemma.lower()
            if key not in seen_lower and key != term.lower():
                seen_lower.add(key)
                synonyms.append(lemma)
                if len(synonyms) >= max_synonyms:
                    return synonyms

    return synonyms

if __name__ == "__main__":
    print(f"Synonyme zu {_BEGRIFF}:", synonyms_from_odenet(_BEGRIFF, max_synonyms=10))
