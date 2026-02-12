"""
Reine Exportfunktionen für Datenformate (JSONL, TXT).
Diese Datei enthält KEINE IFC-Logik oder Felddefinitionen.
"""

import json

def export_list_of_dicts_to_jsonl(dict_list, output_path):
    """Exportiert eine Liste von Dictionaries als JSONL-Datei."""
    with open(output_path, "w", encoding="utf-8") as f:
        for obj in dict_list:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"Export abgeschlossen: {output_path}")
    return output_path

def export_list_of_strings_to_txt(string_list, output_path):
    """Exportiert eine Liste von Strings als TXT-Datei (eine Zeile pro String)."""
    with open(output_path, "w", encoding="utf-8") as f:
        for line in string_list:
            f.write(line + "\n")
    print(f"Fertig! {len(string_list)} Zeilen in {output_path} gespeichert.")
    return output_path
