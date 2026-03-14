import os
import sys
import subprocess

# Schritt 2: IFC-Export als Subprozess aufrufen
def run_ifc_export(ifc_path):
    project_root = os.path.dirname(__file__)
    print(f"Starte IFC-Export für: {ifc_path}")
    result = subprocess.run(
        [sys.executable, "-m", "core.ifc_extraction.ifc_extraction_main", ifc_path],
        capture_output=True, text=True, cwd=project_root,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("Fehler beim IFC-Export:")
        print(result.stderr)
        sys.exit(1)


# Aus dem IFC-Dateipfad den zugehörigen JSONL-Pfad ableiten
def get_jsonl_path_from_ifc(ifc_path):
    base = os.path.splitext(os.path.basename(ifc_path))[0]
    directory = os.path.dirname(ifc_path)
    return os.path.join(directory, base + ".jsonl")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_ifc_sbert_pipeline.py <path_to_ifc>")
        sys.exit(1)

    ifc_path = sys.argv[1]
    if not os.path.isfile(ifc_path):
        print(f"IFC file not found: {ifc_path}")
        sys.exit(1)

    print(f"IFC file from argument: {ifc_path}")
    run_ifc_export(ifc_path)
    jsonl_path = get_jsonl_path_from_ifc(ifc_path)
    print(f"Verwende JSONL-Datei: {jsonl_path}")
    from core.sbert.sentence_transformer import run_sbert_matching
    run_sbert_matching(jsonl_path)

if __name__ == "__main__":
    main()


