import json
import re

import pandas as pd


def add_domain_defaults(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    colmap = {
        "ifc_entity": "IfcEntity",
        "element_name": "Name",
        "ifc_material": "Material",
    }
    for old, new in colmap.items():
        if old not in df.columns and new in df.columns:
            df[old] = df[new]

    if "volume_m3" not in df.columns:
        if "NetVolume" in df.columns:
            df["volume_m3"] = df["NetVolume"]
            if "GrossVolume" in df.columns:
                df["volume_m3"] = df["volume_m3"].fillna(df["GrossVolume"])
        elif "GrossVolume" in df.columns:
            df["volume_m3"] = df["GrossVolume"]
    elif "GrossVolume" in df.columns and "NetVolume" in df.columns:
        df["volume_m3"] = df["volume_m3"].fillna(df["NetVolume"]).fillna(df["GrossVolume"])

    if "kbob_material" not in df.columns:
        df["kbob_material"] = df["ifc_material"] if "ifc_material" in df.columns else None
    else:
        if "ifc_material" in df.columns:
            df["kbob_material"] = df["kbob_material"].fillna(df["ifc_material"])
        else:
            df["kbob_material"] = df["kbob_material"].fillna("Unbekannt")

    if "selected_kbob_material" in df.columns:
        df["kbob_material"] = df["selected_kbob_material"].fillna(df["kbob_material"])

    if "density_kg_m3" not in df.columns:
        df["density_kg_m3"] = 2350
    else:
        df["density_kg_m3"] = df["density_kg_m3"].fillna(2350)

    if "volume_m3" not in df.columns:
        df["volume_m3"] = 0.0

    df["mass_kg"] = df["volume_m3"] * df["density_kg_m3"]

    for col in ["gwp_kgco2eq", "ubp", "penre_kwh_oil_eq"]:
        if col not in df:
            df[col] = 0.0
        df[col] = df[col].fillna(0.0)

    return df


def _normalize_top_k_matches(matches) -> list[dict]:
    if not isinstance(matches, list):
        return []
    normalized = []
    for match in matches:
        if not isinstance(match, dict):
            continue
        material = match.get("material")
        score_raw = match.get("score")
        score = None
        if score_raw is not None:
            try:
                score = round(float(score_raw), 6)
            except (TypeError, ValueError):
                score = None
        normalized.append({"material": material, "score": score})
    normalized.sort(
        key=lambda item: (
            item.get("score") is None,
            -(item.get("score") if item.get("score") is not None else float("-inf")),
            str(item.get("material") or "").lower(),
        )
    )
    return normalized


def build_ai_mapping_groups(base_df: pd.DataFrame) -> list[dict]:
    fields = ["IfcEntity", "PredefinedType", "Name", "Description", "Material", "Durchmesser", "MaterialLayerIndex"]
    groups: dict[tuple, dict] = {}
    for _, row in base_df.iterrows():
        row_dict = row.to_dict()
        normalized_matches = _normalize_top_k_matches(row_dict.get("top_k_matches"))
        signature = tuple(str(row_dict.get(field) or "").strip() for field in fields) + (
            json.dumps(normalized_matches, ensure_ascii=False, sort_keys=True),
        )
        if signature not in groups:
            groups[signature] = {
                "row": row_dict,
                "guids": [],
                "matches": normalized_matches,
            }
        groups[signature]["guids"].append(row_dict.get("GUID"))
    grouped_rows = list(groups.values())
    grouped_rows.sort(
        key=lambda group: (
            str(group["row"].get("IfcEntity") or ""),
            str(group["row"].get("Name") or ""),
            str(group["row"].get("GUID") or ""),
        )
    )
    return grouped_rows
