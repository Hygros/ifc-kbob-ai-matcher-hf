import ifcopenshell
from typing import Dict, Any, List

def _gather_materials_from_definition(mat_def) -> List[Dict[str, Any]]:
    """Extrahiert alle Materialobjekte (Name, Description) aus einer Materialdefinition."""
    materials = []
    def add(mat):
        if not mat:
            return
        name = getattr(mat, "Name", None)
        desc = getattr(mat, "Description", None)
        # Nur aufnehmen, wenn mindestens eins nicht leer/None ist
        entry = {}
        if name not in (None, ""):
            entry["Name"] = name
        if desc not in (None, ""):
            entry["Description"] = desc
        if entry:
            materials.append(entry)
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
        add(mat_def)
    return materials

def extract_materials(file: ifcopenshell.file, el) -> List[Dict[str, Any]]:
    """Sammelt alle Materialobjekte (Name, Description) aus direkten und Typ-Zuweisungen."""
    candidates: List[Dict[str, Any]] = []
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
    # Filter Duplikate
    seen = set()
    unique = []
    for m in candidates:
        # Nur Dicts mit mindestens einem Feld
        if not m:
            continue
        key = (m.get("Name"), m.get("Description"))
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique
