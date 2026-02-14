import os
import sys

import pandas as pd
import streamlit as st

from Dashboard.config import INDICATOR_DB_TO_COLUMN


DASHBOARD_DIR = os.path.dirname(os.path.dirname(__file__))
APP_ROOT = os.path.dirname(DASHBOARD_DIR)
if APP_ROOT not in sys.path:
    sys.path.append(APP_ROOT)

from calculate_ubp21_per_element import calculate_ubp_for_jsonl


def apply_ubp_results(df: pd.DataFrame, results: list) -> pd.DataFrame:
    if not results:
        return df
    results_df = pd.DataFrame(results)
    for src, dst in INDICATOR_DB_TO_COLUMN.items():
        if src in results_df.columns:
            results_df[dst] = results_df[src]
    keep_cols = ["GUID"]
    for src, dst in INDICATOR_DB_TO_COLUMN.items():
        if src in results_df.columns:
            keep_cols.append(src)
        if dst in results_df.columns:
            keep_cols.append(dst)
    keep_cols = list(dict.fromkeys(keep_cols))
    results_df = results_df[keep_cols].copy()
    merged = df.merge(results_df, on="GUID", how="left", suffixes=("", "_calc"))
    indicator_columns = list(dict.fromkeys(list(INDICATOR_DB_TO_COLUMN.keys()) + list(INDICATOR_DB_TO_COLUMN.values())))
    for col_name in indicator_columns:
        calc_col = f"{col_name}_calc"
        if calc_col in merged.columns:
            if col_name in merged.columns:
                merged[col_name] = merged[calc_col].fillna(merged[col_name])
            else:
                merged[col_name] = merged[calc_col]
            merged = merged.drop(columns=[calc_col])
    return merged


def run_ubp_calculation(jsonl_path: str | None, df: pd.DataFrame | None):
    if not jsonl_path or df is None:
        return df, None
    if "selected_kbob_material" not in df.columns:
        return df, None
    if df["selected_kbob_material"].isna().all():
        return df, None
    export_dir = os.path.join(APP_ROOT, "IFC-Modelle", "Resultate_UBP_Berechnung")
    try:
        db_path, results = calculate_ubp_for_jsonl(jsonl_path, export_dir=export_dir)
    except Exception as exc:
        st.error(f"UBP-Berechnung fehlgeschlagen: {exc}")
        return df, None
    df = apply_ubp_results(df, results)
    return df, db_path
