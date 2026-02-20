import os
import ifcopenshell
import ifcopenshell.util.element
from ifc_material_extract_util import extract_materials
import sys
from tkinter import filedialog
import tkinter as tk
import ifcopenshell.util.element


NO_AGGREGATES_ALLOWED_SUBENTITY_TYPES = {"IfcCovering", "IfcReinforcingBar"}


# Schritt 1: IFC-Datei auswählen
def choose_ifc_file():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title="Select IFC file", filetypes=[("IFC files","*.ifc")])
    root.destroy()
    return path


def _entity_label(obj):
    if obj is None:
        return "<None>"
    ifc_entity = obj.is_a() if hasattr(obj, "is_a") else "Unknown"
    name = getattr(obj, "Name", None)
    guid = getattr(obj, "GlobalId", None)
    if name and guid:
        return f"{ifc_entity}: {name} ({guid})"
    if name:
        return f"{ifc_entity}: {name}"
    if guid:
        return f"{ifc_entity}: ({guid})"
    return ifc_entity


def _rel_related_objects(rels, rel_type, related_attr):
    result = []
    seen = set()
    for rel in rels or []:
        if rel_type and hasattr(rel, "is_a") and not rel.is_a(rel_type):
            continue
        for obj in getattr(rel, related_attr, []) or []:
            obj_id = obj.id() if hasattr(obj, "id") else id(obj)
            if obj_id in seen:
                continue
            seen.add(obj_id)
            result.append(obj)
    return result


def _get_aggregate_children(obj):
    return _rel_related_objects(getattr(obj, "IsDecomposedBy", []), "IfcRelAggregates", "RelatedObjects")


def _get_nested_children(obj):
    return _rel_related_objects(getattr(obj, "IsNestedBy", []), "IfcRelNests", "RelatedObjects")


def _get_contained_elements(spatial_obj):
    return _rel_related_objects(
        getattr(spatial_obj, "ContainsElements", []),
        "IfcRelContainedInSpatialStructure",
        "RelatedElements",
    )


def _get_referenced_elements(spatial_obj):
    return _rel_related_objects(
        getattr(spatial_obj, "ReferencesElements", []),
        "IfcRelReferencedInSpatialStructure",
        "RelatedElements",
    )


def _plural_group_name(ifc_entity):
    # IfcWall -> Walls, IfcBeam -> Beams
    short_name = ifc_entity[3:] if ifc_entity.startswith("Ifc") else ifc_entity
    return f"{short_name}s"


def _is_aggregate_subcomponent(element):
    for rel in getattr(element, "Decomposes", []) or []:
        if hasattr(rel, "is_a") and rel.is_a("IfcRelAggregates"):
            return True
    return False


def _is_allowed_no_aggregates_subentity(element):
    if not hasattr(element, "is_a"):
        return False
    return any(element.is_a(entity_type) for entity_type in NO_AGGREGATES_ALLOWED_SUBENTITY_TYPES)


def _include_in_no_aggregates_export(element):
    if not _is_aggregate_subcomponent(element):
        return True
    return _is_allowed_no_aggregates_subentity(element)


def _is_reinforcing_bar(element):
    return hasattr(element, "is_a") and element.is_a("IfcReinforcingBar")


def _resolve_single_child_replacement(element):
    current = element
    visited = {_obj_id(current)}

    while True:
        aggregate_children = _get_aggregate_children(current)
        non_exception_children = [
            child for child in aggregate_children if not _is_allowed_no_aggregates_subentity(child)
        ]

        if len(non_exception_children) != 1:
            break

        candidate = non_exception_children[0]
        candidate_id = _obj_id(candidate)
        if candidate_id in visited:
            break

        current = candidate
        visited.add(candidate_id)

    return current


def _build_no_aggregates_pset_elements(elements):
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


def _prepare_tree_elements(elements, include_aggregate_children):
    if include_aggregate_children:
        return elements

    replaced_elements = [_resolve_single_child_replacement(element) for element in elements]

    unique_elements = []
    seen_ids = set()
    for element in replaced_elements:
        element_id = _obj_id(element)
        if element_id in seen_ids:
            continue
        seen_ids.add(element_id)
        unique_elements.append(element)

    return unique_elements


def _obj_id(obj):
    return obj.id() if hasattr(obj, "id") else id(obj)


def _is_spatial_node(obj):
    if not hasattr(obj, "is_a"):
        return False
    return (
        obj.is_a("IfcProject")
        or obj.is_a("IfcSpatialElement")
        or obj.is_a("IfcSpatialStructureElement")
        or obj.is_a("IfcSpatialZone")
        or obj.is_a("IfcFacility")
        or obj.is_a("IfcFacilityPart")
    )


def build_psets_output_lines(model, elements):
    output_lines = []
    for element in elements:
        ifc_entity = element.is_a() if hasattr(element, 'is_a') else ''
        name = getattr(element, 'Name', '')
        description = getattr(element, 'Description', '')
        predefined_type = getattr(element, 'PredefinedType', '')
        guid = getattr(element, 'GlobalId', '')
        psets = ifcopenshell.util.element.get_psets(element)
        materials = extract_materials(model, element)
        material_names = [m["Name"] for m in materials if "Name" in m]
        material_layer_thicknesses = list(dict.fromkeys(m["LayerThickness"] for m in materials if "LayerThickness" in m))

        output_lines.append(f"IfcEntity: {ifc_entity}")
        output_lines.append(f"PredefinedType: {predefined_type}")
        output_lines.append(f"Name: {name}")
        output_lines.append(f"Description: {description}")
        output_lines.append(f"GUID: {guid}")
        output_lines.append(f"Material: {', '.join(material_names)}")
        output_lines.append(f"MaterialLayerThickness: {', '.join(str(v) for v in material_layer_thicknesses)}")

        output_lines.append("Property sets:")
        output_lines.append(str(psets))
        output_lines.append("-" * 60)
    return output_lines


def _traverse_element(element, level, lines, active_path, include_aggregate_children=True):
    if not include_aggregate_children:
        element = _resolve_single_child_replacement(element)

    element_id = _obj_id(element)
    if element_id in active_path:
        lines.append(f"{'  ' * level}- {_entity_label(element)} [cycle]")
        return

    lines.append(f"{'  ' * level}- {_entity_label(element)}")
    next_path = set(active_path)
    next_path.add(element_id)

    children = []
    if include_aggregate_children:
        children.extend(_get_aggregate_children(element))
    else:
        children.extend(
            child for child in _get_aggregate_children(element) if _is_allowed_no_aggregates_subentity(child)
        )
    children.extend(_get_nested_children(element))
    unique_children = []
    seen = set()
    for child in children:
        child_id = _obj_id(child)
        if child_id in seen:
            continue
        seen.add(child_id)
        unique_children.append(child)

    for child in unique_children:
        _traverse_element(child, level + 1, lines, next_path, include_aggregate_children=include_aggregate_children)


def build_ifc_tree_lines(model, include_aggregate_subentities=True):
    lines = []
    projects = model.by_type("IfcProject")
    if not projects:
        lines.append("No IfcProject found.")
        return lines

    def traverse_spatial(obj, level, active_path):
        obj_id = _obj_id(obj)
        if obj_id in active_path:
            lines.append(f"{'  ' * level}- {_entity_label(obj)} [cycle]")
            return

        lines.append(f"{'  ' * level}- {_entity_label(obj)}")
        next_path = set(active_path)
        next_path.add(obj_id)

        aggregate_children = _get_aggregate_children(obj)
        spatial_children = [child for child in aggregate_children if _is_spatial_node(child)]
        aggregated_non_spatial = [child for child in aggregate_children if not _is_spatial_node(child)]
        for child in spatial_children:
            traverse_spatial(child, level + 1, next_path)

        contained = _get_contained_elements(obj)
        if contained:
            contained = _prepare_tree_elements(contained, include_aggregate_subentities)
            contained_ids = {_obj_id(element) for element in contained}
            grouped = {}
            for element in contained:
                grouped.setdefault(element.is_a(), []).append(element)

            for ifc_entity in sorted(grouped.keys()):
                lines.append(f"{'  ' * (level + 1)}- {_plural_group_name(ifc_entity)}")
                for element in grouped[ifc_entity]:
                    _traverse_element(
                        element,
                        level + 2,
                        lines,
                        next_path,
                        include_aggregate_children=include_aggregate_subentities,
                    )
        else:
            contained_ids = set()

        referenced = [
            element for element in _get_referenced_elements(obj)
            if _obj_id(element) not in contained_ids
        ]
        referenced = _prepare_tree_elements(referenced, include_aggregate_subentities)
        referenced_ids = {_obj_id(element) for element in referenced}
        if referenced:
            grouped_referenced = {}
            for element in referenced:
                grouped_referenced.setdefault(element.is_a(), []).append(element)

            lines.append(f"{'  ' * (level + 1)}- ReferencedElements")
            for ifc_entity in sorted(grouped_referenced.keys()):
                lines.append(f"{'  ' * (level + 2)}- {_plural_group_name(ifc_entity)}")
                for element in grouped_referenced[ifc_entity]:
                    _traverse_element(
                        element,
                        level + 3,
                        lines,
                        next_path,
                        include_aggregate_children=include_aggregate_subentities,
                    )

        aggregated_elements = [
            element
            for element in aggregated_non_spatial
            if _obj_id(element) not in contained_ids and _obj_id(element) not in referenced_ids
        ]
        aggregated_elements = _prepare_tree_elements(aggregated_elements, include_aggregate_subentities)
        if aggregated_elements:
            grouped_aggregated = {}
            for element in aggregated_elements:
                grouped_aggregated.setdefault(element.is_a(), []).append(element)

            aggregated_section_label = (
                "AggregatedElements" if include_aggregate_subentities else "DirectElements"
            )
            lines.append(f"{'  ' * (level + 1)}- {aggregated_section_label}")
            for ifc_entity in sorted(grouped_aggregated.keys()):
                lines.append(f"{'  ' * (level + 2)}- {_plural_group_name(ifc_entity)}")
                for element in grouped_aggregated[ifc_entity]:
                    _traverse_element(
                        element,
                        level + 3,
                        lines,
                        next_path,
                        include_aggregate_children=include_aggregate_subentities,
                    )

    for project in projects:
        traverse_spatial(project, 0, set())

    return lines


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
    model = ifcopenshell.open(ifc_path)

    tree_lines = build_ifc_tree_lines(model, include_aggregate_subentities=True)
    tree_path = os.path.splitext(ifc_path)[0] + "_tree.txt"
    with open(tree_path, "w", encoding="utf-8") as f:
        f.write("\n".join(tree_lines) + "\n")
    print(f"Exported IFC hierarchy tree to {tree_path}")

    tree_no_aggregate_lines = build_ifc_tree_lines(model, include_aggregate_subentities=False)
    tree_no_aggregate_path = os.path.splitext(ifc_path)[0] + "_tree_no_aggregates.txt"
    with open(tree_no_aggregate_path, "w", encoding="utf-8") as f:
        f.write("\n".join(tree_no_aggregate_lines) + "\n")
    print(f"Exported IFC hierarchy tree without IfcRelAggregates subentities to {tree_no_aggregate_path}")

    print("--- IFC hierarchy preview (first 40 lines) ---")
    for line in tree_lines[:40]:
        print(line)

    elements = model.by_type("IfcElement")
    if not elements:
        print("No IfcElement found in the model.")
        sys.exit(1)

    output_lines = build_psets_output_lines(model, elements)
    output_path = os.path.splitext(ifc_path)[0] + "_psets.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for line in output_lines:
            f.write(line + "\n")
    print(f"Exported property sets to {output_path}")

    elements_no_aggregate_subcomponents = _build_no_aggregates_pset_elements(elements)
    output_lines_no_aggregate_subcomponents = build_psets_output_lines(
        model, elements_no_aggregate_subcomponents
    )
    output_path_no_aggregate_subcomponents = os.path.splitext(ifc_path)[0] + "_psets_no_aggregates.txt"
    with open(output_path_no_aggregate_subcomponents, "w", encoding="utf-8") as f:
        for line in output_lines_no_aggregate_subcomponents:
            f.write(line + "\n")
    print(
        "Exported property sets without IfcRelAggregates subcomponents to "
        f"{output_path_no_aggregate_subcomponents}"
    )

if __name__ == "__main__":
    main()
    