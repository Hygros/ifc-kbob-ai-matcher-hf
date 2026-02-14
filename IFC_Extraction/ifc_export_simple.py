import os
import ifcopenshell
import ifcopenshell.util.element
from ifc_material_extract_util import extract_materials
import sys
from tkinter import filedialog
import tkinter as tk
import ifcopenshell.util.element


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


def _plural_group_name(ifc_entity):
    # IfcWall -> Walls, IfcBeam -> Beams
    short_name = ifc_entity[3:] if ifc_entity.startswith("Ifc") else ifc_entity
    return f"{short_name}s"


def _is_aggregate_subcomponent(element):
    for rel in getattr(element, "Decomposes", []) or []:
        if hasattr(rel, "is_a") and rel.is_a("IfcRelAggregates"):
            return True
    return False


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

        output_lines.append(f"IfcEntity: {ifc_entity}")
        output_lines.append(f"PredefinedType: {predefined_type}")
        output_lines.append(f"Name: {name}")
        output_lines.append(f"Description: {description}")
        output_lines.append(f"GUID: {guid}")
        output_lines.append(f"Material: {', '.join(material_names)}")

        output_lines.append("Property sets:")
        output_lines.append(str(psets))
        output_lines.append("-" * 60)
    return output_lines


def _traverse_element(element, level, lines, active_path, include_aggregate_children=True):
    element_id = element.id() if hasattr(element, "id") else id(element)
    if element_id in active_path:
        lines.append(f"{'  ' * level}- {_entity_label(element)} [cycle]")
        return

    lines.append(f"{'  ' * level}- {_entity_label(element)}")
    next_path = set(active_path)
    next_path.add(element_id)

    children = []
    if include_aggregate_children:
        children.extend(_get_aggregate_children(element))
    children.extend(_get_nested_children(element))
    unique_children = []
    seen = set()
    for child in children:
        child_id = child.id() if hasattr(child, "id") else id(child)
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
        obj_id = obj.id() if hasattr(obj, "id") else id(obj)
        if obj_id in active_path:
            lines.append(f"{'  ' * level}- {_entity_label(obj)} [cycle]")
            return

        lines.append(f"{'  ' * level}- {_entity_label(obj)}")
        next_path = set(active_path)
        next_path.add(obj_id)

        aggregate_children = _get_aggregate_children(obj)
        spatial_children = [
            child for child in aggregate_children if child.is_a("IfcSpatialElement") or child.is_a("IfcProject")
        ]
        for child in spatial_children:
            traverse_spatial(child, level + 1, next_path)

        contained = _get_contained_elements(obj)
        if contained:
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

    elements_no_aggregate_subcomponents = [
        element for element in elements if not _is_aggregate_subcomponent(element)
    ]
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
    