import ifcopenshell
import sys
import os

# Pfad zur IFC4-Datei anpassen
ifc_file_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "IFC-Modelle", "Tekla", "Bohrpfahl.ifc")

# IFC-Datei laden
ifc_file = ifcopenshell.open(ifc_file_path)

# Einheiten auslesen (IfcUnitAssignment)
# ifcopenshell vorausgesetzt
# Ziel: LENGTHUNIT, AREAUNIT, VOLUMEUNIT robust auslesen (SI + ConversionBased)

def unit_info(unit):
    info: dict = {"kind": None, "unit_type": None, "name": None, "prefix": None,
                  "scale_to_m": None, "human_readable": None}

    # Gemeinsame Felder
    if hasattr(unit, "UnitType"):
        info["unit_type"] = unit.UnitType  # z. B. 'LENGTHUNIT'
    if hasattr(unit, "Name"):
        info["name"] = getattr(unit, "Name", None)
    if hasattr(unit, "Prefix"):
        info["prefix"] = getattr(unit, "Prefix", None)

    # IfcSIUnit: Name ist METRE, Prefix kann MILLI, CENTI, ...
    if unit.is_a("IfcSIUnit"):
        # Basisskalen für Länge: METRE mit Prefix

        prefix = getattr(unit, "Prefix", None)

        # Skalen aus Prefix ableiten
        prefix_scale = {
            "EXA": 1e18, "PETA": 1e15, "TERA": 1e12, "GIGA": 1e9, "MEGA": 1e6,
            "KILO": 1e3, "HECTO": 1e2, "DECA": 1e1, None: 1.0, "DECI": 1e-1,
            "CENTI": 1e-2, "MILLI": 1e-3, "MICRO": 1e-6, "NANO": 1e-9,
            "PICO": 1e-12, "FEMTO": 1e-15, "ATTO": 1e-18
        }
        scale = prefix_scale.get(prefix, 1.0)

        info["kind"] = "SI"
        info["scale_to_m"] = scale  # 1 mm = 1e-3 m
        # Menschlich lesbar
        if info["unit_type"] == "LENGTHUNIT":
            info["human_readable"] = "millimetre" if prefix == "MILLI" else "metre"
        elif info["unit_type"] == "AREAUNIT":
            info["human_readable"] = "mm²" if prefix == "MILLI" else "m²"
        elif info["unit_type"] == "VOLUMEUNIT":
            info["human_readable"] = "mm³" if prefix == "MILLI" else "m³"
        return info

    # IfcConversionBasedUnit[WithUnit]: z. B. 'inch', 'foot', aber auch 'millimetre'
    if unit.is_a("IfcConversionBasedUnit") or unit.is_a("IfcConversionBasedUnitWithUnit"):
        info["kind"] = "CONVERSION"
        # ConversionFactor: IfcMeasureWithUnit(ValueComponent, UnitComponent)
        conv = getattr(unit, "ConversionFactor", None)
        if conv:
            # ValueComponent kann IfcLengthMeasure, IfcReal etc. sein
            value = getattr(conv, "ValueComponent", None)
            val = None
            if value is not None and hasattr(value, "wrappedValue"):
                val = float(value.wrappedValue)
            elif value is not None:
                try:
                    val = float(value)
                except Exception:
                    val = None
            # UnitComponent ist meist IfcSIUnit(METRE[, Prefix])
            ucomp = getattr(conv, "UnitComponent", None)
            base_scale = 1.0
            if ucomp and ucomp.is_a("IfcSIUnit"):
                prefix = getattr(ucomp, "Prefix", None)
                prefix_scale = {
                    "EXA": 1e18, "PETA": 1e15, "TERA": 1e12, "GIGA": 1e9, "MEGA": 1e6,
                    "KILO": 1e3, "HECTO": 1e2, "DECA": 1e1, None: 1.0, "DECI": 1e-1,
                    "CENTI": 1e-2, "MILLI": 1e-3, "MICRO": 1e-6, "NANO": 1e-9,
                    "PICO": 1e-12, "FEMTO": 1e-15, "ATTO": 1e-18
                }
                base_scale = prefix_scale.get(getattr(ucomp, "Prefix", None), 1.0)
            info["scale_to_m"] = (val * base_scale) if (val is not None) else None

        # menschenlesbarer Name, falls gesetzt (z. B. 'inch', 'millimetre')
        info["human_readable"] = info["name"]
        return info

    # Fallback
    return info

# Verwendung:
unit_assignments = ifc_file.by_type("IfcUnitAssignment")
for assignment in unit_assignments:
    for unit in assignment.Units:
        if hasattr(unit, "UnitType") and unit.UnitType in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT"):
            info = unit_info(unit)
            print(f"Einheitentyp: {info['unit_type']}")
            print(f"Art: {info['kind']}")
            print(f"Name: {info['name']}")
            print(f"Prefix: {info['prefix']}")
            print(f"Skalierung nach Meter: {info['scale_to_m']}")
            print(f"Lesbar: {info['human_readable']}")
            print()
