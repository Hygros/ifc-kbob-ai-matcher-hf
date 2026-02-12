import sqlite3
import json
import sys
import os
import tkinter as tk
from tkinter import filedialog

# --- Konfiguration ---
DATABASE_PATH = r"C:\Users\wpx619\AAA_Python_MTH\Ökobilanzdaten.sqlite3"
TABLE_NAME = "Oekobilanzdaten"
COLUMN_MATERIAL = "Material"
# Alle relevanten Spalten für Berechnung
COLUMNS_TO_CALC = [
    "UBP21Total",
    "UBP21Herstellung",
    "UBP21Entsorgung",
    "PrimärenergiegesamtTotalkWhoil-eq",
    "PrimärenergiegesamtHerstellungtotalkWhoil-eq",
    "PrimärenergiegesamtEntsorgungkWhoil-eq",
    "PrimärenergiegesamtHerstellungenergetischgenutztkWhoil-eq",
    "PrimärenergiegesamtHerstellungstofflichgenutztkWhoil-eq",
    "PrimärenergieerneuerbarTotalkWhoil-eq",
    "PrimärenergieerneuerbarHerstellungtotalkWhoil-eq",
    "PrimärenergieerneuerbarHerstellungenergetischgenutztkWhoil-eq",
    "PrimärenergieerneuerbarHerstellungstofflichgenutztkWhoil-eq",
    "nichterneuerbar(GraueEnergie)TotalkWhoil-eq",
    "nichterneuerbar(GraueEnergie)HerstellungtotalkWhoil-eq",
    "nichterneuerbar(GraueEnergie)HerstellungenergetischgenutztkWhoil-eq",
    "nichterneuerbar(GraueEnergie)HerstellungstofflichgenutztkWhoil-eq",
    "nichterneuerbar(GraueEnergie)EntsorgungkWhoil-eq",
    "TreibhausgasemissionenTotalkgCO2-eq",
    "TreibhausgasemissionenHerstellungkgCO2-eq",
    "TreibhausgasemissionenEntsorgungkgCO2-eq",
    "BiogenerKohlenstoffimProduktenthaltenkgC"
]

DEFAULT_EXPORT_DIR = os.path.join(
    os.path.dirname(__file__),
    "IFC-Modelle",
    "Resultate_UBP_Berechnung",
)


def load_ifc_jsonl_entries(jsonl_path):
    entries = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def fetch_material_values_map(connection):
    cursor = connection.cursor()
    # Füge eckige Klammern um Spaltennamen mit Sonderzeichen
    def safe_col(col):
        if any(c in col for c in " ()-[]"):  # SQLite: Klammern, Bindestrich, Leerzeichen
            return f'[{col}]'
        return col
    columns = ", ".join([safe_col(COLUMN_MATERIAL)] + [safe_col(col) for col in COLUMNS_TO_CALC])
    cursor.execute(f"SELECT {columns} FROM {TABLE_NAME}")
    result = {}
    for row in cursor.fetchall():
        material = row[0]
        values = dict(zip(COLUMNS_TO_CALC, row[1:]))
        result[material] = values
    return result


def load_material_mapping(jsonl_path):
    # Annahme: Das Materialfeld in der JSONL ist ein String oder eine Liste von Strings
    entries = load_ifc_jsonl_entries(jsonl_path)
    mapping = {}
    for entry in entries:
        guid = entry.get("GUID")
        material = entry.get("Material")
        if isinstance(material, list):
            material = ", ".join([str(m) for m in material if m])
        mapping[guid] = material
    return mapping


def _normalize_material(value):
    if isinstance(value, list):
        return ", ".join([str(v) for v in value if v])
    return value


def _select_material(entry):
    return (
        entry.get("selected_kbob_material")
        or entry.get("best_match_material")
        or entry.get("Material")
    )


def _resolve_export_db_path(jsonl_path, export_dir):
    jsonl_basename = os.path.splitext(os.path.basename(jsonl_path))[0]
    export_root = export_dir or DEFAULT_EXPORT_DIR
    os.makedirs(export_root, exist_ok=True)
    return os.path.join(export_root, jsonl_basename + ".sqlite3")


def calculate_ubp_for_jsonl(jsonl_path, export_dir=None, database_path=DATABASE_PATH):
    entries = load_ifc_jsonl_entries(jsonl_path)
    with sqlite3.connect(database_path) as connection:
        material_values = fetch_material_values_map(connection)

    results = []
    export_db_path = _resolve_export_db_path(jsonl_path, export_dir)
    length_materials = {
        "Tiefgründung Mikrobohrpfahl",
        "Tiefgründung Ortbetonbohrpfahl 700",
        "Tiefgründung Ortbetonbohrpfahl 900",
        "Tiefgründung Ortbetonbohrpfahl 1200",
        "Tiefgründung Ortbetonverdrängungspfahl 560/480 mm",
        "Tiefgründung Ortbetonverdrängungspfahl 660/580 mm",
        "Tiefgründung Rüttelstopfsäule",
        "Tiefgründung Vorgefertigter Betonpfahl",
    }
    ansichtsfläche_materials = {
        "Baugrubensicherung Bohrpfahlwand gespriesst",
        "Baugrubensicherung Bohrpfahlwand unverankert",
        "Baugrubensicherung Bohrpfahlwand verankert",
        "Baugrubensicherung Nagelwand",
        "Baugrubensicherung Rühlwand auskragend",
        "Baugrubensicherung Rühlwand gespriesst",
        "Baugrubensicherung Rühlwand verankert",
        "Baugrubensicherung Schlitzwand 400",
        "Baugrubensicherung Schlitzwand 800",
        "Baugrubensicherung Spundwand auskragend",
        "Baugrubensicherung Spundwand gespriesst",
        "Baugrubensicherung Spundwand verankert",
    }

    for entry in entries:
        guid = entry.get("GUID")
        material = _normalize_material(_select_material(entry))
        material_vals = material_values.get(material, {})
        if material in length_materials:
            value_for_calc = entry.get("Length")
            value_label = "Length"
        elif material in ansichtsfläche_materials:
            value_for_calc = entry.get("Ansichtsfläche")
            value_label = "Ansichtsfläche"
        else:
            value_for_calc = entry.get("NetVolume")
            value_label = "NetVolume"
        try:
            value_num = float(value_for_calc) if value_for_calc is not None else None
        except Exception:
            value_num = None

        export_row = {
            "GUID": guid,
            "Material (KBOB)": material,
            value_label: value_for_calc,
        }
        for col in COLUMNS_TO_CALC:
            db_val = material_vals.get(col)
            try:
                db_val_num = float(db_val) if db_val is not None else None
            except Exception:
                db_val_num = None
            if value_num is not None and db_val_num is not None:
                export_row[col] = round(value_num * db_val_num, 0)
            else:
                export_row[col] = None
        results.append(export_row)

    conn = sqlite3.connect(export_db_path)
    cursor = conn.cursor()
    if results:
        columns = list(results[0].keys())
        col_defs = ", ".join(
            [
                f"[{col}] REAL" if col not in ["GUID", "Material (KBOB)"] else f"[{col}] TEXT"
                for col in columns
            ]
        )
        cursor.execute(f"CREATE TABLE IF NOT EXISTS Resultate ({col_defs})")

        cursor.execute("PRAGMA table_info(Resultate)")
        table_cols = [row[1] for row in cursor.fetchall()]
        has_length = "Length" in table_cols
        has_ansichtsfläche = "Ansichtsfläche" in table_cols

        for row in results:
            guid = str(row.get("GUID", ""))
            material_kbob = str(row.get("Material (KBOB)", ""))
            length_val = str(row.get("Length", ""))
            ansichtsfläche_val = str(row.get("Ansichtsfläche", ""))
            select_cols = ["[Material (KBOB)]"]
            if has_length:
                select_cols.append("[Length]")
            if has_ansichtsfläche:
                select_cols.append("[Ansichtsfläche]")
            select_stmt = f"SELECT {', '.join(select_cols)} FROM Resultate WHERE [GUID]=?"
            cursor.execute(select_stmt, (guid,))
            existing = cursor.fetchone()
            values = [row.get(col, None) for col in columns]
            placeholders = ", ".join(["?" for _ in columns])
            if existing:
                if has_length and has_ansichtsfläche:
                    existing_material, existing_length, existing_ansichtsfläche = existing
                elif has_length:
                    existing_material, existing_length = existing
                    existing_ansichtsfläche = ""
                elif has_ansichtsfläche:
                    existing_material, existing_ansichtsfläche = existing
                    existing_length = ""
                else:
                    existing_material = existing[0]
                    existing_length = ""
                    existing_ansichtsfläche = ""
                changed = False
                if material_kbob != existing_material:
                    changed = True
                if length_val and length_val != existing_length:
                    changed = True
                if ansichtsfläche_val and ansichtsfläche_val != existing_ansichtsfläche:
                    changed = True
                if changed:
                    set_clause = ", ".join([f"[{col}]=?" for col in columns])
                    cursor.execute(
                        f"UPDATE Resultate SET {set_clause} WHERE [GUID]=?",
                        values + [guid],
                    )
                else:
                    pass
            else:
                cursor.execute(f"INSERT INTO Resultate VALUES ({placeholders})", values)
        conn.commit()
    conn.close()
    return export_db_path, results



def main():
    # GUI-Dialog zur Auswahl der JSONL-Datei
    root = tk.Tk()
    root.withdraw()
    jsonl_path = filedialog.askopenfilename(title="Wähle IFC-Export JSONL", filetypes=[("JSONL files", "*.jsonl")])
    root.destroy()
    if not jsonl_path:
        print("Keine Datei ausgewählt. Beende.")
        sys.exit(1)

    export_db_path, _ = calculate_ubp_for_jsonl(jsonl_path)
    print(f"Export abgeschlossen: {export_db_path}")

if __name__ == "__main__":
    main()
