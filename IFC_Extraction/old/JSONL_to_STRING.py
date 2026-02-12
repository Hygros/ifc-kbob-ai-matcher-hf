import json

# Pfad zur jsonl-Datei
input_path = r"C:\Users\wpx619\OneDrive - FHNW\Masterthesis\IFC-Modelle\Tekla\Bohrpfahl.jsonl"
output_path = r"C:\Users\wpx619\OneDrive - FHNW\Masterthesis\IFC-Modelle\Tekla\Bohrpfahl.txt"

# Die gewünschten Felder
fields = [
    "IfcEntity",
    "PredefinedType",
    "Name",
    "Material",
    "comment",
    "Status",
    "PROFILE.DIAMETER",
    "CastingMethod",
    "StructuralClass",
    "StrengthClass",
    "ExposureClass",
    "ReinforcementStrengthClass"
]

def clean_value(val):
    if isinstance(val, list):
        val = ", ".join(str(v) for v in val if v)
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()

sbert_lines = []

with open(input_path, "r", encoding="utf-8") as infile:
    for line in infile:
        obj = json.loads(line)
        values = [clean_value(obj.get(f, "")) for f in fields]
        # Entferne None- oder leere Werte
        values = [v for v in values if v]
        if values:
            sbert_line = " | ".join(values)
            sbert_lines.append(sbert_line)

with open(output_path, "w", encoding="utf-8") as outfile:
    for line in sbert_lines:
        outfile.write(line + "\n")

print(f"Fertig! {len(sbert_lines)} bereinigte Zeilen in {output_path} gespeichert.")