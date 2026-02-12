import ifcopenshell
import tkinter as tk
from tkinter import filedialog
from typing import Optional

def select_ifc_file_dialog() -> str | None:
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="IFC-Datei auswählen",
        filetypes=[("IFC Dateien", "*.ifc")],
    )
    root.update()
    root.destroy()
    return path

def _get_element_volume(element: ifcopenshell.entity_instance) -> float | None:
    """Extract GrossVolume from element quantities."""
    # Check for IfcRelDefinesByProperties relationships
    for rel in element.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            prop_set = rel.RelatingPropertyDefinition
            # Check if the property set is an IfcElementQuantity
            if prop_set.is_a("IfcElementQuantity") and prop_set.Name.startswith("Qto_"):
                # Look for IfcQuantityVolume with GrossVolume
                for quantity in prop_set.Quantities:
                    if quantity.is_a("IfcQuantityVolume") and quantity.Name == "GrossVolume":
                        if quantity.VolumeValue is not None:
                            return float(quantity.VolumeValue)
            # Check if the property set is an IfcPropertySet
            elif prop_set.is_a("IfcPropertySet"):
                for prop in prop_set.HasProperties:
                    if prop.is_a("IfcPropertySingleValue") and prop.Name == "GrossVolume":
                        if prop.NominalValue is not None:
                            return float(prop.NominalValue.wrappedValue)
    return None


# Select the IFC file
ifc_file_path = select_ifc_file_dialog()
if not ifc_file_path:
    print("No file selected.")
    exit()

# Open the IFC file
ifc_file = ifcopenshell.open(ifc_file_path)

# Get all elements from the IFC file
elements = ifc_file.by_type("IfcElement")

# Extract GrossVolume for each element
for element in elements:
    volume = _get_element_volume(element)
    if volume is not None:
        print(f"Element GUID: {element.GlobalId}, Volume: {volume}")
    else:
        print(f"Element GUID: {element.GlobalId}, Volume not found.")

