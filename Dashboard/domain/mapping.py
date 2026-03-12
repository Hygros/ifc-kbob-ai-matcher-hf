import json
import re

import numpy as np
import pandas as pd

from Dashboard.config import (
    CONCRETE_KEYWORDS,
    DEFAULT_REINFORCEMENT_RATIO,
)

# Entity types that should be grouped by entity only (not by all fields)
REINFORCEMENT_ENTITIES: set[str] = {"IfcReinforcingBar", "IfcReinforcingMesh", "IfcTendon"}


# ---------------------------------------------------------------------------
# Beton-Erkennung  (Concrete detection)
# ---------------------------------------------------------------------------

def is_concrete_material(material_name) -> bool:
    """Return True when *material_name* contains a concrete-related keyword.

    Handles ``str``, ``list[str]`` and ``NaN``/``None`` gracefully.
    """
    if material_name is None:
        return False
    if isinstance(material_name, list):
        combined = " ".join(str(m) for m in material_name if m is not None)
    else:
        combined = str(material_name)
    combined_lower = combined.lower()
    return any(kw in combined_lower for kw in CONCRETE_KEYWORDS)


# ---------------------------------------------------------------------------
# Bewehrungsinformationen pro Element  (Reinforcement enrichment)
# ---------------------------------------------------------------------------

def _get_default_ratio(ifc_entity: str | None) -> float:
    """Look up the default reinforcement ratio (kg/m³) for an IfcEntity type."""
    if ifc_entity and ifc_entity in DEFAULT_REINFORCEMENT_RATIO:
        return DEFAULT_REINFORCEMENT_RATIO[ifc_entity]
    return DEFAULT_REINFORCEMENT_RATIO.get("_default", 100.0)


def _to_float_safe(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def add_reinforcement_info(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich *df* with reinforcement detection columns.

    New columns:
        is_concrete                – bool
        has_modeled_rebar          – bool (from JSONL field ``HasModeledRebar``)
        reinforcement_ratio_source – ``"ifc"`` | ``"default"`` | None
        reinforcement_ratio_kg_m3 – float | NaN
        reinforcement_mass_kg      – float | NaN  (volume_m3 × ratio)
        reinforcement_status       – ``"explicit"`` | ``"assumed"`` | ``"none"`` | ``"no_material"``
    """
    df = df.copy()

    # --- is_concrete ---
    mat_col = "Material" if "Material" in df.columns else "ifc_material"
    if mat_col in df.columns:
        df["is_concrete"] = df[mat_col].apply(is_concrete_material)
    else:
        df["is_concrete"] = False

    # Also consider the selected KBOB material: if user chose a concrete
    # KBOB entry, treat it as concrete even if the IFC material is missing
    if "kbob_material" in df.columns:
        df["is_concrete"] = df["is_concrete"] | df["kbob_material"].apply(is_concrete_material)

    # --- has_modeled_rebar ---
    if "HasModeledRebar" in df.columns:
        df["has_modeled_rebar"] = pd.Series(
            np.where(df["HasModeledRebar"].isna(), False, df["HasModeledRebar"]),
            index=df.index,
        ).astype(bool)
    else:
        df["has_modeled_rebar"] = False

    # --- reinforcement_ratio_source & reinforcement_ratio_kg_m3 ---
    def _ratio_row(row):
        ifc_entity = str(row.get("IfcEntity") or "").strip()
        # Skip IfcReinforcingBar itself
        if ifc_entity == "IfcReinforcingBar":
            return pd.Series({"reinforcement_ratio_source": None, "reinforcement_ratio_kg_m3": None})
        ifc_ratio = _to_float_safe(row.get("ReinforcementVolumeRatio"))
        if ifc_ratio is not None and ifc_ratio > 0:
            return pd.Series({"reinforcement_ratio_source": "ifc", "reinforcement_ratio_kg_m3": ifc_ratio})
        return pd.Series({"reinforcement_ratio_source": "default", "reinforcement_ratio_kg_m3": _get_default_ratio(ifc_entity)})

    ratio_df = df.apply(_ratio_row, axis=1)
    df["reinforcement_ratio_source"] = ratio_df["reinforcement_ratio_source"]
    df["reinforcement_ratio_kg_m3"] = ratio_df["reinforcement_ratio_kg_m3"]

    # --- reinforcement_status ---
    def _status(row):
        ifc_entity = str(row.get("IfcEntity") or "").strip()
        if ifc_entity == "IfcReinforcingBar":
            return "none"
        has_material = bool(row.get("Material")) and str(row.get("Material", "")).strip() not in ("", "nan", "None", "[]")
        if not has_material:
            # Also check kbob_material
            kbob = str(row.get("kbob_material") or "").strip()
            if kbob and kbob not in ("Unbekannt", "nan", "None"):
                has_material = True
        if not has_material:
            return "no_material"
        if not row.get("is_concrete"):
            return "none"
        if row.get("has_modeled_rebar"):
            return "explicit"
        return "assumed"

    df["reinforcement_status"] = df.apply(_status, axis=1)

    # --- reinforcement_mass_kg ---
    vol = df.get("volume_m3", pd.Series(dtype=float))
    ratio = df["reinforcement_ratio_kg_m3"]
    df["reinforcement_mass_kg"] = vol * ratio
    # Only meaningful for "assumed" status
    df.loc[~df["reinforcement_status"].isin(["assumed"]), "reinforcement_mass_kg"] = None

    return df


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


def _merge_matches(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Merge two normalised match lists, keeping the highest score per material."""
    best: dict[str, float | None] = {}
    for m in existing + incoming:
        mat = m.get("material")
        if not mat:
            continue
        score = m.get("score")
        prev = best.get(mat)
        if prev is None or (score is not None and (prev is None or score > prev)):
            best[mat] = score
    merged = [{"material": mat, "score": sc} for mat, sc in best.items()]
    merged.sort(
        key=lambda item: (
            item.get("score") is None,
            -(item["score"] if item.get("score") is not None else float("-inf")),
            str(item.get("material") or "").lower(),
        )
    )
    return merged


def build_ai_mapping_groups(base_df: pd.DataFrame) -> list[dict]:
    fields = ["IfcEntity", "PredefinedType", "Name", "Description", "Material", "Durchmesser", "MaterialLayerIndex"]
    merge_fields = ["PredefinedType", "Name", "Description", "Material", "Durchmesser", "MaterialLayerIndex"]
    groups: dict[tuple, dict] = {}
    for _, row in base_df.iterrows():
        row_dict = row.to_dict()
        normalized_matches = _normalize_top_k_matches(row_dict.get("top_k_matches"))
        ifc_entity = str(row_dict.get("IfcEntity") or "").strip()
        guid = row_dict.get("GUID")
        layer_idx = row_dict.get("MaterialLayerIndex")

        if ifc_entity in REINFORCEMENT_ENTITIES:
            # Group all elements of the same reinforcement entity type together
            signature = ("__rebar__", ifc_entity)
            if signature in groups:
                grp = groups[signature]
                # Merge: set fields to None where values differ
                for field in merge_fields:
                    existing_val = str(grp["row"].get(field) or "").strip()
                    new_val = str(row_dict.get(field) or "").strip()
                    if existing_val != new_val:
                        grp["row"][field] = None
                grp["matches"] = _merge_matches(grp["matches"], normalized_matches)
            else:
                groups[signature] = {
                    "row": row_dict,
                    "guids": [],
                    "guid_layer_map": {},
                    "matches": normalized_matches,
                }
            groups[signature]["guids"].append(guid)
            groups[signature]["guid_layer_map"][guid] = layer_idx
            # Collect aggregate child GUIDs for viewer selection
            child_guids = row_dict.get("AggregateChildGUIDs")
            if isinstance(child_guids, list):
                groups[signature].setdefault("aggregate_child_guids", []).extend(child_guids)
        else:
            signature = tuple(str(row_dict.get(field) or "").strip() for field in fields) + (
                json.dumps(normalized_matches, ensure_ascii=False, sort_keys=True),
            )
            if signature not in groups:
                groups[signature] = {
                    "row": row_dict,
                    "guids": [],
                    "guid_layer_map": {},
                    "matches": normalized_matches,
                }
            groups[signature]["guids"].append(guid)
            groups[signature]["guid_layer_map"][guid] = layer_idx
            # Collect aggregate child GUIDs for viewer selection
            child_guids = row_dict.get("AggregateChildGUIDs")
            if isinstance(child_guids, list):
                groups[signature].setdefault("aggregate_child_guids", []).extend(child_guids)

    grouped_rows = list(groups.values())
    grouped_rows.sort(
        key=lambda group: (
            str(group["row"].get("IfcEntity") or ""),
            str(group["row"].get("Name") or ""),
            str(group["row"].get("GUID") or ""),
        )
    )
    return grouped_rows
