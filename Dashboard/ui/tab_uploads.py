import json
import os

import pandas as pd
import streamlit as st

from Dashboard.domain.mapping import add_domain_defaults
from Dashboard.services.ifc_pipeline import get_upload_key, load_data, resolve_ifc_for_jsonl, save_ifc_for_viewer
from Dashboard.services.ubp import run_ubp_calculation


def render_tab_uploads() -> None:
    upload = st.file_uploader("IFC-Datei hochladen", type=["ifc", "ifczip"])
    loaded_path = None
    jsonl_path = None
    upload_key = get_upload_key(upload)
    last_upload_key = st.session_state.get("last_upload_key")

    dashboard_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    try:
        jsonl_files = [f for f in os.listdir(dashboard_data_dir) if f.endswith(".jsonl")]
    except Exception:
        jsonl_files = []

    if jsonl_files:
        selected_jsonl = st.selectbox("Vorhandene JSONL-Datei laden", jsonl_files, index=0)
        if st.button("JSONL laden"):
            jsonl_path = os.path.join(dashboard_data_dir, selected_jsonl)
            with open(jsonl_path, "r", encoding="utf-8") as f:
                records = [json.loads(line) for line in f]
            df = pd.DataFrame(records)
            if "index" in df.columns:
                df = df.drop(columns=["index"])
            df = add_domain_defaults(df)
            df, ubp_db_path = run_ubp_calculation(str(jsonl_path), df)
            st.session_state["data"] = df
            st.session_state["jsonl_path"] = str(jsonl_path)
            static_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"))
            resolved_ifc = resolve_ifc_for_jsonl(static_dir, selected_jsonl)
            if resolved_ifc:
                st.session_state["ifc_filename"] = resolved_ifc
            if ubp_db_path:
                st.session_state["ubp_db_path"] = ubp_db_path
            st.session_state["_success_message"] = f"JSONL geladen: {jsonl_path}"
            st.session_state["_just_loaded_jsonl"] = True
            st.rerun()

    if upload is not None and upload_key != last_upload_key:
        loaded_path = upload.name if hasattr(upload, "name") else str(upload)
        ifc_filename = save_ifc_for_viewer(upload)
        with st.spinner("IFC-Datei wird verarbeitet und exportiert..."):
            df, jsonl_path = load_data(upload)
        if df is not None:
            if "index" in df.columns:
                df = df.drop(columns=["index"])
            df = add_domain_defaults(df)
            df, ubp_db_path = run_ubp_calculation(str(jsonl_path), df)
            st.session_state["data"] = df
            if jsonl_path:
                st.session_state["jsonl_path"] = str(jsonl_path)
            if ifc_filename:
                st.session_state["ifc_filename"] = ifc_filename
            if ubp_db_path:
                st.session_state["ubp_db_path"] = ubp_db_path
            st.session_state["_just_uploaded"] = True
            st.session_state["last_upload_key"] = upload_key
            msg = f"Daten geladen: {loaded_path}"
            if jsonl_path:
                msg += f" | JSONL: {jsonl_path}"
            st.session_state["_success_message"] = msg
            st.rerun()
        else:
            st.error("Fehler beim Parsen der IFC-Datei.")
    elif st.session_state.get("_just_uploaded"):
        msg = st.session_state.pop("_success_message", None)
        if msg:
            st.success(msg)
        st.session_state["_just_uploaded"] = False
    elif st.session_state.get("_just_loaded_jsonl"):
        msg = st.session_state.pop("_success_message", None)
        if msg:
            st.success(msg)
        st.session_state["_just_loaded_jsonl"] = False
