import sqlite3
import json
import sys
import os
import tkinter as tk
from tkinter import filedialog

# --- Konfiguration ---
DATABASE_PATH = os.environ.get("KBOB_DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "Ökobilanzdaten.sqlite3"))
TABLE_NAME = "Oekobilanzdaten"

COLUMN_UUID = "UUID"
COLUMN_MATERIAL = "Material"
COLUMN_DENSITY = "Rohdichte"
COLUMN_BEZUG = "Bezug"
COLUMN_UNIT = "Einheit"

# Spalten, die keine Berechnungsspalten sind und beim dynamischen Abruf ignoriert werden
METADATA_COLUMNS = {COLUMN_UUID, COLUMN_MATERIAL, COLUMN_DENSITY, COLUMN_BEZUG, COLUMN_UNIT}

DEFAULT_EXPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "IFC-Modelle",
    "Resultate_UBP_Berechnung",
)

KG_DIRECT_FIELDS = [
    "Masse",
    "Mass",
    "Weight",
    "NetWeight",
    "GrossWeight",
    "Menge",
]

# Schichtdicken-Regeln für IfcCovering (Keyword -> Dicke in Meter).
# Keywords werden gegen Description, Name und Material (lowercase) geprüft.
# Reihenfolge ist relevant: erster Treffer gewinnt.
COVERING_THICKNESS_RULES = [
    # Epoxidharzversiegelung: 0.5–1.0 mm -> Mittelwert 0.75 mm
    (["epoxid", "epoxy"], 0.00075),
    # PBD-Abdichtung (PMMA, PUR, Polyurethan, Methylmethacrylat): 2–4 mm -> 3 mm
    (["pmma", "pur", "polyurethan", "polyurethane", "methylmethacrylat", "pbd", "pbma"], 0.003),
    # Flüssigkunststoff-Abdichtung (FLK): 2–4 mm -> 3 mm
    (["flk", "fl\u00fcssigkunststoff", "fl\u00fcssig", "fluessigkunststoff", "fluessig"], 0.003),
]
COVERING_THICKNESS_DEFAULT = 0.003  # 3 mm Fallback


def _to_float(value):
    try:
        return float(value) if value is not None else None
    except Exception:
        return None


def _first_numeric(entry, keys):
    for key in keys:
        if key in entry:
            value = _to_float(entry.get(key))
            if value is not None:
                return value
    return None


def _get_covering_thickness(entry):
    """Bestimmt die Schichtdicke (in Meter) für ein IfcCovering-Element anhand von
    Keyword-Matching auf Description, Name und Material."""
    search_fields = [
        entry.get("Description") or "",
        entry.get("Name") or "",
    ]
    mat = entry.get("Material") or ""
    if isinstance(mat, list):
        search_fields += [str(m) for m in mat]
    else:
        search_fields.append(str(mat))

    combined = " ".join(search_fields).lower()

    for keywords, thickness in COVERING_THICKNESS_RULES:
        if any(kw in combined for kw in keywords):
            return thickness
    return COVERING_THICKNESS_DEFAULT


def _create_result_table(cursor, columns):
    col_defs = ", ".join(
        [
            f"[{col}] REAL" if col not in ["GUID", "MaterialLayerIndex", "Material (KBOB)", "Bezugsgrösse", "Fehlende Berechnungsgrundlage"] else f"[{col}] TEXT"
            for col in columns
        ]
    )
    cursor.execute(f"CREATE TABLE Resultate ({col_defs})")
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_resultate_guid_layer "
        "ON Resultate([GUID], [MaterialLayerIndex])"
    )


def _ensure_result_table_schema(cursor, columns):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Resultate'")
    exists = cursor.fetchone() is not None
    if not exists:
        _create_result_table(cursor, columns)
        return

    cursor.execute("PRAGMA table_info(Resultate)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if existing_cols != columns:
        cursor.execute("DROP TABLE Resultate")
        _create_result_table(cursor, columns)
        return

    cursor.execute("PRAGMA index_list(Resultate)")
    existing_index_names = [row[1] for row in cursor.fetchall()]
    if "idx_resultate_guid" in existing_index_names:
        cursor.execute("DROP INDEX IF EXISTS idx_resultate_guid")

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_resultate_guid_layer "
        "ON Resultate([GUID], [MaterialLayerIndex])"
    )


def _determine_reference_value(entry, material, material_vals):
    ifc_entity = str(entry.get("IfcEntity") or "").strip().lower()
    bezug = str(material_vals.get(COLUMN_BEZUG) or "").strip().lower()
    net_volume = entry.get("NetVolume")
    gross_volume = entry.get("GrossVolume")
    preferred_volume = net_volume if _to_float(net_volume) is not None else gross_volume
    length = entry.get("Length")
    ansichtsfläche = entry.get("Ansichtsfläche")

    # IfcCovering: synthetisches Volumen aus NetArea × Schichtdicke
    if ifc_entity == "ifccovering" and _to_float(preferred_volume) is None:
        net_area = _to_float(entry.get("NetArea"))
        if net_area is not None:
            thickness = _get_covering_thickness(entry)
            preferred_volume = net_area * thickness

    if ifc_entity == "ifcreinforcingbar":
        weight = _first_numeric(entry, ["Weight", "Weight [kg]"])
        count = _first_numeric(entry, ["Count"])
        if weight is not None and count is not None:
            return "Masse (kg)", weight * count, None
        if weight is None:
            return "Masse (kg)", None, "Masse fehlt für IfcReinforcingBar"
        return "Masse (kg)", None, "Anzahl fehlt für IfcReinforcingBar"

    if bezug == "m":
        value = _to_float(length)
        reason = None if value is not None else "Länge fehlt"
        return "Length", value, reason

    if bezug == "m2":
        value = _to_float(ansichtsfläche)
        reason = None if value is not None else "Ansichtsfläche fehlt"
        return "Ansichtsfläche", value, reason

    if bezug == "kg":
        for field in KG_DIRECT_FIELDS:
            direct_mass = _to_float(entry.get(field))
            if direct_mass is not None:
                return "Masse (kg)", direct_mass, None

        density_num = _to_float(material_vals.get(COLUMN_DENSITY))
        net_volume_num = _to_float(preferred_volume)
        if density_num is not None and net_volume_num is not None:
            return "Masse (kg)", net_volume_num * density_num, None
        if net_volume_num is None:
            return "Masse (kg)", None, "Volumen fehlt für Umrechnung m3->kg"
        return "Masse (kg)", None, "Rohdichte fehlt in DB"

    # Default: m3 (Volumen)
    value = _to_float(preferred_volume)
    reason = None if value is not None else "Volumen fehlt"
    return "NetVolume", value, reason


def load_ifc_jsonl_entries(jsonl_path):
    entries = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def fetch_material_values_map(connection):
    cursor = connection.cursor()

    # Spaltennamen dynamisch aus der DB lesen
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    all_columns = [row[1] for row in cursor.fetchall()]
    columns_to_calc = [col for col in all_columns if col not in METADATA_COLUMNS]

    def safe_col(col):
        if any(c in col for c in " ()-[]"):
            return f'[{col}]'
        return col

    select_cols = ", ".join(
        [safe_col(COLUMN_MATERIAL)]
        + [safe_col(col) for col in columns_to_calc]
        + [safe_col(COLUMN_DENSITY), safe_col(COLUMN_BEZUG)]
    )
    cursor.execute(f"SELECT {select_cols} FROM {TABLE_NAME}")
    result = {}
    for row in cursor.fetchall():
        material = row[0]
        values = dict(zip(columns_to_calc + [COLUMN_DENSITY, COLUMN_BEZUG], row[1:]))
        result[material] = values
    return result, columns_to_calc


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
        material_values, columns_to_calc = fetch_material_values_map(connection)

    results = []
    export_db_path = _resolve_export_db_path(jsonl_path, export_dir)
    for entry in entries:
        guid = entry.get("GUID")
        layer_index = entry.get("MaterialLayerIndex")
        material = _normalize_material(_select_material(entry))
        material_vals = material_values.get(material, {})
        net_volume = entry.get("NetVolume")
        gross_volume = entry.get("GrossVolume")
        preferred_volume = net_volume if _to_float(net_volume) is not None else gross_volume
        length = entry.get("Length")
        ansichtsfläche = entry.get("Ansichtsfläche")
        net_area = entry.get("NetArea")
        count = entry.get("Count")
        weight = entry.get("Weight") if "Weight" in entry else entry.get("Weight [kg]")
        value_label, value_num, missing_reason = _determine_reference_value(entry, material, material_vals)

        export_row = {
            "GUID": guid,
            "MaterialLayerIndex": layer_index,
            "Material (KBOB)": material,
            "IfcEntity": entry.get("IfcEntity"),
            "Length": length,
            "Ansichtsfläche": ansichtsfläche,
            "NetArea": net_area,
            "NetVolume": preferred_volume,
            "GrossVolume": gross_volume,
            "Count": count,
            "Weight": weight,
            "Masse (kg)": value_num if value_label == "Masse (kg)" else None,
            "Bezugsgröße": value_label,
            "Berechnungswert": value_num,
            "Fehlende Berechnungsgrundlage": missing_reason,
        }
        for col in columns_to_calc:
            db_val = material_vals.get(col)
            db_val_num = _to_float(db_val)
            if value_num is not None and db_val_num is not None:
                export_row[col] = round(value_num * db_val_num, 0)
            else:
                export_row[col] = None
        results.append(export_row)

    # --- Synthetische Bewehrungszeilen (reinforcement assumptions) ---
    rebar_material_name = "Armierungsstahl"
    rebar_material_vals = material_values.get(rebar_material_name, {})
    for entry in entries:
        if not entry.get("reinforcement_accepted"):
            continue
        ratio = _to_float(entry.get("reinforcement_ratio_kg_m3"))
        if ratio is None or ratio <= 0:
            continue
        net_volume = _to_float(entry.get("NetVolume"))
        gross_volume = _to_float(entry.get("GrossVolume"))
        volume = net_volume if net_volume is not None else (gross_volume if gross_volume is not None else None)
        if volume is None or volume <= 0:
            continue
        rebar_mass = volume * ratio
        guid = entry.get("GUID")

        rebar_row = {
            "GUID": guid,
            "MaterialLayerIndex": "R",
            "Material (KBOB)": rebar_material_name,
            "IfcEntity": entry.get("IfcEntity"),
            "Length": None,
            "Ansichtsfläche": None,
            "NetArea": None,
            "NetVolume": volume,
            "GrossVolume": entry.get("GrossVolume"),
            "Count": None,
            "Weight": None,
            "Masse (kg)": rebar_mass,
            "Bezugsgröße": "Masse (kg)",
            "Berechnungswert": rebar_mass,
            "Fehlende Berechnungsgrundlage": None,
        }
        for col in columns_to_calc:
            db_val = rebar_material_vals.get(col)
            db_val_num = _to_float(db_val)
            if db_val_num is not None:
                rebar_row[col] = round(rebar_mass * db_val_num, 0)
            else:
                rebar_row[col] = None
        results.append(rebar_row)

    conn = sqlite3.connect(export_db_path)
    cursor = conn.cursor()
    if results:
        columns = list(results[0].keys())
        _ensure_result_table_schema(cursor, columns)

        for row in results:
            values = [row.get(col, None) for col in columns]
            placeholders = ", ".join(["?" for _ in columns])
            col_list = ", ".join([f"[{col}]" for col in columns])
            update_clause = ", ".join(
                [
                    f"[{col}]=excluded.[{col}]"
                    for col in columns
                    if col not in {"GUID", "MaterialLayerIndex"}
                ]
            )
            cursor.execute(
                f"INSERT INTO Resultate ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT([GUID], [MaterialLayerIndex]) DO UPDATE SET {update_clause}",
                values,
            )
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
