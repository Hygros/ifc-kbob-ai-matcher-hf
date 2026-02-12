import ifcopenshell
from IfcLCA import IfcLCA, KBOBReader, IfcLCAReporter
import tkinter as tk
from tkinter import filedialog


# New: ask user to select IFC file
root = tk.Tk()
root.withdraw()
ifc_path = filedialog.askopenfilename(
    title="Select IFC file",
    filetypes=[("IFC files", "*.ifc"), ("All files", "*.*")]
)
root.destroy()
if not ifc_path:
    print("No IFC file selected. Exiting.")
    raise SystemExit(0)

# Load IFC file
ifc_file = ifcopenshell.open(ifc_path)

# Initialize database and LCA interface
db_reader = KBOBReader()  # Uses built-in KBOB data
lca = IfcLCA(ifc_file, db_reader)

# Discover and map materials
materials = lca.get_all_materials()
mapping = lca.auto_map_materials()

# Run analysis
analysis = lca.run_analysis(mapping)

# Generate report
reporter = IfcLCAReporter("My Building")
report = reporter.generate_analysis_report(analysis, 'text')
print(report)