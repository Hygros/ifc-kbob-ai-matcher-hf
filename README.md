# IFC-basierte Ökobilanzierung & Material-Matching

Automatisierte Zuordnung von IFC-Bauelementen zu Ökobilanzdaten (KBOB) mit Sentence-Transformer-basiertem Matching und Berechnung von Umweltindikatoren (UBP21, GWP, Primärenergie).

## Überblick

Das Projekt besteht aus drei Hauptbereichen und einer gemeinsamen Codebasis:

| Bereich | Zweck |
| --------- | ------- |
| **Dashboard** | Streamlit-App: IFC-Upload, AI-Materialzuordnung, 3D-Viewer, Umweltindikator-Visualisierung |
| **Evaluation** | Evaluation von Bi-Encoder- und Cross-Encoder-Modellen gegen erwartete Materialzuordnungen |
| **Training** | Fine-Tuning von Sentence-Transformer-Modellen (BAAI/bge-m3) mit eigenen Trainingsdaten |
| **core** | Gemeinsam genutzte Module: IFC-Extraktion, SBERT-Matching, UBP-Berechnung, Synonyme |

### Pipeline-Ablauf

```text
IFC-Datei
  → core/ifc_extraction   (Elemente, Materialien, PropertySets → JSONL)
  → core/sbert             (Bi-Encoder-Matching + Cross-Encoder-Reranking gegen KBOB-DB)
  → Dashboard              (Nutzer wählt Zuordnung, UBP-Berechnung, Charts)
```

## Projektstruktur

```text
Matching/
│
├── core/                              # Gemeinsam genutzte Module
│   ├── ifc_extraction/                # IFC-Parsing und Element-/Materialextraktion
│   │   ├── ifc_extraction_core.py     #   Kern-Logik: PropertySets, Einheiten, Materialschichten
│   │   ├── ifc_extraction_main.py     #   CLI-Einstiegspunkt (python -m core.ifc_extraction.ifc_extraction_main)
│   │   ├── ifc_material_extract_util.py
│   │   ├── ifc_batch_export_to_csv.py #   Batch-Export ganzer IFC-Ordner → CSV + Analyse-Reports
│   │   ├── ifc_export_simple.py       #   Einfacher Hierarchie-/PropertySet-Export als Text
│   │   └── ifc_reinforcement_relation.py
│   ├── sbert/                         # Sentence-Transformer Matching-Engine
│   │   ├── sentence_transformer.py    #   Bi-Encoder + Cross-Encoder Reranking gegen KBOB
│   │   ├── batch_benchmark.py         #   Batch-Size-Benchmark für optimale Encoding-Performance
│   │   └── cross_encoder.py           #   Standalone Cross-Encoder-Demo
│   ├── synonyme/                      # Deutsche Synonym-Anreicherung
│   │   ├── conceptnet.py              #   ConceptNet API
│   │   ├── conceptnet_scraper.py      #   ConceptNet mit HTML-Fallback
│   │   ├── odenet.py                  #   OdeNet (German WordNet)
│   │   └── openthesaurus.py           #   OpenThesaurus API
│   ├── calculate_ubp21_per_element.py # UBP/GWP/Energie-Berechnung pro Element
│   └── ifc_units_reader.py            # IFC-Einheiten-Interpretation (SI, Prefixes)
│
├── Dashboard/                         # Streamlit-Webanwendung
│   ├── app_with_viewer.py             #   Haupteinstiegspunkt
│   ├── config.py                      #   Modell-Optionen, Indikator-Definitionen, Schwellwerte
│   ├── domain/
│   │   └── mapping.py                 #   Domain-Logik: Bewehrung, Betonzuordnung, Gruppierung
│   ├── services/
│   │   ├── bootstrap.py               #   App-Initialisierung: Modell-Vorladung, Viewer-Start
│   │   ├── ifc_pipeline.py            #   IFC → JSONL → SBERT Pipeline (subprocess + API)
│   │   ├── kbob_materials.py          #   KBOB-Datenbank-Zugriff
│   │   ├── training_export.py         #   Export manueller Zuordnungen als Trainingsdaten
│   │   ├── ubp.py                     #   UBP-Berechnung und Ergebnis-Merge
│   │   └── viewer.py                  #   3D-IFC-Viewer (ifc-lite) Integration
│   ├── ui/
│   │   ├── header.py                  #   KPI-Metriken
│   │   ├── tab_ai_mapping.py          #   AI-Mapping-Tab: Materialauswahl, Viewer-Sync
│   │   ├── tab_charts.py              #   Charts-Tab: Balken/Torte/Bubble nach KPI
│   │   └── tab_uploads.py             #   Upload-Tab: Modellwahl, IFC-Upload, Quick-Load
│   ├── data/                          #   Gespeicherte JSONL-Ergebnisse
│   ├── ifc-lite/                      #   TypeScript/Vite 3D-Viewer (npm/pnpm)
│   └── static/                        #   Hochgeladene IFC-Dateien für Viewer
│
├── Evaluation/                        # Modell-Evaluation
│   ├── run_evaluation_pipeline.py     #   Orchestrator: Query-Export → Evaluate → Report
│   ├── evaluate_material_models.py    #   Kern-Engine: 13 Bi-Encoder + Cross-Encoder Benchmarks
│   ├── build_evaluation_report.py     #   Markdown-Report + SVG-Übersichtsgrafik generieren
│   ├── export_sbert_queries_to_txt.py #   IFC/JSONL → Query-TXT für Evaluation
│   ├── retrieval_metrics.py           #   Hit@K, MRR, MAP@10, nDCG@10, Recall@10
│   ├── metric_explanations.md         #   Erklärung der Metriken
│   ├── test_data/                     #   Testdaten (IFC, JSONL, Queries, Analyse-CSVs)
│   ├── expected_material/             #   Ground-Truth-Dateien für Evaluation
│   ├── exports/                       #   Generierte Queries + Evaluationsergebnisse
│   │   ├── queries/                   #     Query-TXT-Dateien
│   │   └── model_evaluation/          #     CSV-Metriken, Reports, SVG-Grafiken
│   ├── tests/                         #   Unit-Tests (pytest)
│   └── azure/                         #   Azure ML Evaluation-Jobs
│
├── Training/                          # Bi-Encoder Fine-Tuning
│   ├── run_training_pipeline.py       #   Orchestrator: validate → prepare → train
│   ├── prepare_training_data.py       #   Query/Expected TXT → JSONL-Trainingspaare
│   ├── train_bge_m3.py                #   Fine-Tuning mit MultipleNegativesRankingLoss
│   ├── validate_training_data.py      #   Validierung von Roh- und JSONL-Trainingsdaten
│   ├── run_single_model_evaluation.py #   Einzelmodell-Evaluation (ohne alle 13 Modelle)
│   ├── data/                          #   Rohdaten (Query-/Expected-TXT, Excel)
│   ├── artifacts/                     #   Trainierte Modelle + Trainingspaare
│   └── outputs/                       #   Evaluationsergebnisse einzelner Modelle
│
├── scripts/                           # Ad-hoc-Beispiele und Testskripte
├── models/                            # Lokaler Modell-Cache (SBERT, Cross-Encoder)
├── IFC-Modelle/                       # Test-IFC-Dateien und UBP-Berechnungsergebnisse
├── Ökobilanzdaten.sqlite3             # KBOB-Materialdatenbank (nicht im Repo)
│
├── run_ifc_sbert_pipeline.py          # CLI-Einstiegspunkt: IFC → JSONL → SBERT-Matching
├── requirements.txt                   # Python-Abhängigkeiten
├── .env.example                       # Vorlage für Umgebungsvariablen
├── DATENFLUSS_EIGENSCHAFTEN.md        # Dokumentation: Datenfluss IFC → SBERT → Dashboard
├── CONTRIBUTING.md
├── LICENSE                            # MIT
└── THIRD_PARTY_NOTICES.md
```

## Voraussetzungen

- **Python 3.12**
- **KBOB-Datenbank:** `Ökobilanzdaten.sqlite3` (bereinigte und gefilterte Ökobilanzdaten der KBOB)
- **Optional:** Node.js / pnpm für die 3D-IFC-Viewer-Integration im Dashboard

## Quickstart

```bash
# Repository klonen
git clone https://github.com/<your-org>/Matching.git
cd Matching

# Virtuelle Umgebung erstellen und aktivieren
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# Abhängigkeiten installieren
pip install -r requirements.txt

# Umgebungsvariablen konfigurieren
cp .env.example .env
# → KBOB_DATABASE_PATH in .env auf den Pfad zur SQLite-Datenbank setzen

# Dashboard starten
streamlit run Dashboard/app_with_viewer.py
```

## Nutzung

### Dashboard

```bash
streamlit run Dashboard/app_with_viewer.py
```

1. **Uploads-Tab:** IFC-Datei hochladen, SBERT-Modell und optional Cross-Encoder wählen, "Mapping berechnen" klicken.
2. **AI-Mapping-Tab:** Vom AI vorgeschlagene KBOB-Materialien prüfen und bestätigen/korrigieren. 3D-Viewer zeigt das gewählte Element. Bewehrungsannahmen konfigurieren.
3. **Charts-Tab:** UBP, CO₂, Energie und weitere KPIs nach Element, Material oder IfcEntity visualisieren.

> **Credits:** Der integrierte 3D-Viewer basiert auf dem Open-Source-Projekt [ifc-lite](https://github.com/louistrue/ifc-lite) von [Louis True](https://github.com/louistrue) (Lizenz: MPL-2.0).

Manuell korrigierte Zuordnungen werden automatisch als Trainingsdaten nach `Training/data/` exportiert.

### CLI-Pipeline (ohne Dashboard)

```bash
# Komplette Pipeline: IFC → JSONL → SBERT-Matching
python run_ifc_sbert_pipeline.py <Pfad-zur-IFC-Datei>

# Nur IFC-Extraktion
python -m core.ifc_extraction.ifc_extraction_main <Pfad-zur-IFC-Datei>

# Batch-Export (Ordner mit IFC-Dateien → CSV + Analyse)
python -m core.ifc_extraction.ifc_batch_export_to_csv --ifc-folder <Ordner> --output-csv export.csv
```

## Evaluation

Die Evaluation vergleicht bis zu 13 Bi-Encoder-Modelle (+ optionalen Cross-Encoder) gegen Ground-Truth-Zuordnungen.

```bash
# Komplette Pipeline mit interaktiver Modell-/Dateiauswahl
python Evaluation/run_evaluation_pipeline.py

# Mit expliziten Parametern
python Evaluation/run_evaluation_pipeline.py \
  --query-source Evaluation/exports/queries/list_1_queries_with_ifc.txt \
  --expected-file Evaluation/expected_material/list_1_expected_mit-ohne_ifc.txt \
  --cross-encoder-model BAAI/bge-reranker-v2-m3 \
  --rerank-top-n 30

# Einzelne Schritte
python Evaluation/evaluate_material_models.py   # Nur Evaluation
python Evaluation/build_evaluation_report.py     # Nur Report generieren
```

**Expected-Format** (eine Zeile pro Query, `|`-separiert für Alternativen, `::` für Relevanz-Gewichtung):

```text
Tiefgründung Ortbetonbohrpfahl 900
Material A | Material B | Material C
Material A::1.0 | Material B::0.7
```

Ergebnisse: `Evaluation/exports/model_evaluation/` (CSV, Markdown-Report, SVG-Grafik).

**Metriken:** Hit@K, MRR, MAP@10, nDCG@10, Recall@10 — Details in [Evaluation/metric_explanations.md](Evaluation/metric_explanations.md).

## Training

Fine-Tuning von `BAAI/bge-m3` mit eigenen Query/Expected-Paaren:

```bash
python Training/run_training_pipeline.py \
  --query-file Evaluation/exports/queries/list_1_queries_with_ifc.txt \
  --expected-file Evaluation/expected_material/list_1_expected_mit-ohne_ifc.txt \
  --base-model BAAI/bge-m3 \
  --output-dir Training/artifacts/models/bge-m3-finetuned \
  --epochs 2 --batch-size 8 --lr 2e-5 --device cuda --fp16 --deduplicate
```

Das trainierte Modell kann direkt mit dem Single-Model-Runner evaluiert werden:

```bash
python Training/run_single_model_evaluation.py \
  --model Training/artifacts/models/bge-m3-finetuned \
  --query-file Evaluation/exports/queries/list_1_queries_with_ifc.txt \
  --expected-file Evaluation/expected_material/list_1_expected_mit-ohne_ifc.txt \
  --run-label finetuned
```

Details: [Training/README.md](Training/README.md).

## Umgebungsvariablen

Konfiguration über `.env` oder Umgebungsvariablen (siehe [.env.example](.env.example)):

| Variable | Beschreibung | Default |
| ---------- | ------------- | --------- |
| `KBOB_DATABASE_PATH` | Pfad zur KBOB SQLite-Datenbank | `./Ökobilanzdaten.sqlite3` |
| `SBERT_DEVICE` | Device erzwingen: `cpu` oder `cuda` | Auto (GPU ab 500 Queries) |
| `SBERT_BATCH_SIZE` | Feste Batch-Size | `64` |
| `SBERT_AUTO_BENCH_BATCH` | Batch-Benchmark vor Matching | `0` |
| `SBERT_AUTO_HEURISTIC_BATCH` | Heuristische Batch-Size | `1` (aktiv) |
| `SBERT_CUDA_QUERY_THRESHOLD` | Mindest-Queries für Auto-GPU | `500` |
| `SBERT_CROSS_ENCODER_REVISION` | Pinned Cross-Encoder Revision | — |

## Tests

```bash
python -m pytest Evaluation/tests/ -v
```

## Lizenz

[MPL-Lizenz](LICENSE).

Informationen zu Drittbibliotheken und Modell-Lizenzen: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

> **Hinweis:** Einige optionale Cross-Encoder-Modelle (z. B. Jina Reranker) stehen unter
> nicht-kommerziellen Lizenzen. Details siehe `THIRD_PARTY_NOTICES.md`.
