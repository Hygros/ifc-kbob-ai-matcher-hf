import os
import csv
import sys
import json
import argparse
from collections import Counter
from ifc_extraction_core import DEFAULT_PROPERTY_FIELDS, extract_export_dicts_from_ifc_file

def _stringify_for_csv(value):
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def _extract_material_values(raw_value):
    if isinstance(raw_value, list):
        if not raw_value:
            return [""]
        return ["" if value is None else str(value) for value in raw_value]
    if raw_value is None:
        return [""]
    return [str(raw_value)]


def _normalize_label(value):
    if value is None:
        return "UNDEFINED"
    label = str(value).strip()
    if label == "":
        return "UNDEFINED"
    if label.upper() in {"NOTDEFINED", "UNDEFINED", "NONE", "NULL", "N/A"}:
        return "UNDEFINED"
    return label


def _build_guid_based_keys(rows):
    row_keys = []
    fallback_counter = 0
    for row in rows:
        guid = row.get("GUID")
        if guid in (None, ""):
            fallback_counter += 1
            row_keys.append(f"__NO_GUID__::{row.get('SourceFile', '')}::{fallback_counter}")
        else:
            row_keys.append(str(guid))
    return row_keys


def _write_analysis_reports(all_rows, output_directory, analysis_prefix):
    if not all_rows:
        return

    row_keys = _build_guid_based_keys(all_rows)
    unique_guid_map = {}
    for row, row_key in zip(all_rows, row_keys):
        if row_key not in unique_guid_map:
            unique_guid_map[row_key] = row

    entity_counter = Counter()
    predefined_counter = Counter()
    for row in unique_guid_map.values():
        entity_counter[_normalize_label(row.get("IfcEntity"))] += 1
        predefined_counter[_normalize_label(row.get("PredefinedType"))] += 1

    material_counter = Counter()
    for row in all_rows:
        for material in _extract_material_values(row.get("Material")):
            material_counter[_normalize_label(material)] += 1

    guid_rows = list(unique_guid_map.items())
    entity_to_guid_keys = {}
    entity_predefined_to_guid_keys = {}
    entity_material_to_guid_keys = {}
    entity_predefined_material_to_guid_keys = {}

    for guid_key, row in guid_rows:
        entity = _normalize_label(row.get("IfcEntity"))
        predefined_type = _normalize_label(row.get("PredefinedType"))
        if entity not in entity_to_guid_keys:
            entity_to_guid_keys[entity] = set()
        entity_to_guid_keys[entity].add(guid_key)

        entity_predefined_key = (entity, predefined_type)
        if entity_predefined_key not in entity_predefined_to_guid_keys:
            entity_predefined_to_guid_keys[entity_predefined_key] = set()
        entity_predefined_to_guid_keys[entity_predefined_key].add(guid_key)

    for row, guid_key in zip(all_rows, row_keys):
        entity = _normalize_label(row.get("IfcEntity"))
        predefined_type = _normalize_label(row.get("PredefinedType"))
        for material in _extract_material_values(row.get("Material")):
            material_label = _normalize_label(material)
            entity_material_key = (entity, material_label)
            if entity_material_key not in entity_material_to_guid_keys:
                entity_material_to_guid_keys[entity_material_key] = set()
            entity_material_to_guid_keys[entity_material_key].add(guid_key)

            entity_predefined_material_key = (entity, predefined_type, material_label)
            if entity_predefined_material_key not in entity_predefined_material_to_guid_keys:
                entity_predefined_material_to_guid_keys[entity_predefined_material_key] = set()
            entity_predefined_material_to_guid_keys[entity_predefined_material_key].add(guid_key)

    summary_csv = os.path.join(output_directory, f"{analysis_prefix}_summary.csv")
    with open(summary_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["Metric", "Value"])
        writer.writeheader()
        writer.writerow({"Metric": "ExportRowsTotal", "Value": len(all_rows)})
        writer.writerow({"Metric": "UniqueElementsGuidBased", "Value": len(unique_guid_map)})
        writer.writerow({"Metric": "DistinctIfcEntity", "Value": len(entity_counter)})
        writer.writerow({"Metric": "DistinctPredefinedType", "Value": len(predefined_counter)})
        writer.writerow({"Metric": "DistinctMaterial", "Value": len(material_counter)})

    entity_csv = os.path.join(output_directory, f"{analysis_prefix}_ifcentity_counts.csv")
    with open(entity_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["IfcEntity", "CountGuidBased"])
        writer.writeheader()
        for ifc_entity, count in sorted(entity_counter.items(), key=lambda item: (-item[1], item[0])):
            writer.writerow({"IfcEntity": ifc_entity, "CountGuidBased": count})

    predefined_csv = os.path.join(output_directory, f"{analysis_prefix}_predefinedtype_counts.csv")
    with open(predefined_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["PredefinedType", "CountGuidBased"])
        writer.writeheader()
        for predefined_type, count in sorted(predefined_counter.items(), key=lambda item: (-item[1], item[0])):
            writer.writerow({"PredefinedType": predefined_type, "CountGuidBased": count})

    materials_csv = os.path.join(output_directory, f"{analysis_prefix}_materials.csv")
    with open(materials_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["Material", "CountRows"])
        writer.writeheader()
        for material, count in sorted(material_counter.items(), key=lambda item: (-item[1], item[0])):
            writer.writerow({"Material": material, "CountRows": count})

    entity_tree_csv = os.path.join(output_directory, f"{analysis_prefix}_entity_tree.csv")
    with open(entity_tree_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "IfcEntity",
                "IfcEntityCountGuidBased",
                "PredefinedType",
                "Material",
                "CountGuidBased",
            ],
        )
        writer.writeheader()
        combo_rows = []
        for (ifc_entity, predefined_type, material), guid_set in entity_predefined_material_to_guid_keys.items():
            combo_rows.append(
                {
                    "IfcEntity": ifc_entity,
                    "IfcEntityCountGuidBased": len(entity_to_guid_keys.get(ifc_entity, set())),
                    "PredefinedType": predefined_type,
                    "Material": material,
                    "CountGuidBased": len(guid_set),
                }
            )
        combo_rows.sort(
            key=lambda row: (
                -int(row["IfcEntityCountGuidBased"]),
                row["IfcEntity"],
                -int(row["CountGuidBased"]),
                row["PredefinedType"],
                row["Material"],
            )
        )
        for combo_row in combo_rows:
            writer.writerow(combo_row)

    print(f"Analyse abgeschlossen: {summary_csv}")
    print(f"Analyse abgeschlossen: {entity_csv}")
    print(f"Analyse abgeschlossen: {predefined_csv}")
    print(f"Analyse abgeschlossen: {materials_csv}")
    print(f"Analyse abgeschlossen: {entity_tree_csv}")


def _collect_export_fields(all_elements):
    default_order = [
        "IfcEntity",
        "PredefinedType",
        "Name",
        "Description",
        "Material",
        "MaterialLayerThickness",
        "MaterialLayerIndex",
        "GUID",
        "Status",
        "CastingMethod",
        "StructuralClass",
        "StrengthClass",
        "ExposureClass",
        "Length",
        "NetVolume",
        "GrossVolume",
        "Ansichtsfläche",
        "ReinforcementVolumeRatio",
        "Count",
        "Weight",
        "Durchmesser",
    ]

    discovered = set()
    for element in all_elements:
        discovered.update(element.keys())

    ordered = [field for field in default_order if field in discovered]
    ordered.extend(sorted(discovered - set(default_order)))
    return ordered

def main():
    parser = argparse.ArgumentParser(description="Batch IFC-Export mit gleicher Logik wie IFC-extraction-main.py")
    parser.add_argument("--ifc-folder", default=os.getcwd(), help="Ordner mit IFC-Dateien")
    parser.add_argument("--output-csv", default=None, help="Pfad zur aggregierten CSV-Ausgabe")
    parser.add_argument("--analysis-prefix", default="ifc_elements_analysis", help="Dateipräfix für Analyse-CSVs")
    args = parser.parse_args()

    ifc_folder = args.ifc_folder
    if not os.path.isdir(ifc_folder):
        print(f"Ordner nicht gefunden: {ifc_folder}")
        sys.exit(1)

    output_csv = args.output_csv or os.path.join(ifc_folder, "ifc_elements_export.csv")
    property_fields = list(DEFAULT_PROPERTY_FIELDS)

    all_elements = []
    for filename in os.listdir(ifc_folder):
        if filename.lower().endswith(".ifc"):
            ifc_path = os.path.join(ifc_folder, filename)
            print(f"Verarbeite: {ifc_path}")
            elements = extract_export_dicts_from_ifc_file(ifc_path, property_fields)
            for el in elements:
                el["SourceFile"] = filename
            all_elements.extend(elements)

    if not all_elements:
        print("Keine Elemente gefunden.")
        return

    export_fields_for_csv = _collect_export_fields(all_elements)
    with open(output_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["SourceFile"] + export_fields_for_csv)
        writer.writeheader()
        for el in all_elements:
            row = {k: _stringify_for_csv(el.get(k, "")) for k in ["SourceFile"] + export_fields_for_csv}
            writer.writerow(row)

    print(f"Export abgeschlossen: {output_csv}")
    _write_analysis_reports(all_elements, os.path.dirname(output_csv), args.analysis_prefix)

if __name__ == "__main__":
    main()
