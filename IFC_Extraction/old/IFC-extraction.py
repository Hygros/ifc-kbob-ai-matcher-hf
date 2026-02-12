"""
einfaches skript ohne fallbacks oder try - except um von jedem ifcElement die GUID, Beschreibung, Entität und PredefinedType mit einem print-Befehl auszugeben
"""

import sys
import ifcopenshell
import tkinter as tk
from tkinter import filedialog
from typing import Optional
import ifcopenshell.util.element

def select_ifc_file_dialog() -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="IFC-Datei auswählen",
        filetypes=[("IFC Dateien", "*.ifc")],
    )
    root.update()
    root.destroy()
    return path

def _extract_relevant_pset_info(psets):
    # Status aus Pset_*Common (erste Listeintrag wenn vorhanden)
    status = None
    # Dynamisch das passende Pset_*Common suchen (z.B. Pset_WallCommon, Pset_PileCommon, ...)
    pc = {}
    if psets:
        for k, v in psets.items():
            if isinstance(k, str) and k.startswith("Pset_") and k.endswith("Common"):
                pc = v or {}
                break
    st = pc.get("Status")
    if st:
        if isinstance(st, (list, tuple)) and len(st) > 0:
            status = st[0]
        else:
            status = st

    # QTO: NetVolume und Length (z.B. Qto_PileBaseQuantities)
    net_volume = None
    length = None
    for k, v in (psets or {}).items():
        if k.startswith("Qto_"):
            if net_volume is None and "NetVolume" in v:
                net_volume = v.get("NetVolume")
            if length is None and "Length" in v:
                length = v.get("Length")
    # Concrete Pset Felder
    pcon = psets.get("Pset_ConcreteElementGeneral") or {}
    casting = pcon.get("CastingMethod")
    structural = pcon.get("StructuralClass")
    strength = pcon.get("StrengthClass")
    exposure = pcon.get("ExposureClass")
    reinf_ratio = pcon.get("ReinforcementVolumeRatio")
    reinf_strength = pcon.get("ReinforcementStrengthClass")

    # Beschrieb (z.B. {'comment': 'Pfahlreihe Süd'})
    beschrieb = None
    b = psets.get("Beschrieb") or {}
    beschrieb = b.get("comment") or b.get("Beschrieb")

    # Durchmesser: wähle erstes numerisches Feld (ohne 'id')
    durchmesser = None
    d = psets.get("Durchmesser") or {}
    for key, val in d.items():
        if key == "id":
            continue
        if isinstance(val, (int, float)):
            durchmesser = val
            break

    return {
        "Status": status,
        "NetVolume": net_volume,
        "Length": length,
        "CastingMethod": casting,
        "StructuralClass": structural,
        "StrengthClass": strength,
        "ExposureClass": exposure,
        "ReinforcementVolumeRatio": reinf_ratio,
        "ReinforcementStrengthClass": reinf_strength,
        "Beschrieb": beschrieb,
        "Durchmesser": durchmesser,
    }

def main(ifc_path: str):
    model = ifcopenshell.open(ifc_path)
    for element in model:
        # only consider IfcElement and its subtypes
        if hasattr(element, "is_a") and element.is_a("IfcElement"):
            psets = ifcopenshell.util.element.get_psets(element)
            info = _extract_relevant_pset_info(psets)
            guid = getattr(element, "GlobalId", None)
            beschreibung = getattr(element, "Description", None)
            entitaet = element.is_a()
            predefined = getattr(element, "PredefinedType", None)

            print(
                f"GUID: {guid} | Beschreibung: {info['Beschrieb'] or ''} | Entität: {entitaet} | "
                f"PredefinedType: {predefined or ''} | Status: {info['Status'] or ''} | "
                f"NetVolume: {info['NetVolume'] or ''} | Length: {info['Length'] or ''} | "
                f"CastingMethod: {info['CastingMethod'] or ''} | StructuralClass: {info['StructuralClass'] or ''} | "
                f"StrengthClass: {info['StrengthClass'] or ''} | ExposureClass: {info['ExposureClass'] or ''} | "
                f"ReinforcementVolumeRatio: {info['ReinforcementVolumeRatio'] or ''} | "
                f"ReinforcementStrengthClass: {info['ReinforcementStrengthClass'] or ''} | "
                f"Durchmesser: {info['Durchmesser'] or ''}"
            )

if __name__ == "__main__":
    ifc_path = select_ifc_file_dialog()
    if not ifc_path:
        print("No file selected. Exiting.")
        sys.exit(1)
    main(ifc_path)