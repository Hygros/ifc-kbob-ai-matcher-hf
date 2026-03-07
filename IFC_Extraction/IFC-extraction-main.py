
import os
import sys
import json
from ifc_extraction_core import DEFAULT_PROPERTY_FIELDS, extract_export_dicts_from_ifc_file


def export_list_of_dicts_to_jsonl(dict_list, output_path):
    """Exportiert eine Liste von Dictionaries als JSONL-Datei."""
    with open(output_path, "w", encoding="utf-8") as f:
        for obj in dict_list:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"Export abgeschlossen: {output_path}")
    return output_path

if __name__ == "__main__":
    # IFC-Dateipfad als Argument erwarten
    if len(sys.argv) > 1:
        ifc_file_path = sys.argv[1]
    else:
        print("Usage: python IFC_Extraction/IFC-extraction-main.py <path-to-ifc-file>")
        sys.exit(1)

    # Definiere, welche Eigenschaften aus den PropertySets extrahiert werden sollen
    property_fields = list(DEFAULT_PROPERTY_FIELDS)
    export_dicts = extract_export_dicts_from_ifc_file(ifc_file_path, property_fields)

    # Schritt 4: Exportiere als JSONL
    base_filename = os.path.splitext(os.path.basename(ifc_file_path))[0]
    output_directory = os.path.dirname(ifc_file_path)
    jsonl_export_path = os.path.join(output_directory, base_filename + ".jsonl")
    export_list_of_dicts_to_jsonl(export_dicts, jsonl_export_path)

    print("JSONL-Export abgeschlossen.")

