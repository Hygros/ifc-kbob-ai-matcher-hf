import pandas as pd


CHART_HEIGHT = 700


# ---------------------------------------------------------------------------
# Bewehrungserkennung (Reinforcement detection)
# ---------------------------------------------------------------------------
# Case-insensitive Substrings – deckt z.B. Stahlbeton, Ortbeton, Spritzbeton,
# Fertigbeton, Reinforced Concrete, Precast Concrete, etc.
CONCRETE_KEYWORDS: list[str] = ["beton", "concrete"]

# Standard-Bewehrungsgehalt (kg Stahl / m³ Beton) je IfcEntity.
# "_default" wird verwendet, wenn der IfcEntity-Typ nicht gelistet ist.
DEFAULT_REINFORCEMENT_RATIO: dict[str, float] = {
    "IfcSlab": 80.0,
    "IfcWall": 60.0,
    "IfcColumn": 150.0,
    "IfcBeam": 120.0,
    "IfcPile": 100.0,
    "IfcFooting": 80.0,
    "_default": 100.0,
}

# KBOB-Materialname für synthetische Bewehrungszeilen
REINFORCEMENT_KBOB_MATERIAL: str = "Armierungsstahl"

# Fallback-Dichte (kg/m³) für Armierungsstahl, falls DB-Abfrage fehlschlägt
REINFORCEMENT_STEEL_DENSITY_FALLBACK: float = 7850.0


SBERT_MODEL_OPTIONS = [
    "google/embeddinggemma-300m",
    "BAAI/bge-m3",
    "BAAI/bge-m3.finetuned.1e",
    "intfloat/multilingual-e5-large",
    "intfloat/multilingual-e5-base",
    "sentence-transformers/LaBSE",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "sentence-transformers/distiluse-base-multilingual-cased-v2",
]

DEFAULT_SBERT_MODEL = "BAAI/bge-m3"

# --- Cross-Encoder (Re-Ranking) ---
DEFAULT_CROSS_ENCODER_MODEL = "jinaai/jina-reranker-v2-base-multilingual"

CROSS_ENCODER_MODEL_OPTIONS = [
    "jinaai/jina-reranker-v2-base-multilingual",   # 278M | 100 Sprachen | DE+EN optimiert
    "BAAI/bge-reranker-v2-m3",                      # 568M | Multilingual  | stärkstes Modell
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",  # 117M | 26 Sprachen   | schnelle Baseline
]


INDICATOR_DEFINITIONS = [
    {
        "db_col": "UBP21Total",
        "column": "ubp",
        "label": "UBP21 Total",
        "family": "Umweltbelastungspunkte (UBP21)",
        "phase": "Total",
        "unit": "UBP",
    },
    {
        "db_col": "UBP21Herstellung",
        "column": "ubp21_herstellung",
        "label": "UBP21 Herstellung",
        "family": "Umweltbelastungspunkte (UBP21)",
        "phase": "Herstellung",
        "unit": "UBP",
    },
    {
        "db_col": "UBP21Entsorgung",
        "column": "ubp21_entsorgung",
        "label": "UBP21 Entsorgung",
        "family": "Umweltbelastungspunkte (UBP21)",
        "phase": "Entsorgung",
        "unit": "UBP",
    },
    {
        "db_col": "PrimärenergiegesamtTotalkWhoil-eq",
        "column": "penre_kwh_oil_eq",
        "label": "Primärenergie gesamt Total",
        "family": "Primärenergie gesamt (kWh oil-eq)",
        "phase": "Total",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "PrimärenergiegesamtHerstellungtotalkWhoil-eq",
        "column": "penre_gesamt_herstellung_total",
        "label": "Primärenergie gesamt Herstellung total",
        "family": "Primärenergie gesamt (kWh oil-eq)",
        "phase": "Herstellung total",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "PrimärenergiegesamtEntsorgungkWhoil-eq",
        "column": "penre_gesamt_entsorgung",
        "label": "Primärenergie gesamt Entsorgung",
        "family": "Primärenergie gesamt (kWh oil-eq)",
        "phase": "Entsorgung",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "PrimärenergiegesamtHerstellungenergetischgenutztkWhoil-eq",
        "column": "penre_gesamt_herstellung_energetisch",
        "label": "Primärenergie gesamt Herstellung energetisch genutzt",
        "family": "Primärenergie gesamt (kWh oil-eq)",
        "phase": "Herstellung energetisch genutzt",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "PrimärenergiegesamtHerstellungstofflichgenutztkWhoil-eq",
        "column": "penre_gesamt_herstellung_stofflich",
        "label": "Primärenergie gesamt Herstellung stofflich genutzt",
        "family": "Primärenergie gesamt (kWh oil-eq)",
        "phase": "Herstellung stofflich genutzt",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "PrimärenergieerneuerbarTotalkWhoil-eq",
        "column": "penre_erneuerbar_total",
        "label": "Primärenergie erneuerbar Total",
        "family": "Primärenergie erneuerbar (kWh oil-eq)",
        "phase": "Total",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "PrimärenergieerneuerbarHerstellungtotalkWhoil-eq",
        "column": "penre_erneuerbar_herstellung_total",
        "label": "Primärenergie erneuerbar Herstellung total",
        "family": "Primärenergie erneuerbar (kWh oil-eq)",
        "phase": "Herstellung total",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "PrimärenergieerneuerbarHerstellungenergetischgenutztkWhoil-eq",
        "column": "penre_erneuerbar_herstellung_energetisch",
        "label": "Primärenergie erneuerbar Herstellung energetisch genutzt",
        "family": "Primärenergie erneuerbar (kWh oil-eq)",
        "phase": "Herstellung energetisch genutzt",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "PrimärenergieerneuerbarHerstellungstofflichgenutztkWhoil-eq",
        "column": "penre_erneuerbar_herstellung_stofflich",
        "label": "Primärenergie erneuerbar Herstellung stofflich genutzt",
        "family": "Primärenergie erneuerbar (kWh oil-eq)",
        "phase": "Herstellung stofflich genutzt",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "nichterneuerbar(GraueEnergie)TotalkWhoil-eq",
        "column": "graue_energie_total",
        "label": "Graue Energie Total",
        "family": "Nicht erneuerbar (Graue Energie) (kWh oil-eq)",
        "phase": "Total",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "nichterneuerbar(GraueEnergie)HerstellungtotalkWhoil-eq",
        "column": "graue_energie_herstellung_total",
        "label": "Graue Energie Herstellung total",
        "family": "Nicht erneuerbar (Graue Energie) (kWh oil-eq)",
        "phase": "Herstellung total",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "nichterneuerbar(GraueEnergie)HerstellungenergetischgenutztkWhoil-eq",
        "column": "graue_energie_herstellung_energetisch",
        "label": "Graue Energie Herstellung energetisch genutzt",
        "family": "Nicht erneuerbar (Graue Energie) (kWh oil-eq)",
        "phase": "Herstellung energetisch genutzt",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "nichterneuerbar(GraueEnergie)HerstellungstofflichgenutztkWhoil-eq",
        "column": "graue_energie_herstellung_stofflich",
        "label": "Graue Energie Herstellung stofflich genutzt",
        "family": "Nicht erneuerbar (Graue Energie) (kWh oil-eq)",
        "phase": "Herstellung stofflich genutzt",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "nichterneuerbar(GraueEnergie)EntsorgungkWhoil-eq",
        "column": "graue_energie_entsorgung",
        "label": "Graue Energie Entsorgung",
        "family": "Nicht erneuerbar (Graue Energie) (kWh oil-eq)",
        "phase": "Entsorgung",
        "unit": "kWh oil-eq",
    },
    {
        "db_col": "TreibhausgasemissionenTotalkgCO2-eq",
        "column": "gwp_kgco2eq",
        "label": "Treibhausgasemissionen Total",
        "family": "Treibhausgasemissionen (kg CO2-eq)",
        "phase": "Total",
        "unit": "kg CO2-eq",
    },
    {
        "db_col": "TreibhausgasemissionenHerstellungkgCO2-eq",
        "column": "gwp_herstellung_kgco2eq",
        "label": "Treibhausgasemissionen Herstellung",
        "family": "Treibhausgasemissionen (kg CO2-eq)",
        "phase": "Herstellung",
        "unit": "kg CO2-eq",
    },
    {
        "db_col": "TreibhausgasemissionenEntsorgungkgCO2-eq",
        "column": "gwp_entsorgung_kgco2eq",
        "label": "Treibhausgasemissionen Entsorgung",
        "family": "Treibhausgasemissionen (kg CO2-eq)",
        "phase": "Entsorgung",
        "unit": "kg CO2-eq",
    },
    {
        "db_col": "BiogenerKohlenstoffimProduktenthaltenkgC",
        "column": "biogener_kohlenstoff_kgc",
        "label": "Biogener Kohlenstoff im Produkt",
        "family": "Biogener Kohlenstoff (kg C)",
        "phase": "Inhalt",
        "unit": "kg C",
    },
]


INDICATOR_DB_TO_COLUMN = {
    item["db_col"]: item["column"] for item in INDICATOR_DEFINITIONS
}


def get_available_indicator_definitions(df: pd.DataFrame) -> list[dict]:
    available = []
    for definition in INDICATOR_DEFINITIONS:
        alias_col = definition["column"]
        db_col = definition["db_col"]
        active_col = None
        if alias_col in df.columns and not df[alias_col].isna().all():
            active_col = alias_col
        elif db_col in df.columns and not df[db_col].isna().all():
            active_col = db_col
        if active_col:
            enriched = definition.copy()
            enriched["active_column"] = active_col
            available.append(enriched)
    return available
