# 


import os
import sys
import math
import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.unit
from ifc_material_extract_util import extract_materials
import json


NO_AGGREGATES_ALLOWED_SUBENTITY_TYPES = {"IfcCovering", "IfcReinforcingBar"}
DIAMETER_CANDIDATE_ENTITIES = {"IfcPile"}
VALUE_CONVERSION_FIELDS = ["Length", "Height", "NetVolume", "GrossVolume", "Ansichtsfläche", "NetArea", "Durchmesser"]
COMPUTED_FIELDS = {"Durchmesser", "Ansichtsfläche"}

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

    def _has_aggregate_parent_in_scope(element):
        for rel in getattr(element, "Decomposes", []) or []:
            if not (hasattr(rel, "is_a") and rel.is_a("IfcRelAggregates")):
                continue
            parent = getattr(rel, "RelatingObject", None)
            if parent is None:
                continue
            parent_id = _obj_id(parent)
            if parent_id in elements_by_id:
                return True
        return False

    roots = [element for element in elements if not _has_aggregate_parent_in_scope(element)]

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


def _is_missing_value(value):
    if value is None:
        return True
    value_str = str(value).strip()
    return value_str == "" or value_str == "NOTDEFINED"

def clean_and_convert_value(val, field, units):
    if _is_missing_value(val):
        return None
    fval = _to_float(val)
    if fval is None:
        return str(val).strip()
    # Längenfelder in Meter
    if field in {"Length", "Height"}:
        length_factor = units.get("LENGTHUNIT", 1.0)
        return round(fval * length_factor, 6)
    # Volumenfelder in m³
    if field in {"NetVolume", "GrossVolume"}:
        volume_factor = units.get("VOLUMEUNIT", 1.0)
        return round(fval * volume_factor, 9)
    # Flächenfelder in m² (optional, falls benötigt)
    if field in {"AREA_PROJECTION_XY_NET", "Ansichtsfläche", "NetArea"}:
        area_factor = units.get("AREAUNIT", 1.0)
        return round(fval * area_factor, 6)
    # Durchmesser in mm
    if field == "Durchmesser":
        length_factor = units.get("LENGTHUNIT", 1.0)
        # Projekt-Länge -> Meter -> mm
        return str(int(round(fval * length_factor * 1000)))
    return str(val).strip()


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def _compute_diameter_from_volume_and_length_mm(length_m, volume_m3):
    if length_m is None or volume_m3 is None:
        return None
    if length_m <= 0 or volume_m3 <= 0:
        return None
    diameter_m = math.sqrt((4.0 * volume_m3) / (math.pi * length_m))
    diameter_mm = diameter_m * 1000.0
    diameter_mm_rounded_10 = int(round(diameter_mm / 10.0) * 10)
    return str(diameter_mm_rounded_10)


def _iter_representation_items(representation):
    if representation is None:
        return

    reps = getattr(representation, "Representations", None)
    if reps:
        for rep in reps:
            for item in _iter_representation_items(rep):
                yield item
        return

    items = getattr(representation, "Items", None)
    if not items:
        return

    for item in items:
        yield item
        if hasattr(item, "is_a") and item.is_a("IfcMappedItem"):
            mapping_source = getattr(item, "MappingSource", None)
            mapped_rep = getattr(mapping_source, "MappedRepresentation", None)
            for mapped_item in _iter_representation_items(mapped_rep):
                yield mapped_item


def _is_circular_profile_item(item):
    if not hasattr(item, "is_a"):
        return False

    if item.is_a("IfcExtrudedAreaSolid"):
        swept_area = getattr(item, "SweptArea", None)
        return bool(
            swept_area
            and hasattr(swept_area, "is_a")
            and (swept_area.is_a("IfcCircleProfileDef") or swept_area.is_a("IfcCircleHollowProfileDef"))
        )

    if item.is_a("IfcRevolvedAreaSolid"):
        swept_area = getattr(item, "SweptArea", None)
        return bool(
            swept_area
            and hasattr(swept_area, "is_a")
            and (swept_area.is_a("IfcCircleProfileDef") or swept_area.is_a("IfcCircleHollowProfileDef"))
        )

    return False


def _has_circular_profile(element):
    representation = getattr(element, "Representation", None)
    for item in _iter_representation_items(representation):
        if _is_circular_profile_item(item):
            return True
    return False


def _should_compute_diameter(element, ifc_entity):
    if ifc_entity not in DIAMETER_CANDIDATE_ENTITIES:
        return False
    return True


def build_export_dicts(model, elements, property_fields, units):
    export_dicts = []
    for element in elements:
        property_sets = ifcopenshell.util.element.get_psets(element)
        ifc_entity = element.is_a() if hasattr(element, "is_a") else None
        name = getattr(element, 'Name', None)
        predefined_type = getattr(element, 'PredefinedType', None)
        guid = element.GlobalId if hasattr(element, 'GlobalId') else None
        description = getattr(element, "Description", None)
        base_fields = [field for field in property_fields if field not in COMPUTED_FIELDS]
        fields_to_extract = base_fields + ["Height", "NetArea"]
        if ifc_entity == "IfcReinforcingBar":
            fields_to_extract.extend(["Count", "Weight"])

        extracted_properties = extract_fields_from_psets(property_sets, fields_to_extract)
        for key in VALUE_CONVERSION_FIELDS:
            if key in extracted_properties and extracted_properties[key] is not None:
                extracted_properties[key] = clean_and_convert_value(extracted_properties[key], key, units)

        if extracted_properties.get("NetVolume") is None and extracted_properties.get("GrossVolume") is not None:
            extracted_properties["NetVolume"] = extracted_properties["GrossVolume"]

        length_m = _to_float(extracted_properties.get("Length"))
        volume_m3 = _to_float(extracted_properties.get("NetVolume"))
        if _should_compute_diameter(element, ifc_entity):
            diameter_mm = _compute_diameter_from_volume_and_length_mm(length_m, volume_m3)
            if diameter_mm is not None:
                extracted_properties["Durchmesser"] = diameter_mm

        if ifc_entity == "IfcWall":
            extracted_properties.pop("Durchmesser", None)
            height_m = _to_float(extracted_properties.get("Height"))
            if length_m is not None and height_m is not None and length_m > 0 and height_m > 0:
                extracted_properties["Ansichtsfläche"] = round(length_m * height_m, 6)

        if ifc_entity == "IfcCovering":
            net_area_m2 = _to_float(extracted_properties.get("NetArea"))
            if net_area_m2 is not None and net_area_m2 > 0:
                extracted_properties["Ansichtsfläche"] = round(net_area_m2, 6)

        filtered_properties = {key: value for key, value in extracted_properties.items() if value not in (None, "", [], {})}
        materials = extract_materials(model, element)

        base_dict = {
            "IfcEntity": ifc_entity,
            "PredefinedType": predefined_type,
            "Name": name,
            "Description": description,
            "GUID": guid,
            **filtered_properties,
        }

        if materials:
            layer_thicknesses = [_to_float(m.get("LayerThickness")) for m in materials]
            can_split_by_thickness = all(t is not None and t > 0 for t in layer_thicknesses)
            total_thickness = (
                sum(t for t in layer_thicknesses if t is not None) if can_split_by_thickness else None
            )

            for layer_index, material in enumerate(materials, start=1):
                layer_entry = dict(base_dict)
                layer_name = material.get("Name")
                layer_thickness = _to_float(material.get("LayerThickness"))

                if can_split_by_thickness and total_thickness and layer_thickness is not None:
                    layer_ratio = layer_thickness / total_thickness
                    net_volume_total = _to_float(base_dict.get("NetVolume"))
                    gross_volume_total = _to_float(base_dict.get("GrossVolume"))
                    if net_volume_total is not None:
                        layer_entry["NetVolume"] = round(net_volume_total * layer_ratio, 9)
                    if gross_volume_total is not None:
                        layer_entry["GrossVolume"] = round(gross_volume_total * layer_ratio, 9)

                layer_entry["Material"] = [layer_name] if layer_name not in (None, "") else []
                if layer_thickness is not None:
                    layer_entry["MaterialLayerThickness"] = [layer_thickness]
                layer_entry["MaterialLayerIndex"] = layer_index

                layer_entry = {k: v for k, v in layer_entry.items() if v not in (None, "", [], {})}
                export_dicts.append(layer_entry)
        else:
            element_dict = {k: v for k, v in base_dict.items() if v not in (None, "", [], {})}
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
        "Description",
        "Status",
        "CastingMethod",
        "StructuralClass",
        "StrengthClass",
        "ExposureClass",
        "ReinforcementStrengthClass",
        "Length",
        "NetVolume",
        "GrossVolume",
        "ReinforcementVolumeRatio",
    ]

    # Schritt 2: IFC öffnen und relevante Elemente extrahieren
    model = ifcopenshell.open(ifc_file_path)
    units = get_ifc_units(model)
    elements = [element for element in model.by_type("IfcElement") if _is_exportable_ifc_element(element)]
    elements_no_aggregates = _build_no_aggregates_elements(elements)

    # Schritt 3: Relevante Felder aus Aggregationslogik-Elementen extrahieren
    export_dicts = build_export_dicts(model, elements_no_aggregates, property_fields, units)

    # Schritt 4: Exportiere als JSONL
    base_filename = os.path.splitext(os.path.basename(ifc_file_path))[0]
    output_directory = os.path.dirname(ifc_file_path)
    jsonl_export_path = os.path.join(output_directory, base_filename + ".jsonl")
    export_list_of_dicts_to_jsonl(export_dicts, jsonl_export_path)

    print("JSONL-Export abgeschlossen.")

