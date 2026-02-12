
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import argparse
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog

import ifcopenshell
from ifcopenshell.util import element as util_element  # genutzt für andere Helfer falls später nötig


def get_predefined_type(file: ifcopenshell.file, el) -> Optional[str]:
    """
    Versucht PredefinedType zuerst direkt am Element, danach am zugewiesenen Typ (IfcRelDefinesByType).
    """
    # Direkt am Element
    if hasattr(el, "PredefinedType"):
        val = el.PredefinedType
        if val and str(val).upper() not in {"NOTDEFINED", "UNSET", "NULL"}:
            return str(val)

    # Über Type-Zuweisung
    for inv in file.get_inverse(el):
        if inv.is_a("IfcRelDefinesByType") and getattr(inv, "RelatingType", None):
            t = inv.RelatingType
            if hasattr(t, "PredefinedType") and t.PredefinedType:
                pt = str(t.PredefinedType)
                if pt.upper() not in {"NOTDEFINED", "UNSET", "NULL"}:
                    return pt

    return None


def get_connections(file: ifcopenshell.file, el) -> List[str]:
    """
    Sammelt verbundene Elemente über IfcRelConnectsElements (beide Richtungen).
    Gibt eine Liste von GlobalIds zurück.
    """
    connected = []
    for inv in file.get_inverse(el):
        if inv.is_a("IfcRelConnectsElements"):
            # Zwei Richtungen möglich:
            if getattr(inv, "RelatingElement", None) == el and getattr(inv, "RelatedElement", None):
                connected.append(inv.RelatedElement.GlobalId)
            elif getattr(inv, "RelatedElement", None) == el and getattr(inv, "RelatingElement", None):
                connected.append(inv.RelatingElement.GlobalId)
    # Duplikate entfernen
    return sorted(set(connected))


def get_coverings(file: ifcopenshell.file, el) -> List[str]:
    """
    Sammelt Abdeckungen (Coverings) über IfcRelCoversBldgElements.
    Gibt eine Liste von GlobalIds der Covering-Elemente zurück.
    """
    coverings = []
    for inv in file.get_inverse(el):
        if inv.is_a("IfcRelCoversBldgElements"):
            for c in getattr(inv, "RelatedCoverings", []) or []:
                coverings.append(c.GlobalId)
    return sorted(set(coverings))


def _gather_materials_from_definition(mat_def) -> List[str]:
    materials: List[str] = []
    def add(mat):
        if not mat:
            return
        name = getattr(mat, "Name", None) or getattr(mat, "Category", None) or getattr(mat, "Tag", None)
        if name and isinstance(name, str):
            materials.append(name.strip())
    if not mat_def:
        return materials
    if mat_def.is_a("IfcMaterial"):
        add(mat_def)
    elif mat_def.is_a("IfcMaterialLayerSetUsage"):
        ls = getattr(mat_def, "ForLayerSet", None)
        if ls:
            for layer in getattr(ls, "MaterialLayers", []) or []:
                add(getattr(layer, "Material", None))
    elif mat_def.is_a("IfcMaterialProfileSetUsage"):
        ps = getattr(mat_def, "ForProfileSet", None)
        if ps:
            for prof in getattr(ps, "Profiles", []) or []:
                add(getattr(prof, "Material", None))
    elif mat_def.is_a("IfcMaterialConstituentSet"):
        for cons in getattr(mat_def, "Constituents", []) or []:
            add(getattr(cons, "Material", None))
    elif mat_def.is_a("IfcMaterialLayerSet"):
        for layer in getattr(mat_def, "MaterialLayers", []) or []:
            add(getattr(layer, "Material", None))
    elif mat_def.is_a("IfcMaterialProfileSet"):
        for prof in getattr(mat_def, "Profiles", []) or []:
            add(getattr(prof, "Material", None))
    else:
        # Generischer Versuch falls anderer Subtyp von IfcMaterialDefinition mit Name
        add(mat_def)
    return materials


def extract_material(file: ifcopenshell.file, el) -> Optional[str]:
    """Sammelt alle Material-Kandidaten aus direkten und Typ-Zuweisungen und wählt ein finales Material.
    Quellen: IfcRelAssociatesMaterial -> IfcMaterial / LayerSet(Usage) / ProfileSet(Usage) / ConstituentSet.
    Wenn mehrere Namen: Mehrheitswahl; bei Gleichstand erster eindeutiger Eintrag.
    Gibt einen Materialnamen oder None zurück."""
    candidates: List[str] = []

    def collect_from_object(obj):
        for inv in file.get_inverse(obj):
            if inv.is_a("IfcRelAssociatesMaterial"):
                mat_def = getattr(inv, "RelatingMaterial", None)
                candidates.extend(_gather_materials_from_definition(mat_def))

    collect_from_object(el)
    if not candidates:
        for inv in file.get_inverse(el):
            if inv.is_a("IfcRelDefinesByType") and getattr(inv, "RelatingType", None):
                collect_from_object(inv.RelatingType)

    candidates = [c for c in (candidates or []) if c]
    if not candidates:
        return None
    # Mehrheitswahl
    freq: Dict[str, int] = {}
    for c in candidates:
        freq[c] = freq.get(c, 0) + 1
    # Sortiere nach Häufigkeit, dann nach erster Auftretensposition
    ordered = sorted(freq.items(), key=lambda kv: (-kv[1], candidates.index(kv[0])))
    return ordered[0][0] if ordered else None


def _collect_qtos_manual(el) -> Dict[str, Dict[str, Any]]:
    """Erfasst Quantity Sets (IfcElementQuantity) manuell ohne util_element.get_qtos.
    Gibt Dict[SetName -> Dict[QuantityName -> numeric value]] zurück."""
    result: Dict[str, Dict[str, Any]] = {}
    # Inverse Relation: IsDefinedBy (Liste von IfcRelDefinesByProperties)
    for rel in getattr(el, "IsDefinedBy", []) or []:
        if rel and rel.is_a("IfcRelDefinesByProperties"):
            ps = getattr(rel, "RelatingPropertyDefinition", None)
            if ps and ps.is_a("IfcElementQuantity"):
                set_name = ps.Name or "UnnamedSet"
                quantities: Dict[str, Any] = {}
                for q in getattr(ps, "Quantities", []) or []:
                    q_name = (getattr(q, "Name", None) or "").strip() or "UnnamedQuantity"
                    val: Optional[float] = None
                    # Typ-spezifische Extraktion
                    if q.is_a("IfcQuantityVolume"):
                        val = getattr(q, "VolumeValue", None)
                    elif q.is_a("IfcQuantityLength"):
                        val = getattr(q, "LengthValue", None)
                    elif q.is_a("IfcQuantityArea"):
                        val = getattr(q, "AreaValue", None)
                    elif q.is_a("IfcQuantityCount"):
                        val = getattr(q, "CountValue", None)
                    elif q.is_a("IfcQuantityWeight"):
                        val = getattr(q, "WeightValue", None)
                    elif q.is_a("IfcQuantityTime"):
                        val = getattr(q, "TimeValue", None)

                    if val is not None:
                        try:
                            quantities[q_name] = float(val)
                        except (TypeError, ValueError):
                            pass
                if quantities:
                    result[set_name] = quantities
    return result


def find_volume_in_qtos(el) -> Tuple[Optional[float], Optional[float]]:
    """
    Sucht GrossVolume / NetVolume in den QTOs (Quantity Sets) eines Elements.
    Berücksichtigt unterschiedliche Satznamen (BaseQuantities, QTO_* etc.) und
    mehrere Sprach-/Benennungsvarianten falls vorhanden.
    """
    # util_element.get_qtos existiert in manchen Distributionen nicht; daher manueller Fallback
    qtos: Dict[str, Dict[str, Any]] = _collect_qtos_manual(el)
    gross_candidates = {"GrossVolume", "VolumeGross", "BruttoVolumen", "Gross_Volume"}
    net_candidates = {"NetVolume", "VolumeNet", "NettoVolumen", "Net_Volume"}

    gross = None
    net = None

    def pick_first_numeric(val):
        # val kann eine Zahl sein oder ein Struktur-Dict (z.B. {"value": ..., "unit": ...} je nach Version)
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        # Manchmal liefert util_element Werte als einfache Zahl; wenn nicht, versuche generische Felder
        if isinstance(val, dict):
            for key in ("value", "VolumeValue", "nominal_value", "Val"):
                if key in val and isinstance(val[key], (int, float)):
                    return float(val[key])
        return None

    # Durch alle Quantity Sets iterieren
    for set_name, quantities in qtos.items():
        # quantities: Dict[quantity_name -> value]
        for q_name, q_val in quantities.items():
            qn_norm = (q_name or "").strip()
            if qn_norm in gross_candidates and gross is None:
                gross = pick_first_numeric(q_val)
            elif qn_norm in net_candidates and net is None:
                net = pick_first_numeric(q_val)

        # Falls exakte Namen nicht gefunden wurden, versuche heuristische Suche
        if gross is None:
            for q_name, q_val in quantities.items():
                nm = (q_name or "").lower()
                if "gross" in nm or "brutto" in nm:
                    gross = pick_first_numeric(q_val)
                    if gross is not None:
                        break
        if net is None:
            for q_name, q_val in quantities.items():
                nm = (q_name or "").lower()
                if "net" in nm or "netto" in nm:
                    net = pick_first_numeric(q_val)
                    if net is not None:
                        break

        if gross is not None and net is not None:
            break

    return gross, net


def element_to_dict(file: ifcopenshell.file, element) -> Dict[str, Any]:
    """
    Extrahiert die gewünschten Felder aus einem IfcElement.
    """
    gross, net = find_volume_in_qtos(element)

    # Nur ein Feld 'Volume' ausgeben. Priorität: NetVolume vor GrossVolume.
    if net is not None:
        volume = net
    else:
        volume = gross

    return {
        "GlobalId": element.GlobalId,
        "IfcEntity": element.is_a(),
        "PredefinedType": get_predefined_type(file, element),
        "Name": getattr(element, "Name", None),
        "Description": getattr(element, "Description", None),
        "Material": extract_material(file, element),
        "ConnectedTo": get_connections(file, element),
        "HasCoverings": get_coverings(file, element),
        "Volume": volume,
    }


def select_ifc_file_dialog() -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="IFC-Datei auswählen",
        filetypes=[("IFC Dateien", "*.ifc")],
    )
    root.update()
    root.destroy()
    return path if path else None


def main():
    parser = argparse.ArgumentParser(
        description="Extrahiere Eigenschaften aus allen IfcElementen und speichere sie als JSON. Bei jedem Ausführen kann eine IFC-Datei ausgewählt werden."
    )
    parser.add_argument("-o", "--out", help="Ausgabedatei (JSON). Standard: <IFC_Basename>_elements.json")
    parser.add_argument("--no-dialog", action="store_true", help="Kein Dialog öffnen; --ifc verwenden.")
    parser.add_argument("--ifc", help="Pfad zur IFC-Datei für --no-dialog Modus")
    args = parser.parse_args()

    if args.no_dialog:
        if not args.ifc:
            print("Fehler: Mit --no-dialog muss --ifc angegeben werden.", file=sys.stderr)
            sys.exit(1)
        ifc_path = args.ifc
    else:
        ifc_path = select_ifc_file_dialog()
        if not ifc_path:
            print("Abbruch: Keine IFC-Datei gewählt.")
            return

    if not Path(ifc_path).is_file():
        print(f"Fehler: Datei nicht gefunden: {ifc_path}", file=sys.stderr)
        sys.exit(1)

    out_path = args.out if args.out else f"{Path(ifc_path).stem}_elements.json"

    # Zielordner im selben Verzeichnis wie dieses Skript (z.B. 'export')
    script_dir = Path(__file__).resolve().parent
    export_dir = script_dir / "ifc-export"
    try:
        export_dir.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Warnung: Export-Ordner konnte nicht erstellt werden ({e}); nutze Skriptverzeichnis.")
        export_dir = script_dir

    out_path = export_dir / Path(out_path).name

    file = ifcopenshell.open(ifc_path)

    elements = file.by_type("IfcElement")
    result = [element_to_dict(file, el) for el in elements]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(result)} Elemente aus '{Path(ifc_path).name}' exportiert nach: {out_path}")


if __name__ == "__main__":
    main()
