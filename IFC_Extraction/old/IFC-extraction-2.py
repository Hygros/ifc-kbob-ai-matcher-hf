"""
• get_psets(element, qtos_only=True) liefert alle zu einem Element zugewiesenen Mengen als Dictionary je Qto‑Satz, inkl. vererbter Type‑Mengen. 
• get_predefined_type(element) berücksichtigt die Regeln der IFC‑Vererbung zwischen Vorkommnis und zugewiesenem Typ. Falls ein Typ zugewiesen ist, gilt dessen PredefinedType vorrangig. 
• Materialbezüge und ‑auflösung: get_materials(element) gibt die individuellen IfcMaterial‑Instanzen zurück, auch wenn Sets oder Layer/Profile verwendet werden. Namen, Beschreibung und Kategorie sind reguläre Attribute von IfcMaterial seit IFC4. 
• PSet_MaterialCommon ist ein am Material definiertes Pset; darin liegt u. a. MassDensity. 
• Die Quantität NetVolume und die Längenangaben sind in den standardisierten Qto‑Sätzen (z. B. Qto_WallBaseQuantities) definiert. [docs.ifcop...nshell.org], [docs.ifcop...nshell.org]



Extrahiert pro IfcElement:
- Entity (Klassenname), PredefinedType, GlobalId, Name, Description
- qto_NetVolume, qto_Length
- Material: Name, Description, Category
- MassDensity (aus PSet_MaterialCommon)

Abhängigkeit: ifcopenshell >= 0.8.x

"""

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# GUI: Dateiauswahl
import tkinter as tk
from tkinter import filedialog, messagebox

import ifcopenshell
import ifcopenshell.util.element as uel


def _get_qto_value(qtos: Dict[str, Dict[str, Any]], keys: Tuple[str, ...]) -> Optional[Any]:
    for _, props in qtos.items():
        for k in keys:
            if k in props and props[k] is not None:
                return props[k]
    return None


def _material_info_for_element(element) -> List[Dict[str, Any]]:
    infos: List[Dict[str, Any]] = []
    materials = uel.get_materials(element) or []
    for m in materials:
        name = getattr(m, "Name", None)
        desc = getattr(m, "Description", None)
        cat = getattr(m, "Category", None)

        mass_density = None
        try:
            for mp in getattr(m, "HasProperties", []) or []:
                for p in getattr(mp, "Properties", []) or []:
                    if getattr(p, "Name", "") == "MassDensity":
                        nv = getattr(p, "NominalValue", None)
                        if nv is not None and hasattr(nv, "wrappedValue"):
                            mass_density = nv.wrappedValue
                        else:
                            mass_density = getattr(p, "NominalValue", None)
        except Exception:
            pass

        infos.append(
            {
                "material_name": name,
                "material_description": desc,
                "material_category": cat,
                "material_mass_density": mass_density,
            }
        )
    return infos


def extract_elements(file: ifcopenshell.file) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for el in file.by_type("IfcElement"):
        entity = el.is_a()
        gid = getattr(el, "GlobalId", None)
        name = getattr(el, "Name", None)
        desc = getattr(el, "Description", None)

        predefined = uel.get_predefined_type(el)

        qtos = uel.get_psets(el, qtos_only=True) or {}
        net_volume = _get_qto_value(qtos, ("NetVolume",))
        length = _get_qto_value(qtos, ("Length", "TotalLength"))

        mats = _material_info_for_element(el)
        element_mass_density = uel.get_element_mass_density(el)

        mat_names = ";".join([str(m["material_name"]) for m in mats if m["material_name"] is not None]) or None
        mat_descs = ";".join([str(m["material_description"]) for m in mats if m["material_description"] is not None]) or None
        mat_cats = ";".join([str(m["material_category"]) for m in mats if m["material_category"] is not None]) or None
        mat_densities = ";".join(
            [str(m["material_mass_density"]) for m in mats if m["material_mass_density"] is not None]
        ) or None

        rows.append(
            {
                "global_id": gid,
                "entity": entity,
                "predefined_type": predefined,
                "name": name,
                "description": desc,
                "qto_NetVolume": net_volume,
                "qto_Length": length,
                "material_name": mat_names,
                "material_description": mat_descs,
                "material_category": mat_cats,
                "MassDensity_PSet_MaterialCommon": mat_densities,
                "MassDensity_element": element_mass_density,
            }
        )
    return rows


def write_csv(rows: List[Dict[str, Any]], csv_path: Path) -> None:
    if not rows:
        rows = [
            {
                "entity": None,
                "predefined_type": None,
                "global_id": None,
                "name": None,
                "description": None,
                "qto_NetVolume": None,
                "qto_Length": None,
                "material_name": None,
                "material_description": None,
                "material_category": None,
                "MassDensity_PSet_MaterialCommon": None,
                "MassDensity_element": None,
            }
        ]
    fieldnames = list(rows[0].keys())
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def pick_files_via_gui() -> Optional[Tuple[Path, Optional[Path]]]:
    root = tk.Tk()
    root.withdraw()  # kein Hauptfenster

    ifc_path_str = filedialog.askopenfilename(
        title="IFC-Datei auswählen",
        filetypes=[("IFC", "*.ifc *.ifczip"), ("Alle Dateien", "*.*")],
    )
    if not ifc_path_str:
        return None

    default_csv = str(Path(ifc_path_str).with_suffix(".elements.csv"))
    csv_path_str = filedialog.asksaveasfilename(
        title="CSV-Ziel auswählen (optional)",
        initialfile=Path(default_csv).name,
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv"), ("Alle Dateien", "*.*")],
    )
    if not csv_path_str:
        return Path(ifc_path_str), None
    return Path(ifc_path_str), Path(csv_path_str)


def main(argv: List[str]) -> int:
    # CLI‑Variante bleibt erhalten; ohne Argumente öffnet sich die GUI.
    if len(argv) >= 2:
        in_ifc = Path(argv[1])
        out_csv = Path(argv[2]) if len(argv) > 2 else in_ifc.with_suffix(".elements.csv")
    else:
        picked = pick_files_via_gui()
        if picked is None:
            # Abbruch durch Benutzer
            return 1
        in_ifc, csv_opt = picked
        out_csv = csv_opt if csv_opt is not None else in_ifc.with_suffix(".elements.csv")

    try:
        model = ifcopenshell.open(str(in_ifc))
    except Exception as e:
        # Falls GUI genutzt wurde, Fehlermeldung anzeigen
        if "tkinter" in sys.modules:
            messagebox.showerror("Fehler beim Öffnen", f"Konnte IFC nicht öffnen:\n{e}")
        else:
            print(f"Fehler: {e}", file=sys.stderr)
        return 2

    rows = extract_elements(model)
    write_csv(rows, out_csv)

    # GUI‑Feedback
    if "tkinter" in sys.modules:
        messagebox.showinfo("Fertig", f"Export erstellt:\n{out_csv}")
    else:
        print(f"Export: {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
