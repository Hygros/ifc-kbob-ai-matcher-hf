# IFC-basierte Ökobilanzierung & Material-Matching

Dieses Projekt bietet eine Pipeline zur Extraktion, Analyse und Bewertung von Baumaterialien aus IFC-Modellen. Ziel ist die automatisierte Zuordnung von IFC-Elementen zu Ökobilanzdaten (KBOB) und die Berechnung von Umweltindikatoren wie UBP21, GWP und Primärenergie.

## Hauptfunktionen

- **IFC-Export:** Extrahiert relevante Informationen (z.B. Material, Volumen, Eigenschaften) aus IFC-Dateien und speichert sie als `.jsonl` und `.txt`.
- **AI-Material-Matching:** Nutzt SBERT (Sentence Transformers), um IFC-Materialien mit KBOB-Datenbankeinträgen zu matchen.
- **Ökobilanz-Berechnung:** Berechnet Umweltindikatoren pro Element auf Basis der gematchten Materialien und exportiert die Ergebnisse als SQLite-Datenbank.
- **Dashboard:** Streamlit-App zur Visualisierung, Materialzuordnung und Ergebnisanalyse inkl. Viewer-Integration.

## Verzeichnisstruktur

- `IFC_Extraction/`: Scripte zur IFC-Extraktion.
- `SBERT/`: SBERT-Matching und Modellverwaltung.
- `Dashboard/`: Streamlit-App mit Viewer und Analyse.
- `models/`: Kanonischer lokaler Modellordner (repo-weit) für SBERT- und Cross-Encoder-Modelle.
- `ifc-export/`, `IFC-Modelle/`: Beispiel- und Ergebnisdaten.
- `Synonyme/`: Synonymdatenbanken und -tools.

## Wichtige Dateien

- `run_ifc_sbert_pipeline.py`: Startet die gesamte Pipeline (IFC → JSONL → SBERT-Matching).
- `Evaluation/export_sbert_queries_to_txt.py`: Exportiert die SBERT-Queries aus dem bestehenden Workflow in eine `.txt`.
- `IFC_Extraction/IFC-extraction-main.py`: Extrahiert IFC-Elementdaten.
- `SBERT/Sentence_Transformer_V00.py`: Führt das Material-Matching durch.
- `calculate_ubp21_per_element.py`: Berechnet Umweltindikatoren pro Element.
- `Dashboard/app_with_viewer.py`: Streamlit-App für Upload, Matching und Visualisierung.

## Voraussetzungen

- Python 3.10+
- KBOB-Datenbank: `Ökobilanzdaten.sqlite3` (nicht im Repo enthalten — eigene Kopie bereitstellen)
- Optional: Node.js / pnpm für die IFC-Viewer-Integration

## Quickstart

```bash
# 1. Repository klonen
git clone https://github.com/<your-org>/Matching.git
cd Matching

# 2. Virtuelle Umgebung erstellen und aktivieren
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Umgebungsvariablen konfigurieren
cp .env.example .env
# → KBOB_DATABASE_PATH in .env auf den Pfad zur SQLite-Datenbank setzen

# 5. Dashboard starten
streamlit run Dashboard/app_with_viewer.py
```

## Nutzung

1. **Dashboard starten:**  
 `streamlit run Dashboard/app_with_viewer.py`  
 → Web-App für Upload, Matching, Visualisierung und Viewer.

2. **Wähle IFC-Datei**

3. **Wähle die korrekte Zuordnung zur KBOB-Datenbank**

4. **Bestaune die Resultate im Charts-Tab**

## SBERT Laufzeit-Konfiguration

Für `SBERT/Sentence_Transformer_V00.py` können Device- und Batch-Entscheidungen per Umgebungsvariablen gesteuert werden:

- `SBERT_DEVICE=cpu|cuda`  
  Erzwingt das Gerät. Ohne Override gilt: ab `SBERT_CUDA_QUERY_THRESHOLD` (Default `500`) und verfügbarer GPU wird `cuda` genutzt, sonst `cpu`.
- `SBERT_BATCH_SIZE=<int>`  
  Feste Batch-Size (höchste Priorität).
- `SBERT_AUTO_BENCH_BATCH=1`  
  Führt vor dem Matching einen Batch-Benchmark aus und verwendet die schnellste stabile Größe.
- `SBERT_AUTO_HEURISTIC_BATCH=1` (Default aktiv)  
  Verwendet feste Heuristik ohne Benchmark:
  - `cuda` und `>=500` Queries → `128`
  - `cpu` und `<=200` Queries → `16`
  - sonst Default (`SBERT_BATCH_SIZE`, falls nicht gesetzt: `64`)
- `SBERT_BENCH_BATCH_SIZES=16,32,64,128`  
  Kandidaten für den Benchmark.
- `SBERT_BENCH_SAMPLE_LIMIT=1500`  
  Maximale Anzahl Queries für den Benchmark.

Batch-Benchmark manuell starten:

- `python SBERT/Sentence_Transformer_V00.py --benchmark-batch Dashboard/data/cuda-test.jsonl`

## Hinweise

- Die KBOB-Datenbank muss vorhanden und korrekt befüllt sein.
- Für die Viewer-Integration wird Node.js/pnpm benötigt.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).

Informationen zu Drittbibliotheken und Modell-Lizenzen: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

> **Hinweis:** Einige optionale Cross-Encoder-Modelle (z. B. Jina Reranker) stehen unter
> nicht-kommerziellen Lizenzen. Details siehe `THIRD_PARTY_NOTICES.md`.

## Evaluation von Modellen

- Komplette Pipeline (optional inkl. Query-Export): `python Evaluation/run_evaluation_pipeline.py --query-source <.ifc|.jsonl|.txt>`
- Ohne `--query-source` öffnet die Pipeline eine Terminal-Auswahl aller `.ifc`, `.jsonl`, `.txt` im Projekt.
- Ohne `--expected-file` fragt die Pipeline optional interaktiv nach einer `.txt` mit Expected-Materialien.
- Format `--expected-file` (eine Zeile pro Query):
  - Ein einzelner Treffer: `Tiefgründung Ortbetonbohrpfahl 900`
  - Mehrere mögliche Treffer: `Material A | Material B | Material C`
  - Mehrere Treffer mit Relevanz: `Material A::1.0 | Material B::0.7 | Material C::0.3`
  - Ohne `::Relevanz` gilt automatisch `1.0`.
- Nur Evaluation laufen lassen: `python Evaluation/evaluate_material_models.py`
- Nur Report + Übersichtsgrafik erzeugen: `python Evaluation/build_evaluation_report.py`
- Query-Export liegt standardmäßig unter `Evaluation/exports/queries/`.
- Ergebnisse liegen unter `Evaluation/exports/model_evaluation/` als:
  - `summary_*.csv`, `details_*.csv`
  - `evaluation_report_*.md` (automatische Dokumentation)
  - `overview_*.svg` (Übersichtsgrafik)
  - `evaluation_report_latest.md`, `overview_latest.svg` (immer der neueste Stand)
