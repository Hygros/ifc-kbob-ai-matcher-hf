import os
import sys
import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.unit
from ifc_material_extract_util import extract_materials
import json

# --- Einheiten-Handling ---
def get_ifc_units(model):
    """Liest Skalierungsfaktoren für Länge/Fläche/Volumen aus dem IFC-Modell.

    Rückgabe: Dict mit Faktoren, um von Projekt-Einheiten nach SI zu konvertieren:
      value_in_si = value_in_ifc * factor

    Nutzt ifcopenshell.util.unit.calculate_unit_scale(), das auch
    ConversionBasedUnits besser abdeckt als ein reines Prefix-Mapping.
    """
    units = {}
    for unit_type in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT"):
        try:
            units[unit_type] = ifcopenshell.util.unit.calculate_unit_scale(model, unit_type)
        except Exception:
            units[unit_type] = 1.0
    return units

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

def extract_fields_from_psets(pset_dict, wanted_fields, default=None):
    extracted = {}
    for field in wanted_fields:
        value = default
        for _, sub_dict in pset_dict.items():
            if isinstance(sub_dict, dict) and field in sub_dict:
                value = sub_dict[field]
                break
        extracted[field] = value
    return extracted


# clean_value wird für generische Felder verwendet, aber für Längen/Volumen/Durchmesser gibt es jetzt clean_and_convert_value
def clean_value(val, field=None):
    if isinstance(val, list):
        val = ", ".join(str(v) for v in val if v)
    if val is None or str(val).strip() == "" or str(val).strip() == "NOTDEFINED":
        return None
    return str(val).strip()

def clean_and_convert_value(val, field, units):
    if val is None or str(val).strip() == "" or str(val).strip() == "NOTDEFINED":
        return None
    try:
        fval = float(val)
    except Exception:
        return str(val).strip()
    # Längenfelder in Meter
    if field == "Length":
        length_factor = units.get("LENGTHUNIT", 1.0)
        return round(fval * length_factor, 6)
    # Volumenfelder in m³
    if field == "NetVolume":
        volume_factor = units.get("VOLUMEUNIT", 1.0)
        return round(fval * volume_factor, 9)
    # Flächenfelder in m² (optional, falls benötigt)
    if field == "AREA_PROJECTION_XY_NET":
        area_factor = units.get("AREAUNIT", 1.0)
        return round(fval * area_factor, 6)
    # Durchmesser in mm
    if field == "Durchmesser":
        length_factor = units.get("LENGTHUNIT", 1.0)
        # Projekt-Länge -> Meter -> mm
        return str(int(round(fval * length_factor * 1000)))
    return str(val).strip()


if __name__ == "__main__":
    # IFC-Dateipfad als Argument erwarten
    if len(sys.argv) > 1:
        ifc_file_path = sys.argv[1]
    else:
        print("Usage: python IFC-extraction-main.py <path-to-ifc-file>")
        sys.exit(1)

    # Definiere, welche Eigenschaften aus den PropertySets extrahiert werden sollen
    property_fields = [
        "comment",
        "Description",
        "Status",
        "Durchmesser",
        "CastingMethod",
        "StructuralClass",
        "StrengthClass",
        "ExposureClass",
        "ReinforcementStrengthClass",
        "Length",
        "NetVolume",
        "Ansichtsfläche",
        "ReinforcementVolumeRatio",
    ]

    # Definiere, welche Felder in die TXT-Exportzeile aufgenommen werden
    export_fields_for_txt = [
        "IfcEntity",
        "PredefinedType",
        "Name",
        "Material",
        "comment",
        "Description",
        "Durchmesser",
        "CastingMethod",
        "StructuralClass",
        "StrengthClass",
        "ExposureClass",
        "ReinforcementStrengthClass"
    ]


    # Schritt 2: IFC öffnen und relevante Elemente extrahieren
    model = ifcopenshell.open(ifc_file_path)
    units = get_ifc_units(model)
    elements = [element for element in model.by_type("IfcElement") if element.is_a() not in ["IfcOpeningElement", "IfcElementAssembly"]]

    # Schritt 3: Für jedes Element relevante Felder extrahieren und Dictionary-Liste aufbauen
    export_dicts = []
    for element in elements:
        property_sets = ifcopenshell.util.element.get_psets(element)
        ifc_entity = element.is_a() if hasattr(element, 'is_a') else None
        name = getattr(element, 'Name', None)
        predefined_type = getattr(element, 'PredefinedType', None)
        guid = element.GlobalId if hasattr(element, 'GlobalId') else None
        description = getattr(element, "Description", None)
        extracted_properties = extract_fields_from_psets(property_sets, property_fields)
        # Konvertiere relevante Felder
        for key in ["Length", "NetVolume", "Durchmesser"]:
            if key in extracted_properties and extracted_properties[key] is not None:
                extracted_properties[key] = clean_and_convert_value(extracted_properties[key], key, units)
        filtered_properties = {key: value for key, value in extracted_properties.items() if value not in (None, "", [], {})}
        materials = extract_materials(model, element)
        material_names = [m["Name"] for m in materials if "Name" in m]
        element_dict = {
            "IfcEntity": ifc_entity,
            "PredefinedType": predefined_type,
            "Name": name,
            "Description": description,
            "Material": material_names,
            "GUID": guid,
            **filtered_properties
        }
        # Entferne leere Felder
        element_dict = {k: v for k, v in element_dict.items() if v not in (None, "", [], {})}
        export_dicts.append(element_dict)

    # Schritt 4: Exportiere als JSONL
    base_filename = os.path.splitext(os.path.basename(ifc_file_path))[0]
    output_directory = os.path.dirname(ifc_file_path)
    jsonl_export_path = os.path.join(output_directory, base_filename + ".jsonl")
    export_list_of_dicts_to_jsonl(export_dicts, jsonl_export_path)

    # Schritt 5: Erzeuge String-Liste für TXT-Export
    export_lines = []
    for element_dict in export_dicts:
        values = [clean_value(element_dict.get(field, ""), field) for field in export_fields_for_txt]
        values = [v for v in values if v]
        if values:
            line = " ; ".join(values)
            export_lines.append(line)

    txt_export_path = os.path.join(output_directory, base_filename + ".txt")
    export_list_of_strings_to_txt(export_lines, txt_export_path)

    print("Beide Exporte abgeschlossen.")

