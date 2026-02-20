import ifcopenshell
from typing import Dict, Any, List


def _not_empty(value: Any) -> bool:
    return value not in (None, "")


def _add_unique_entry(target: List[Dict[str, Any]], entry: Dict[str, Any]) -> None:
    if not entry:
        return
    if entry not in target:
        target.append(entry)

def _gather_materials_from_definition(mat_def) -> List[Dict[str, Any]]:
    """Extrahiert Materialdaten aus einer Materialdefinition (inkl. Layer/Profile/Constituent)."""
    materials: List[Dict[str, Any]] = []

    def add_from_material(mat, *, thickness=None, fallback_name=None):
        if not mat and not _not_empty(fallback_name):
            return

        entry: Dict[str, Any] = {}
        name = getattr(mat, "Name", None) if mat else fallback_name
        desc = getattr(mat, "Description", None) if mat else None

        if _not_empty(name):
            entry["Name"] = name
        if _not_empty(desc):
            entry["Description"] = desc
        if thickness is not None:
            entry["LayerThickness"] = thickness
        _add_unique_entry(materials, entry)

    if not mat_def:
        return materials

    if mat_def.is_a("IfcMaterial"):
        add_from_material(mat_def)

    elif mat_def.is_a("IfcMaterialLayerSetUsage"):
        ls = getattr(mat_def, "ForLayerSet", None)
        if ls:
            for layer in getattr(ls, "MaterialLayers", []) or []:
                add_from_material(
                    getattr(layer, "Material", None),
                    thickness=getattr(layer, "LayerThickness", None),
                )

    elif mat_def.is_a("IfcMaterialProfileSetUsage"):
        ps = getattr(mat_def, "ForProfileSet", None)
        if ps:
            profiles = getattr(ps, "MaterialProfiles", None)
            if profiles is None:
                profiles = getattr(ps, "Profiles", [])
            for prof in profiles or []:
                add_from_material(
                    getattr(prof, "Material", None),
                    fallback_name=getattr(prof, "Name", None),
                )

    elif mat_def.is_a("IfcMaterialConstituentSet"):
        constituents = getattr(mat_def, "MaterialConstituents", None)
        if constituents is None:
            constituents = getattr(mat_def, "Constituents", [])
        for cons in constituents or []:
            add_from_material(
                getattr(cons, "Material", None),
                fallback_name=getattr(cons, "Name", None),
            )

    elif mat_def.is_a("IfcMaterialLayerSet"):
        for layer in getattr(mat_def, "MaterialLayers", []) or []:
            add_from_material(
                getattr(layer, "Material", None),
                thickness=getattr(layer, "LayerThickness", None),
            )

    elif mat_def.is_a("IfcMaterialProfileSet"):
        profiles = getattr(mat_def, "MaterialProfiles", None)
        if profiles is None:
            profiles = getattr(mat_def, "Profiles", [])
        for prof in profiles or []:
            add_from_material(
                getattr(prof, "Material", None),
                fallback_name=getattr(prof, "Name", None),
            )

    elif mat_def.is_a("IfcMaterialList"):
        for mat in getattr(mat_def, "Materials", []) or []:
            add_from_material(mat)

    else:
        add_from_material(mat_def)

    return materials

def extract_materials(file: ifcopenshell.file, el) -> List[Dict[str, Any]]:
    """Sammelt Materialdaten aus direkter, Typ- und util-basierter Zuordnung."""
    candidates: List[Dict[str, Any]] = []

    try:
        import ifcopenshell.util.element as elem_util

        util_mat = elem_util.get_material(el)
        candidates.extend(_gather_materials_from_definition(util_mat))
    except Exception:
        pass

    def collect_from_object(obj):
        for inv in file.get_inverse(obj):
            if inv.is_a("IfcRelAssociatesMaterial"):
                mat_def = getattr(inv, "RelatingMaterial", None)
                candidates.extend(_gather_materials_from_definition(mat_def))

    collect_from_object(el)

    for inv in file.get_inverse(el):
        if inv.is_a("IfcRelDefinesByType") and getattr(inv, "RelatingType", None):
            collect_from_object(inv.RelatingType)

    # Filter Duplikate
    seen = set()
    unique: List[Dict[str, Any]] = []
    for m in candidates:
        # Nur Dicts mit mindestens einem Feld
        if not m:
            continue
        key = (
            m.get("Name"),
            m.get("Description"),
            m.get("LayerThickness"),
        )
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique
