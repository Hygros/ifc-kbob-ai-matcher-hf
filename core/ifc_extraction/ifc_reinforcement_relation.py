import ifcopenshell
import sys
import os

# IFC-Datei laden (Pfad als CLI-Argument oder Beispielpfad)
_default_ifc = os.path.join(os.path.dirname(__file__), "..", "..", "IFC-Modelle", "Tekla", "Bohrpfahl-Bewehrt-Beziehung.ifc")
ifc_file = ifcopenshell.open(sys.argv[1] if len(sys.argv) > 1 else _default_ifc)

def get_parent_assembly(element):
    """Geht die Aggregationshierarchie nach oben (IfcRelAggregates), bis IfcElementAssembly gefunden wird."""
    for rel in getattr(element, "DecomposedBy", []) or []:
        if rel.is_a("IfcRelAggregates"):
            for obj in rel.RelatedObjects or []:
                if obj.is_a("IfcElementAssembly"):
                    return obj
    # Alternativ: Suche nach oben über IsDecomposedBy
    for rel in getattr(element, "IsDecomposedBy", []) or []:
        if rel.is_a("IfcRelAggregates"):
            for obj in rel.RelatedObjects or []:
                if obj.is_a("IfcElementAssembly"):
                    return obj
    return None

reinforcements = ifc_file.by_type("IfcReinforcingBar")


rel_aggregates = ifc_file.by_type("IfcRelAggregates")

for reinforcement in reinforcements:
    print(f"\nBewehrung: {reinforcement.GlobalId} ({reinforcement.Name})")

    # Suche nach IfcElementAssembly (z.B. Bohrpfahl) über IfcRelAggregates
    for rel in rel_aggregates:
        if reinforcement in (rel.RelatedObjects or []):
            parent = rel.RelatingObject
            if parent.is_a("IfcElementAssembly"):
                print(f"  -> Gehört zu Assembly: {parent.GlobalId} ({parent.Name})")
            elif parent.is_a("IfcPile"):
                print(f"  -> Gehört zu Pile: {parent.GlobalId} ({parent.Name})")

    # Materialzuordnung
    for rel in getattr(reinforcement, "HasAssociations", []) or []:
        if rel.is_a("IfcRelAssociatesMaterial"):
            material = getattr(rel, "RelatingMaterial", None)
            if material:
                print(f"  -> Material: {getattr(material, 'Name', str(material))}")