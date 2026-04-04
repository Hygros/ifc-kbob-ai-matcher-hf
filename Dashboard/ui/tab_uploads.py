import json
import os

import pandas as pd
import streamlit as st

from Dashboard.config import (
    DEFAULT_SBERT_MODEL,
    IS_HF_SPACE,
    SBERT_MODEL_OPTIONS,
)
from Dashboard.domain.mapping import add_domain_defaults, add_galvanization_info, add_physical_quantity_columns, add_reinforcement_info
from Dashboard.services.ifc_pipeline import (
    _session_data_dir,
    _session_static_dir,
    get_upload_key,
    load_data,
    preload_sbert_resources,
    resolve_ifc_for_jsonl,
    save_ifc_for_viewer,
)
from Dashboard.services.ubp import run_ubp_calculation


def _clear_previous_mapping_selection(jsonl_path: str | None) -> None:
    if not jsonl_path or not os.path.exists(jsonl_path):
        return
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        changed = False
        for rec in records:
            for key in ["selected_kbob_material", "selected_ai_score", "selected_on"]:
                if key in rec:
                    rec.pop(key, None)
                    changed = True
        if changed:
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _render_embedded_viewer_tip() -> None:
    if not IS_HF_SPACE:
        return

    st.html(
        """
        <script>
        (() => {
            const rootWindow = window.parent;
            const bannerId = 'ifc-lite-embed-banner';

            const ensureEmbeddedBanner = () => {
                const existingBanner = rootWindow.document.getElementById(bannerId);

                const isEmbedded = (() => {
                    try {
                        return rootWindow.top !== rootWindow.self;
                    } catch (err) {
                        return true;
                    }
                })();

                const onHfSpaceDomain = /\\.hf\\.space$/i.test(rootWindow.location.hostname || '');

                if (!isEmbedded || !onHfSpaceDomain) {
                    if (existingBanner) {
                        existingBanner.remove();
                    }
                    return;
                }

                if (existingBanner) {
                    return;
                }

                const mountPoint =
                    rootWindow.document.querySelector('[data-testid="block-container"]') ||
                    rootWindow.document.querySelector('.block-container') ||
                    rootWindow.document.body;

                if (!mountPoint) {
                    return;
                }

                const banner = rootWindow.document.createElement('div');
                banner.id = bannerId;
                banner.style.display = 'flex';
                banner.style.flexWrap = 'wrap';
                banner.style.alignItems = 'center';
                banner.style.justifyContent = 'space-between';
                banner.style.gap = '0.75rem';
                banner.style.padding = '0.75rem 1rem';
                banner.style.margin = '0 0 0.75rem 0';
                banner.style.border = '1px solid #b6d7ff';
                banner.style.borderRadius = '10px';
                banner.style.background = '#eef6ff';
                banner.style.color = '#0f2b4c';

                const info = rootWindow.document.createElement('div');
                info.textContent = "Privacy notice: Uploaded IFC files are stored temporarily in a session-scoped directory and automatically deleted after 2 hours. Other users cannot access your files. For additional protection, consider using a private HF Space. Viewer tip: In embedded Spaces mode, the viewer's synchronized scrolling may be limited. For stable operation, open the space directly via the hf.space app.";
                info.style.fontSize = '0.92rem';
                info.style.fontWeight = '500';

                const link = rootWindow.document.createElement('a');
                const directUrl = `${rootWindow.location.origin}${rootWindow.location.pathname}${rootWindow.location.search}${rootWindow.location.hash}`;
                link.href = directUrl;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.textContent = 'open hf.space';
                link.style.display = 'inline-block';
                link.style.padding = '0.35rem 0.65rem';
                link.style.borderRadius = '8px';
                link.style.border = '1px solid #8ab8ff';
                link.style.background = '#ffffff';
                link.style.color = '#124070';
                link.style.fontWeight = '600';
                link.style.textDecoration = 'none';

                banner.appendChild(info);
                banner.appendChild(link);
                mountPoint.prepend(banner);
            };

            ensureEmbeddedBanner();
            setTimeout(ensureEmbeddedBanner, 120);
            setTimeout(ensureEmbeddedBanner, 450);
        })();
        </script>
        """,
    )


def render_tab_uploads() -> None:
    _render_embedded_viewer_tip()

    if "ai_mapping_data_version" not in st.session_state:
        st.session_state["ai_mapping_data_version"] = 0

    if st.session_state.get("selected_sbert_model") not in SBERT_MODEL_OPTIONS:
        st.session_state["selected_sbert_model"] = DEFAULT_SBERT_MODEL

    selected_model = st.selectbox(
        "SBERT-Modell",
        options=SBERT_MODEL_OPTIONS,
        key="selected_sbert_model",
        help="Modell für KI-basiertes Material-Matching.",
    )
    preloaded_model = st.session_state.get("preloaded_sbert_model")
    if selected_model != preloaded_model:
        with st.spinner(f"Lade SBERT-Modell: {selected_model}..."):
            preload_sbert_resources(selected_model)
        st.session_state["preloaded_sbert_model"] = selected_model
        st.success(f"SBERT-Modell aktiv: {selected_model}")

    active_model_display = st.session_state.get("selected_sbert_model", DEFAULT_SBERT_MODEL)
    st.caption(f"Aktives SBERT-Modell: {active_model_display}")

    last_used_model = st.session_state.get("last_used_sbert_model_for_matching")
    if last_used_model:
        st.caption(f"Zuletzt fürs IFC-Matching verwendet: {last_used_model}")

    upload = st.file_uploader("IFC-Datei hochladen", type=["ifc", "ifczip"])
    recalculate_mapping = st.button("Mapping berechnen", type="primary")
    loaded_path = None
    jsonl_path = None
    upload_key = get_upload_key(upload)
    active_model = st.session_state.get("selected_sbert_model", DEFAULT_SBERT_MODEL)
    current_processing_key = (upload_key, active_model) if upload_key is not None else None

    dashboard_data_dir = _session_data_dir()
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
            df = add_reinforcement_info(df)
            df = add_galvanization_info(df)
            df, ubp_db_path = run_ubp_calculation(str(jsonl_path), df)
            if df is not None:
                df = add_physical_quantity_columns(df)
            st.session_state["data"] = df
            st.session_state["ai_mapping_data_version"] = st.session_state.get("ai_mapping_data_version", 0) + 1
            st.session_state.pop("ai_mapping_last_rendered_token", None)
            st.session_state["jsonl_path"] = str(jsonl_path)
            static_dir = _session_static_dir()
            resolved_ifc = resolve_ifc_for_jsonl(static_dir, selected_jsonl)
            if resolved_ifc:
                session_id = st.session_state.get("session_id", "")
                st.session_state["ifc_filename"] = os.path.join(session_id, resolved_ifc)
            if ubp_db_path:
                st.session_state["ubp_db_path"] = ubp_db_path
            st.session_state["_success_message"] = f"JSONL geladen: {jsonl_path}"
            st.session_state["_just_loaded_jsonl"] = True
            st.rerun()

    if recalculate_mapping and upload is None:
        st.warning("Bitte zuerst eine IFC-Datei auswählen.")

    if recalculate_mapping and upload is not None:
        loaded_path = upload.name if hasattr(upload, "name") else str(upload)
        ifc_filename = save_ifc_for_viewer(upload)
        with st.spinner("IFC-Datei wird verarbeitet und exportiert..."):
            df, jsonl_path = load_data(upload, model_name=active_model)
        if df is not None:
            _clear_previous_mapping_selection(str(jsonl_path) if jsonl_path else None)
            if jsonl_path:
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    records = [json.loads(line) for line in f]
                df = pd.DataFrame(records)
            if "index" in df.columns:
                df = df.drop(columns=["index"])
            df = add_domain_defaults(df)
            df = add_reinforcement_info(df)
            df = add_galvanization_info(df)
            df, ubp_db_path = run_ubp_calculation(str(jsonl_path), df)
            if df is not None:
                df = add_physical_quantity_columns(df)
            st.session_state["data"] = df
            st.session_state["ai_mapping_data_version"] = st.session_state.get("ai_mapping_data_version", 0) + 1
            st.session_state.pop("ai_mapping_last_rendered_token", None)
            if jsonl_path:
                st.session_state["jsonl_path"] = str(jsonl_path)
            if ifc_filename:
                st.session_state["ifc_filename"] = ifc_filename
            if ubp_db_path:
                st.session_state["ubp_db_path"] = ubp_db_path
            st.session_state["last_used_sbert_model_for_matching"] = active_model
            st.session_state["_just_uploaded"] = True
            st.session_state["last_processing_key"] = current_processing_key
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
