import os
import ifcopenshell
import ifcopenshell.util.element
from ifc_material_extract_util import extract_materials
import csv
import sys

# --- Einheiten-Handling ---
def get_ifc_units(model):
    prefix_factors = {
        "MILLI": 0.001,
        "CENTI": 0.01,
        "DECI": 0.1,
        "NONE": 1.0,
        None: 1.0
    }
    units = {"LENGTHUNIT": ("METRE", 1.0), "VOLUMEUNIT": ("CUBIC_METRE", 1.0), "AREAUNIT": ("SQUARE_METRE", 1.0)}
    for assignment in model.by_type("IfcUnitAssignment"):
        for unit in assignment.Units:
            if hasattr(unit, 'UnitType') and unit.UnitType in ("LENGTHUNIT", "VOLUMEUNIT", "AREAUNIT"):
                name = getattr(unit, 'Name', None)
                prefix = getattr(unit, 'Prefix', None)
                name_str = str(name) if name is not None else ""
                factor = prefix_factors.get(prefix, 1.0)
                units[unit.UnitType] = (name_str, factor)
    return units

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
    if field == "Length":
        length_unit, length_factor = units.get("LENGTHUNIT", ("METRE", 1.0))
        return round(fval * length_factor, 6)
    if field == "NetVolume":
        volume_unit, volume_factor = units.get("VOLUMEUNIT", ("CUBIC_METRE", 1.0))
        return round(fval * volume_factor, 9)
    if field == "AREA_PROJECTION_XY_NET":
        area_unit, area_factor = units.get("AREAUNIT", ("SQUARE_METRE", 1.0))
        return round(fval * area_factor, 6)
    if field == "Durchmesser":
        length_unit, length_factor = units.get("LENGTHUNIT", ("METRE", 1.0))
        return str(int(round(fval * length_factor * 1000)))
    return str(val).strip()

def process_ifc_file(ifc_file_path, property_fields, export_fields_for_csv):
    model = ifcopenshell.open(ifc_file_path)
    units = get_ifc_units(model)
    elements = [element for element in model.by_type("IfcElement") if element.is_a() not in ["IfcOpeningElement", "IfcElementAssembly"]]
    export_dicts = []
    for element in elements:
        property_sets = ifcopenshell.util.element.get_psets(element)
        ifc_entity = element.is_a() if hasattr(element, 'is_a') else None
        name = getattr(element, 'Name', None)
        predefined_type = getattr(element, 'PredefinedType', None)
        guid = element.GlobalId if hasattr(element, 'GlobalId') else None
        extracted_properties = extract_fields_from_psets(property_sets, property_fields)
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
            "Material": material_names,
            "GUID": guid,
            **filtered_properties
        }
        element_dict = {k: v for k, v in element_dict.items() if v not in (None, "", [], {})}
        export_dicts.append(element_dict)
    return export_dicts

def main():
    ifc_folder = r"C:\Users\wpx619\OneDrive - AFRY\BIM-VDC\Ifc_Files_Test"
    output_csv = os.path.join(ifc_folder, "ifc_elements_export.csv")
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
    export_fields_for_csv = [
        "IfcEntity",
        "PredefinedType",
        "Name",
        "Material",
        "GUID",
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
        "ReinforcementVolumeRatio"
    ]
    all_elements = []
    for filename in os.listdir(ifc_folder):
        if filename.lower().endswith(".ifc"):
            ifc_path = os.path.join(ifc_folder, filename)
            print(f"Verarbeite: {ifc_path}")
            elements = process_ifc_file(ifc_path, property_fields, export_fields_for_csv)
            for el in elements:
                el["SourceFile"] = filename
            all_elements.extend(elements)
    if not all_elements:
        print("Keine Elemente gefunden.")
        return
    with open(output_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["SourceFile"] + export_fields_for_csv)
        writer.writeheader()
        for el in all_elements:
            row = {k: clean_value(el.get(k, ""), k) for k in ["SourceFile"] + export_fields_for_csv}
            writer.writerow(row)
    print(f"Export abgeschlossen: {output_csv}")

if __name__ == "__main__":
    main()
