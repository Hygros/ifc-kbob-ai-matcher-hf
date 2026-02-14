import os
import sys
import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.unit
from ifc_material_extract_util import extract_materials
import json


NO_AGGREGATES_ALLOWED_SUBENTITY_TYPES = {"IfcCovering", "IfcReinforcingBar"}

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


def _obj_id(obj):
    return obj.id() if hasattr(obj, "id") else id(obj)


def _rel_related_objects(rels, rel_type, related_attr):
    result = []
    seen = set()
    for rel in rels or []:
        if rel_type and hasattr(rel, "is_a") and not rel.is_a(rel_type):
            continue
        for obj in getattr(rel, related_attr, []) or []:
            obj_id = _obj_id(obj)
            if obj_id in seen:
                continue
            seen.add(obj_id)
            result.append(obj)
    return result


def _get_aggregate_children(obj):
    return _rel_related_objects(getattr(obj, "IsDecomposedBy", []), "IfcRelAggregates", "RelatedObjects")


def _is_allowed_no_aggregates_subentity(element):
    if not hasattr(element, "is_a"):
        return False
    return any(element.is_a(entity_type) for entity_type in NO_AGGREGATES_ALLOWED_SUBENTITY_TYPES)


def _build_no_aggregates_elements(elements):
    elements_by_id = {_obj_id(element): element for element in elements}

    def _aggregate_parent_elements(element):
        parents = []
        for rel in getattr(element, "Decomposes", []) or []:
            if not (hasattr(rel, "is_a") and rel.is_a("IfcRelAggregates")):
                continue
            parent = getattr(rel, "RelatingObject", None)
            if parent is None:
                continue
            parent_id = _obj_id(parent)
            if parent_id in elements_by_id:
                parents.append(elements_by_id[parent_id])
        return parents

    roots = [element for element in elements if not _aggregate_parent_elements(element)]

    selected = {}

    def _select_for_export(element, active_path):
        element_id = _obj_id(element)
        if element_id in active_path:
            selected[element_id] = element
            return

        next_path = set(active_path)
        next_path.add(element_id)

        aggregate_children = [
            child for child in _get_aggregate_children(element) if _obj_id(child) in elements_by_id
        ]
        exception_children = [
            child for child in aggregate_children if _is_allowed_no_aggregates_subentity(child)
        ]
        non_exception_children = [
            child for child in aggregate_children if not _is_allowed_no_aggregates_subentity(child)
        ]

        for child in exception_children:
            selected[_obj_id(child)] = child

        if len(non_exception_children) == 1:
            _select_for_export(non_exception_children[0], next_path)
            return

        selected[element_id] = element

    for root in roots:
        _select_for_export(root, set())

    for element in elements:
        if _is_allowed_no_aggregates_subentity(element):
            selected[_obj_id(element)] = element

    return list(selected.values())


def _is_exportable_ifc_element(element):
    return element.is_a() not in {"IfcOpeningElement", "IfcElementAssembly"}

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


def build_export_dicts(model, elements, property_fields, units):
    export_dicts = []
    for element in elements:
        property_sets = ifcopenshell.util.element.get_psets(element)
        ifc_entity = element.is_a() if hasattr(element, 'is_a') else None
        name = getattr(element, 'Name', None)
        predefined_type = getattr(element, 'PredefinedType', None)
        guid = element.GlobalId if hasattr(element, 'GlobalId') else None
        description = getattr(element, "Description", None)
        extracted_properties = extract_fields_from_psets(property_sets, property_fields)
        if ifc_entity == "IfcReinforcingBar":
            reinforcing_bar_fields = extract_fields_from_psets(property_sets, ["Count", "Weight"])
            extracted_properties.update(reinforcing_bar_fields)
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
        element_dict = {k: v for k, v in element_dict.items() if v not in (None, "", [], {})}
        export_dicts.append(element_dict)
    return export_dicts


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
        "Durchmesser",               # nicht nach IFC-Schema
        "CastingMethod",
        "StructuralClass",
        "StrengthClass",
        "ExposureClass",
        "ReinforcementStrengthClass",
        "Length",
        "NetVolume",
        "Ansichtsfläche",           # nicht nach IFC-Schema
        "ReinforcementVolumeRatio",
    ]

    # Schritt 2: IFC öffnen und relevante Elemente extrahieren
    model = ifcopenshell.open(ifc_file_path)
    units = get_ifc_units(model)
    elements = [element for element in model.by_type("IfcElement") if _is_exportable_ifc_element(element)]
    elements_no_aggregates = _build_no_aggregates_elements(elements)
    elements_no_aggregates = [element for element in elements_no_aggregates if _is_exportable_ifc_element(element)]

    # Schritt 3: Relevante Felder aus Aggregationslogik-Elementen extrahieren
    export_dicts = build_export_dicts(model, elements_no_aggregates, property_fields, units)

    # Schritt 4: Exportiere als JSONL
    base_filename = os.path.splitext(os.path.basename(ifc_file_path))[0]
    output_directory = os.path.dirname(ifc_file_path)
    jsonl_export_path = os.path.join(output_directory, base_filename + ".jsonl")
    export_list_of_dicts_to_jsonl(export_dicts, jsonl_export_path)

    print("JSONL-Export abgeschlossen.")

