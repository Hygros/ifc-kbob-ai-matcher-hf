import os
import ifcopenshell
import ifcopenshell.util.element
from ifc_material_extract_util import extract_materials
import csv
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
    elements = model.by_type("IfcElement")
    if not elements:
        print("No IfcElement found in the model.")
        sys.exit(1)
    output_lines = []
    for idx, element in enumerate(elements):
        element_type = ifcopenshell.util.element.get_type(element)
        ifc_entity = element.is_a() if hasattr(element, 'is_a') else ''
        name = getattr(element, 'Name', '')
        predefined_type = getattr(element, 'PredefinedType', '')
        guid = getattr(element, 'GlobalId', '')
        psets = ifcopenshell.util.element.get_psets(element)
        materials = extract_materials(model, element)
        material_names = [m["Name"] for m in materials if "Name" in m]
        
        output_lines.append(f"IfcEntity: {ifc_entity}")
        output_lines.append(f"PredefinedType: {predefined_type}")
        output_lines.append(f"Name: {name}")
        output_lines.append(f"GUID: {guid}")
        output_lines.append(f"Material: {', '.join(material_names)}")
        
        output_lines.append("Property sets:")
        output_lines.append(str(psets))
        output_lines.append("-"*60)
    output_path = os.path.splitext(ifc_path)[0] + "_psets.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for line in output_lines:
            f.write(line + "\n")
    print(f"Exported property sets to {output_path}")

if __name__ == "__main__":
    main()
    