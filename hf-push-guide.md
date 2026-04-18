# HF Push Guide (kurz)

Voraussetzung:
- Du bist im Repo-Root.
- Der Deploy-Branch ist main.
- Regel: Immer alle lokalen Aenderungen pushen (keine Teil-Commits).

1. Space-Remote setzen (einmalig)

git remote add hf-space https://huggingface.co/spaces/Hygros-LCA/ifc-kbob-ai-matcher
git remote -v

2. Lokalen Stand pruefen

git status --short
git branch --show-current

3. Historie bereinigen (wenn HF alte Dateien blockiert)

git filter-repo --force --refs main --invert-paths --path Evaluation --path Training --path IFC-Modelle --path .cache_material_index --path Matching-MTH-clean
git filter-repo --force --refs main --invert-paths --path-glob '*.png' --path-glob '*.ico' --path-glob '*.icns'

4. Immer alles committen und auf Hugging Face Space pushen

git add -A
git commit -m "update: <kurze beschreibung>"
git push hf-space main:main

Falls der Remote-Branch absichtlich ersetzt werden soll:

git push --force hf-space main:main

5. GitHub origin angleichen

git fetch origin main
git push --force-with-lease origin main:main

6. Build-Logs pruefen

https://huggingface.co/spaces/Hygros-LCA/ifc-kbob-ai-matcher?logs=build

Hinweis:
Wenn HF "binary files" meldet, die gemeldeten Pfade mit git filter-repo aus der Historie entfernen oder diese Dateitypen sauber ueber Xet/LFS verwalten.

7. Headless Betrieb in HF Space (ohne Tkinter)

Die bisherigen Dateidialoge wurden entfernt. In HF Space und Streamlit gibt es keine GUI-Fenster.
Diese Skripte erwarten jetzt immer einen Pfad als CLI-Argument:

python run_ifc_sbert_pipeline.py <path_to_ifc>
python -m core.ifc_extraction.ifc_export_simple <path_to_ifc>
python core/calculate_ubp21_per_element.py <path_to_jsonl> [export_dir]

Wenn kein Argument angegeben ist oder der Pfad nicht existiert, brechen die Skripte mit Usage- bzw. File-not-found-Meldung ab.
