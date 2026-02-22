import json
import os
import re
from pathlib import Path
from urllib.parse import quote, urlencode

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from Dashboard.domain.mapping import add_domain_defaults, build_ai_mapping_groups
from Dashboard.services.ubp import run_ubp_calculation
from Dashboard.services.viewer import ensure_static_server, render_viewer_bridge, set_active_guid


def _get_jsonl_path() -> Path | None:
    jsonl_path = st.session_state.get("jsonl_path")
    return Path(jsonl_path) if jsonl_path else None


def _load_selection_jsonl(jsonl_path: Path) -> pd.DataFrame:
    if jsonl_path and jsonl_path.exists():
        with open(jsonl_path, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f]
        selection_rows = []
        for rec in records:
            selection_rows.append(
                {
                    "GUID": rec.get("GUID"),
                    "MaterialLayerIndex": rec.get("MaterialLayerIndex"),
                    "Material KBOB": rec.get("selected_kbob_material"),
                    "AI Score": rec.get("selected_ai_score"),
                    "SelectedOn": rec.get("selected_on"),
                }
            )
        return pd.DataFrame(selection_rows)
    return pd.DataFrame(columns=["GUID", "MaterialLayerIndex", "Material KBOB", "AI Score", "SelectedOn"])


def _selection_key(guid, layer_index):
    def _normalize_layer_index(value):
        if pd.isna(value):
            return None
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value)
        text = str(value).strip()
        if not text:
            return None
        try:
            numeric = float(text)
            if numeric.is_integer():
                return str(int(numeric))
        except (TypeError, ValueError):
            pass
        return text

    if pd.isna(guid):
        return None
    guid_str = str(guid).strip()
    if not guid_str:
        return None
    normalized_layer_index = _normalize_layer_index(layer_index)
    if normalized_layer_index is None:
        return (guid_str, None)
    return (guid_str, normalized_layer_index)


def _update_jsonl_with_selection(jsonl_path: Path, selection_df: pd.DataFrame) -> None:
    if not jsonl_path.exists():
        return
    with open(jsonl_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    selection_lookup = {}
    for _, row in selection_df.iterrows():
        key = _selection_key(row.get("GUID"), row.get("MaterialLayerIndex"))
        if key is not None:
            selection_lookup[key] = row

    for rec in records:
        key = _selection_key(rec.get("GUID"), rec.get("MaterialLayerIndex"))
        if key in selection_lookup:
            rec["selected_kbob_material"] = selection_lookup[key].get("Material KBOB")
            rec["selected_ai_score"] = selection_lookup[key].get("AI Score")
            rec["selected_on"] = selection_lookup[key].get("SelectedOn")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _as_selection_dict(sel_df: pd.DataFrame) -> dict:
    material_col = "Material KBOB" if "Material KBOB" in sel_df.columns else (
        "SelectedMaterial" if "SelectedMaterial" in sel_df.columns else None
    )
    if material_col is None:
        return {}
    lookup = {}
    for _, row in sel_df.iterrows():
        key = _selection_key(row.get("GUID"), row.get("MaterialLayerIndex"))
        if key is not None:
            lookup[key] = row.get(material_col)
    return lookup


def _get_score_lookup(matches: list) -> dict:
    return {match.get("material"): match.get("score") for match in matches or []}


NO_SELECTION_LABEL = "-- keine Auswahl --"


def _render_viewer(ifc_filename: str | None, active_guid: str | None, active_guids: list[str]) -> None:
    static_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"))
    if ifc_filename:
        ifc_path = os.path.join(static_dir, ifc_filename)
    else:
        ifc_path = None

    if ifc_path and os.path.exists(ifc_path):
        ensure_static_server(static_dir, port=8080)
        file_stat = os.stat(ifc_path)
        cache_bust = f"{file_stat.st_mtime_ns}-{file_stat.st_size}"
        file_url = f"http://127.0.0.1:8080/{quote(str(ifc_filename))}?v={cache_bust}"
        viewer_query = urlencode({"file_url": file_url, "v": cache_bust})
        viewer_url = f"http://localhost:3000/?{viewer_query}"

        st.markdown(
            f"<div class='viewer-sticky'><iframe class='viewer-iframe' src='{viewer_url}'></iframe></div>",
            unsafe_allow_html=True,
        )
        components.html(
            """
            <script>
            (() => {
                const applySticky = () => {
                    const viewer = window.parent.document.querySelector('.viewer-sticky');
                    if (!viewer) return;
                    const column = viewer.closest('[data-testid="stColumn"]');
                    const target = column || viewer.closest('[data-testid="stElementContainer"]') || viewer.parentElement;
                    if (target) {
                        target.style.position = 'sticky';
                        target.style.top = '5rem';
                        target.style.alignSelf = 'flex-start';
                        target.style.zIndex = '1';
                    }
                };

                applySticky();
                setTimeout(applySticky, 250);
                setTimeout(applySticky, 1000);
            })();
            </script>
            """,
            height=0,
            width=0,
        )
        render_viewer_bridge(active_guid, active_guids)
    else:
        st.info("Kein IFC-Modell fuer den Viewer gefunden. Lade eine IFC-Datei im Upload-Tab.")


def render_tab_ai_mapping(df: pd.DataFrame | None) -> None:
    if df is None:
        st.info("Noch keine Daten. Lade in Tab Uploads eine Datei.")
        return

    st.markdown(
        """
        <style>
        .viewer-iframe {
            width: 100%;
            height: 720px;
            border: none;
            margin: 0 auto 1rem auto;
            display: block;
        }
        @media (min-width: 992px) {
            [data-testid="stVerticalBlock"],
            [data-testid="stHorizontalBlock"],
            [data-testid="stColumn"],
            [data-testid="stColumn"] > div,
            .element-container,
            .block-container {
                overflow: visible;
            }
            .viewer-sticky {
                position: sticky;
                top: 1rem;
                align-self: flex-start;
                z-index: 1;
                will-change: transform;
                height: fit-content;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    ifc_filename = st.session_state.get("ifc_filename")
    active_guid = st.session_state.get("viewer_selected_guid")
    active_guids = st.session_state.get("viewer_selected_guids")
    if not isinstance(active_guid, str):
        active_guid = None
        st.session_state["viewer_selected_guid"] = None
    if not isinstance(active_guids, list):
        active_guids = []
        st.session_state["viewer_selected_guids"] = []
    active_guids = [guid for guid in active_guids if isinstance(guid, str) and guid.strip()]
    if active_guid and active_guid not in active_guids:
        active_guids = [active_guid]
        st.session_state["viewer_selected_guids"] = active_guids

    left_width_percent = st.slider(
        "Breite linke Spalte (%)",
        min_value=0,
        max_value=100,
        value=45,
        step=5,
        key="ai_mapping_left_width_percent",
        help="Steuert das Breitenverhältnis zwischen linker Liste und rechtem Viewer.",
    )
    right_width_percent = 100 - left_width_percent

    left_col, right_col = st.columns([left_width_percent, right_width_percent])

    with right_col:
        _render_viewer(ifc_filename, active_guid, active_guids)

    with left_col:
        active_guid = st.session_state.get("viewer_selected_guid") if isinstance(st.session_state.get("viewer_selected_guid"), str) else None
        base_cols = ["IfcEntity", "PredefinedType", "Name", "GUID", "MaterialLayerIndex", "Description", "Material", "Durchmesser", "top_k_matches"]
        if df is not None and hasattr(df, "columns"):
            for col in base_cols:
                if col not in df.columns:
                    df[col] = None
            base = df[base_cols].copy()
            base["Durchmesser"] = base["Durchmesser"].astype(str)
        else:
            st.warning("Daten konnten nicht geladen werden oder sind leer.")
            base = pd.DataFrame(columns=base_cols)

        if base.empty:
            st.stop()

        jsonl_path = _get_jsonl_path()

        data_version = st.session_state.get("ai_mapping_data_version", 0)
        refresh_token = (
            data_version,
            st.session_state.get("last_processing_key"),
            st.session_state.get("jsonl_path"),
            len(base),
        )
        previous_token = st.session_state.get("ai_mapping_last_rendered_token")
        if previous_token != refresh_token:
            stale_keys = [key for key in st.session_state.keys() if str(key).startswith("sel_group_")]
            for key in stale_keys:
                del st.session_state[key]
            st.session_state["ai_mapping_last_rendered_token"] = refresh_token

        if jsonl_path is not None:
            sel_df = _load_selection_jsonl(jsonl_path)
            prev_sel = _as_selection_dict(sel_df)
        else:
            sel_df = pd.DataFrame(columns=["GUID", "MaterialLayerIndex", "Material KBOB", "AI Score", "SelectedOn"])
            prev_sel = {}

        grouped_base = build_ai_mapping_groups(base)

        updates = []
        for group_index, group in enumerate(grouped_base):
            row_data = group["row"]
            guids = [guid for guid in group["guids"] if isinstance(guid, str)]
            if not guids:
                continue
            primary_guid = guids[0]
            layer_index = row_data.get("MaterialLayerIndex")

            def is_valid(value):
                if value is None:
                    return False
                string_value = str(value).strip()
                if not string_value:
                    return False
                normalized = re.sub(r"[\s_\-]+", "", string_value).lower()
                invalid_tokens = {"nan", "none", "null", "undefined", "notdefined", "n/a", "na", "-"}
                return normalized not in invalid_tokens

            def format_label_value(value):
                if isinstance(value, list):
                    cleaned = [str(item).strip() for item in value if item is not None and str(item).strip()]
                    return ", ".join(cleaned)
                return str(value).strip()

            label_parts = []
            for key in ["IfcEntity", "PredefinedType", "Name", "Description", "Material"]:
                val = row_data.get(key)
                formatted_val = format_label_value(val)
                if is_valid(formatted_val):
                    label_parts.append(formatted_val)
            durchmesser = row_data.get("Durchmesser")
            if is_valid(durchmesser):
                label_parts.append(f"Ø {durchmesser}")
            element_label = " | ".join(label_parts)
            if len(guids) > 1:
                element_label = f"{element_label} <span style='color: #999;'>({len(guids)} Elemente)</span>"
            is_active = bool(active_guid) and active_guid in guids
            active_style = "background-color: #fff3cd; padding: 0.15rem 0.35rem; border-radius: 4px;" if is_active else ""
            guid_attr = ",".join(str(guid).replace("'", "") for guid in guids)
            st.markdown(
                f"<div class='ai-map-group-label' data-guids='{guid_attr}' style='font-size: 1.1em; font-weight: bold; margin-bottom: 0.2em; text-align: left; width: 100%; {active_style}'>{element_label}</div>",
                unsafe_allow_html=True,
            )

            matches = group["matches"]
            material_options = [
                f"{m.get('material')} (Score: {m.get('score'):.3f})" if m.get("score") is not None else m.get("material")
                for m in matches
            ]
            material_lookup = {
                f"{m.get('material')} (Score: {m.get('score'):.3f})" if m.get("score") is not None else m.get("material"): m.get("material")
                for m in matches
            }
            options = [NO_SELECTION_LABEL] + material_options
            scores = _get_score_lookup(matches)
            stored_materials = []
            for guid in guids:
                selection_key = _selection_key(guid, layer_index)
                if selection_key in prev_sel:
                    value = prev_sel.get(selection_key)
                    if pd.isna(value):
                        value = None
                    stored_materials.append(value)

            if stored_materials and len(stored_materials) == len(guids):
                unique_materials = {"__NONE__" if value is None else value for value in stored_materials}
                if len(unique_materials) == 1 and stored_materials[0] is not None:
                    default_material = stored_materials[0]
                else:
                    default_material = matches[0].get("material") if matches else None
            else:
                default_material = matches[0].get("material") if matches else None
            if default_material:
                default_label = next((label for label, mat in material_lookup.items() if mat == default_material), NO_SELECTION_LABEL)
            else:
                default_label = NO_SELECTION_LABEL

            sel_label = st.selectbox(
                "Materialauswahl",
                options=options,
                index=(options.index(default_label) if default_label in options else 0),
                key=f"sel_group_{data_version}_{group_index}_{primary_guid}",
                on_change=set_active_guid,
                args=(primary_guid, guids),
                label_visibility="collapsed",
            )

            sel_material = None if sel_label == NO_SELECTION_LABEL else material_lookup.get(sel_label)
            for guid in guids:
                updates.append(
                    {
                        "GUID": guid,
                        "MaterialLayerIndex": layer_index,
                        "Material KBOB": sel_material,
                        "AI Score": scores.get(sel_material) if sel_material else None,
                    }
                )

        submitted = st.button("Auswahl speichern")
        if submitted:
            out = pd.DataFrame(updates)
            out["SelectedOn"] = pd.Timestamp.utcnow().isoformat()
            if jsonl_path is not None:
                _update_jsonl_with_selection(jsonl_path, out)
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    records = [json.loads(line) for line in f]
                df_new = pd.DataFrame(records)
                if df_new is not None and not df_new.empty and "index" in df_new.columns:
                    df_new = df_new.drop(columns=["index"])
                if df_new is not None and not df_new.empty:
                    df_new = add_domain_defaults(df_new)
                df_new, ubp_db_path = run_ubp_calculation(str(jsonl_path), df_new)
                if df_new is None:
                    st.error("UBP-Berechnung lieferte keine Daten.")
                    st.stop()
                else:
                    st.session_state["data"] = df_new
                    st.session_state["ai_mapping_data_version"] = st.session_state.get("ai_mapping_data_version", 0) + 1
                    if ubp_db_path:
                        st.session_state["ubp_db_path"] = ubp_db_path
                    st.success("Auswahl gespeichert und in JSONL übernommen")
            else:
                st.error("Kein JSONL-Pfad gefunden. Auswahl konnte nicht gespeichert werden.")

    if jsonl_path is not None:
        sel_df = _load_selection_jsonl(jsonl_path)
        if "MaterialLayerIndex" in base.columns and "MaterialLayerIndex" in sel_df.columns:
            merge_cols = [c for c in ["GUID", "MaterialLayerIndex", "Material KBOB", "AI Score"] if c in sel_df.columns]
            merged = base.merge(sel_df[merge_cols], on=["GUID", "MaterialLayerIndex"], how="left")
        else:
            merge_cols = [c for c in ["GUID", "Material KBOB", "AI Score"] if c in sel_df.columns]
            merged = base.merge(sel_df[merge_cols], on="GUID", how="left")
        st.subheader("Übersicht")
        uebersicht = merged.rename(columns={"Description": "Beschrieb"})
        df_display = uebersicht[["IfcEntity", "PredefinedType", "Name", "Beschrieb", "Durchmesser", "Material KBOB", "AI Score"]].copy()
        if "AI Score" in df_display.columns:
            df_display["AI Score"] = df_display["AI Score"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "")
        st.dataframe(df_display, hide_index=True, width="stretch")
    else:
        st.info("Keine JSONL-Datei geladen. Keine Übersicht möglich.")
