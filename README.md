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
- `models/`: Vorgehaltene SBERT-Modelle.
- `ifc-export/`, `IFC-Modelle/`: Beispiel- und Ergebnisdaten.
- `Synonyme/`: Synonymdatenbanken und -tools.

## Wichtige Dateien

- `run_ifc_sbert_pipeline.py`: Startet die gesamte Pipeline (IFC → JSONL → SBERT-Matching).
- `IFC_Extraction/IFC-extraction-main.py`: Extrahiert IFC-Elementdaten.
- `SBERT/Sentence_Transformer_V00.py`: Führt das Material-Matching durch.
- `calculate_ubp21_per_element.py`: Berechnet Umweltindikatoren pro Element.
- `Dashboard/app_with_viewer.py`: Streamlit-App für Upload, Matching und Visualisierung.

## Voraussetzungen

- Python 3.8+
- Pakete: `ifcopenshell`, `sentence-transformers`, `streamlit`, `torch`, `sqlite3`, u.a.
- KBOB-Datenbank: `Ökobilanzdaten.sqlite3` im Projektverzeichnis
- Optional: Lokale SBERT-Modelle im `models/`-Ordner

## Nutzung

1. **Dashboard starten:**  
 `streamlit run Dashboard/app_with_viewer.py`  
 → Web-App für Upload, Matching, Visualisierung und Viewer.

2. **Wähle IFC-Datei**

## Hinweise

- Die SBERT-Modelle werden beim ersten Lauf automatisch heruntergeladen und gespeichert.
- Die KBOB-Datenbank muss vorhanden und korrekt befüllt sein.
- Für die Viewer-Integration wird Node.js/pnpm benötigt.

## Lizenz

Noch ergänzen
