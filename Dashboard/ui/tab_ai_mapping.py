import json
import os
import re
from pathlib import Path
from urllib.parse import quote, urlencode

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from Dashboard.config import DEFAULT_REINFORCEMENT_RATIO, REINFORCEMENT_KBOB_MATERIAL
from Dashboard.domain.mapping import (
    add_domain_defaults,
    add_reinforcement_info,
    build_ai_mapping_groups,
    is_concrete_material,
)
from Dashboard.services.kbob_materials import load_all_kbob_materials
from Dashboard.services.training_export import export_training_pairs, record_to_query
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
                    # Reinforcement fields
                    "reinforcement_accepted": rec.get("reinforcement_accepted"),
                    "reinforcement_ratio_kg_m3": rec.get("reinforcement_ratio_kg_m3"),
                    "reinforcement_source": rec.get("reinforcement_source"),
                }
            )
        return pd.DataFrame(selection_rows)
    return pd.DataFrame(columns=[
        "GUID", "MaterialLayerIndex", "Material KBOB", "AI Score", "SelectedOn",
        "reinforcement_accepted", "reinforcement_ratio_kg_m3", "reinforcement_source",
    ])


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
            sel_row = selection_lookup[key]
            rec["selected_kbob_material"] = sel_row.get("Material KBOB")
            rec["selected_ai_score"] = sel_row.get("AI Score")
            rec["selected_on"] = sel_row.get("SelectedOn")
            # Reinforcement decision fields
            rebar_accepted = sel_row.get("reinforcement_accepted")
            if rebar_accepted is not None and not (isinstance(rebar_accepted, float) and pd.isna(rebar_accepted)):
                rec["reinforcement_accepted"] = bool(rebar_accepted)
            rebar_ratio = sel_row.get("reinforcement_ratio_kg_m3")
            if rebar_ratio is not None and not (isinstance(rebar_ratio, float) and pd.isna(rebar_ratio)):
                rec["reinforcement_ratio_kg_m3"] = float(rebar_ratio)
            rebar_source = sel_row.get("reinforcement_source")
            if rebar_source is not None and not (isinstance(rebar_source, float) and pd.isna(rebar_source)):
                rec["reinforcement_source"] = str(rebar_source)
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


def _as_reinforcement_dict(sel_df: pd.DataFrame) -> dict:
    """Build lookup  selection-key -> {accepted, ratio, source}  from persisted JSONL."""
    lookup: dict[tuple, dict] = {}
    for _, row in sel_df.iterrows():
        key = _selection_key(row.get("GUID"), row.get("MaterialLayerIndex"))
        if key is None:
            continue
        accepted = row.get("reinforcement_accepted")
        ratio = row.get("reinforcement_ratio_kg_m3")
        source = row.get("reinforcement_source")
        if accepted is not None and not (isinstance(accepted, float) and pd.isna(accepted)):
            lookup[key] = {
                "accepted": bool(accepted),
                "ratio": float(ratio) if ratio is not None and not (isinstance(ratio, float) and pd.isna(ratio)) else None,
                "source": str(source) if source is not None and not (isinstance(source, float) and pd.isna(source)) else None,
            }
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
        base_cols = ["IfcEntity", "PredefinedType", "Name", "GUID", "MaterialLayerIndex", "Description", "Material", "Durchmesser", "top_k_matches", "AggregateChildGUIDs"]
        if df is not None and hasattr(df, "columns"):
            for col in base_cols:
                if col not in df.columns:
                    df[col] = None
            base = df[base_cols].copy()
            # Exclude synthetic reinforcement rows – they are only for charts/totals
            if "MaterialLayerIndex" in base.columns:
                base = base[base["MaterialLayerIndex"].astype(str) != "R"].reset_index(drop=True)
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
            prev_rebar = _as_reinforcement_dict(sel_df)
        else:
            sel_df = pd.DataFrame(columns=[
                "GUID", "MaterialLayerIndex", "Material KBOB", "AI Score", "SelectedOn",
                "reinforcement_accepted", "reinforcement_ratio_kg_m3", "reinforcement_source",
            ])
            prev_sel = {}
            prev_rebar = {}

        # Compute reinforcement info on the full DataFrame for status detection
        rebar_df = add_reinforcement_info(add_domain_defaults(df)) if df is not None else pd.DataFrame()

        grouped_base = build_ai_mapping_groups(base)

        all_kbob_materials, kbob_db_path, kbob_load_error = load_all_kbob_materials()
        if kbob_db_path:
            st.session_state["kbob_db_path"] = kbob_db_path
        if kbob_load_error:
            st.warning(f"KBOB-Vollauswahl nicht verfügbar ({kbob_load_error}). Es werden nur Top-Treffer angezeigt.")

        st.session_state["_manual_training_pairs"] = []
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
            for key in ["IfcEntity", "PredefinedType", "Name", "Description", "Material", "CastingMethod", "StrengthClass"]:
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
            aggregate_child_guids = group.get("aggregate_child_guids", [])
            all_viewer_guids = guids + [g for g in aggregate_child_guids if isinstance(g, str) and g not in guids]
            is_active = bool(active_guid) and active_guid in all_viewer_guids
            active_style = "background-color: #fff3cd; padding: 0.15rem 0.35rem; border-radius: 4px;" if is_active else ""
            guid_attr = ",".join(str(guid).replace("'", "") for guid in all_viewer_guids)
            st.markdown(
                f"<div class='ai-map-group-label' data-guids='{guid_attr}' style='font-size: 1.1em; font-weight: bold; margin-bottom: 0.2em; text-align: left; width: 100%; {active_style}'>{element_label}</div>",
                unsafe_allow_html=True,
            )

            matches = group["matches"]
            scored_labels = []
            material_lookup = {}
            scored_materials = []
            for match in matches:
                material_name = match.get("material")
                if not material_name:
                    continue
                material_name = str(material_name).strip()
                if not material_name or material_name in scored_materials:
                    continue
                score_value = match.get("score")
                label = f"{material_name} (Score: {score_value:.3f})" if score_value is not None else material_name
                scored_labels.append(label)
                material_lookup[label] = material_name
                scored_materials.append(material_name)

            scored_material_set = set(scored_materials)
            remaining_material_labels = []
            if all_kbob_materials:
                for material_name in all_kbob_materials:
                    if material_name in scored_material_set:
                        continue
                    remaining_material_labels.append(material_name)
                    material_lookup[material_name] = material_name

            options = [NO_SELECTION_LABEL] + scored_labels + remaining_material_labels
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
                args=(primary_guid, all_viewer_guids),
                label_visibility="collapsed",
            )

            sel_material = None if sel_label == NO_SELECTION_LABEL else material_lookup.get(sel_label)

            # Track manually changed selections for training export
            if sel_material is not None and sel_material != default_material:
                query_str = record_to_query(row_data)
                if query_str:
                    if "_manual_training_pairs" not in st.session_state:
                        st.session_state["_manual_training_pairs"] = []
                    st.session_state["_manual_training_pairs"].append((query_str, sel_material))

            # --- Reinforcement UI per group ---
            rebar_accepted = False
            rebar_ratio_value = None
            rebar_source = None
            ifc_entity = str(row_data.get("IfcEntity") or "").strip()

            # Determine reinforcement status from the enriched df
            # Use the first GUID of the group to look up status
            group_rebar_rows = rebar_df[rebar_df["GUID"].isin(guids)] if not rebar_df.empty else pd.DataFrame()
            if not group_rebar_rows.empty:
                first_status = group_rebar_rows.iloc[0].get("reinforcement_status", "none")
                first_ratio_source = group_rebar_rows.iloc[0].get("reinforcement_ratio_source")
                first_ratio = group_rebar_rows.iloc[0].get("reinforcement_ratio_kg_m3")
                first_mass = group_rebar_rows.iloc[0].get("reinforcement_mass_kg")
            else:
                first_status = "none"
                first_ratio_source = None
                first_ratio = None
                first_mass = None

            # Check previously persisted reinforcement decision
            prev_rebar_key = _selection_key(primary_guid, layer_index)
            prev_rebar_data = prev_rebar.get(prev_rebar_key, {})

            if first_status == "explicit":
                st.caption("✅ Bewehrung ist modelliert (IfcReinforcingBar vorhanden)")
            elif first_status == "assumed":
                source_label = "IFC-Wert" if first_ratio_source == "ifc" else "Standardwert"
                default_ratio = float(first_ratio) if first_ratio is not None and not pd.isna(first_ratio) else DEFAULT_REINFORCEMENT_RATIO.get(ifc_entity, DEFAULT_REINFORCEMENT_RATIO["_default"])
                mass_display = f"{first_mass:.1f}" if first_mass is not None and not pd.isna(first_mass) else "?"

                # Restore persisted state or default to True
                prev_accepted = prev_rebar_data.get("accepted", True)
                prev_ratio = prev_rebar_data.get("ratio")
                if prev_ratio is not None:
                    default_ratio = prev_ratio

                st.info(
                    f"⚠️ Keine Bewehrung modelliert. Kontrolliere die Annahme des Bewehrungsgehalts:"
                )
                cb_col, ni_col = st.columns([1, 2])
                with cb_col:
                    rebar_accepted = st.checkbox(
                        "Bewehrung annehmen",
                        value=prev_accepted,
                        key=f"rebar_cb_{data_version}_{group_index}_{primary_guid}",
                    )
                with ni_col:
                    rebar_ratio_value = st.number_input(
                        "Bewehrungsgehalt (kg/m³)",
                        min_value=0.0,
                        max_value=500.0,
                        value=default_ratio,
                        step=10.0,
                        key=f"rebar_ratio_{data_version}_{group_index}_{primary_guid}",
                        disabled=not rebar_accepted,
                    )
                if rebar_accepted:
                    rebar_source = "user" if rebar_ratio_value != first_ratio else (first_ratio_source or "default")
            elif first_status == "no_material":
                st.warning("Kein Material zugewiesen.")
                treat_as_concrete = st.checkbox(
                    "Als Beton behandeln",
                    value=prev_rebar_data.get("accepted", False),
                    key=f"rebar_concrete_cb_{data_version}_{group_index}_{primary_guid}",
                )
                if treat_as_concrete:
                    default_ratio_nm = prev_rebar_data.get("ratio") or DEFAULT_REINFORCEMENT_RATIO.get(ifc_entity, DEFAULT_REINFORCEMENT_RATIO["_default"])
                    rebar_ratio_value = st.number_input(
                        "Bewehrungsgehalt (kg/m³)",
                        min_value=0.0,
                        max_value=500.0,
                        value=float(default_ratio_nm),
                        step=10.0,
                        key=f"rebar_ratio_nm_{data_version}_{group_index}_{primary_guid}",
                    )
                    rebar_accepted = True
                    rebar_source = "user"

            guid_layer_map = group.get("guid_layer_map", {})
            for guid in guids:
                update_entry = {
                    "GUID": guid,
                    "MaterialLayerIndex": guid_layer_map.get(guid, layer_index),
                    "Material KBOB": sel_material,
                    "AI Score": scores.get(sel_material) if sel_material else None,
                }
                if rebar_accepted:
                    update_entry["reinforcement_accepted"] = True
                    update_entry["reinforcement_ratio_kg_m3"] = rebar_ratio_value
                    update_entry["reinforcement_source"] = rebar_source
                else:
                    update_entry["reinforcement_accepted"] = False
                    update_entry["reinforcement_ratio_kg_m3"] = None
                    update_entry["reinforcement_source"] = None
                updates.append(update_entry)

    with right_col:
        submitted = st.button("💾 Auswahl speichern", use_container_width=True)
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
                    df_new = add_reinforcement_info(df_new)
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
                    # --- Export training pairs for fine-tuning ---
                    manual_pairs = st.session_state.get("_manual_training_pairs", [])
                    if manual_pairs:
                        try:
                            training_dir = Path(__file__).resolve().parent.parent.parent / "Training" / "data"
                            total, added = export_training_pairs(manual_pairs, training_dir)
                            if added:
                                st.info(f"Trainingsdaten: {added} neue Paare exportiert ({total} gesamt)")
                            else:
                                st.info(f"Trainingsdaten: keine neuen Paare ({total} gesamt)")
                        except Exception as exc:
                            st.warning(f"Trainingsexport fehlgeschlagen: {exc}")
            else:
                st.error("Kein JSONL-Pfad gefunden. Auswahl konnte nicht gespeichert werden.")

    if jsonl_path is not None:
        sel_df = _load_selection_jsonl(jsonl_path)
        if "MaterialLayerIndex" in base.columns and "MaterialLayerIndex" in sel_df.columns:
            # Normalize MaterialLayerIndex consistently (e.g. '1.0' -> '1', NaN -> 'None')
            from Dashboard.services.ubp import _normalize_layer_index_col
            base["MaterialLayerIndex"] = _normalize_layer_index_col(base["MaterialLayerIndex"])
            sel_df["MaterialLayerIndex"] = _normalize_layer_index_col(sel_df["MaterialLayerIndex"])
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
