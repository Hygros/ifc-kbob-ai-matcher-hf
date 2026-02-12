import os
import sys
import tkinter as tk
from tkinter import filedialog
import subprocess

# Schritt 1: IFC-Datei auswählen
def choose_ifc_file():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title="Select IFC file", filetypes=[("IFC files","*.ifc")])
    root.destroy()
    return path

# Schritt 2: IFC-Export als Subprozess aufrufen
def run_ifc_export(ifc_path):
    script_path = os.path.join(os.path.dirname(__file__), "IFC_Extraction", "IFC-extraction-main.py")
    if not os.path.exists(script_path):
        print(f"IFC-Export-Skript nicht gefunden: {script_path}")
        sys.exit(1)
    print(f"Starte IFC-Export für: {ifc_path}")
    result = subprocess.run([sys.executable, script_path, ifc_path], capture_output=True, text=True)
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
    if len(sys.argv) > 1:
        ifc_path = sys.argv[1]
        print(f"IFC file from argument: {ifc_path}")
    else:
        ifc_path = choose_ifc_file()
        if not ifc_path:
            print("No IFC file selected. Exiting.")
            sys.exit(1)
    print(f"Selected IFC file: {ifc_path}")
    run_ifc_export(ifc_path)
    jsonl_path = get_jsonl_path_from_ifc(ifc_path)
    print(f"Verwende JSONL-Datei: {jsonl_path}")
    from SBERT.Sentence_Transformer_V00 import run_sbert_matching
    run_sbert_matching(jsonl_path)

if __name__ == "__main__":
    main()


