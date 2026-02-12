import ifcopenshell
import ifcopenshell.util.selector
import tkinter as tk
from tkinter import filedialog
from typing import Optional

def select_ifc_file_dialog() -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="IFC-Datei auswählen",
        filetypes=[("IFC Dateien", "*.ifc"), ("Alle Dateien", "*.*")],
    )
    root.update()
    root.destroy()
    return path


# Select the IFC file
ifc_file_path = select_ifc_file_dialog()
if not ifc_file_path:
    print("No file selected.")
    exit()

# Open the IFC file
ifc_file = ifcopenshell.open(ifc_file_path)

# Get all elements from the IFC file
elements = ifc_file.by_type("IfcElement")

# Iterate through elements and print their material names
for element in elements:
    material = ifcopenshell.util.selector.get_element_value(element, "material.Name")
    if material:
        print(f"Element GUID: {element.GlobalId}, Material Name: {material}")
    else:
        print(f"Element GUID: {element.GlobalId}, Material Name: Not found")