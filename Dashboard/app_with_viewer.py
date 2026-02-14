import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
import subprocess
import os
import json
import sys
import socket
import shutil
import re
import unicodedata
from urllib.parse import quote
import streamlit.components.v1 as components

# python -m streamlit run Dashboard/app_with_viewer.py

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
if APP_ROOT not in sys.path:
    sys.path.append(APP_ROOT)

from calculate_ubp21_per_element import calculate_ubp_for_jsonl


@st.cache_resource(show_spinner=False)
def _preload_sbert_resources() -> bool:
    """Load SBERT model + DB corpus embeddings once per Streamlit server process."""
    from SBERT.Sentence_Transformer_V00 import get_cached_corpus, get_global_sbert_model

    _ = get_global_sbert_model()
    _ = get_cached_corpus()
    return True

# ---------- Hilfsfunktionen ----------
def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def ensure_static_server(static_dir: str, port: int = 8080) -> None:
    if _is_port_in_use(port):
        return
    cors_script = os.path.join(os.path.dirname(__file__), "serve_static_with_cors.py")
    subprocess.Popen(
        [sys.executable, cors_script, static_dir, str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_ifclite_viewer(viewer_root: str, port: int = 3000) -> None:
    if _is_port_in_use(port):
        return
    if not os.path.isdir(viewer_root):
        return
    pnpm_cmd = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    if not pnpm_cmd:
        return
    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [pnpm_cmd, "--filter", "viewer", "dev"],
        cwd=viewer_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )


def to_safe_filename(name: str) -> str:
    base, ext = os.path.splitext(name)
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
    for src, dst in replacements.items():
        base = base.replace(src, dst)
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._-")
    if not base:
        base = "ifc_model"
    return f"{base}{ext}"


def resolve_ifc_for_jsonl(static_dir: str, jsonl_name: str) -> str | None:
    base_name = os.path.splitext(jsonl_name)[0]
    ifc_name = base_name + ".ifc"
    ifc_candidate = os.path.join(static_dir, ifc_name)
    safe_ifc_name = to_safe_filename(ifc_name)
    safe_candidate = os.path.join(static_dir, safe_ifc_name)
    if os.path.exists(ifc_candidate):
        if ifc_candidate != safe_candidate and not os.path.exists(safe_candidate):
            shutil.copy(ifc_candidate, safe_candidate)
            return os.path.basename(safe_candidate)
        return os.path.basename(ifc_candidate)
    if os.path.exists(safe_candidate):
        return os.path.basename(safe_candidate)
    safe_target = to_safe_filename(ifc_name)
    for entry in os.listdir(static_dir):
        if not entry.lower().endswith(".ifc"):
            continue
        if to_safe_filename(entry).lower() == safe_target.lower():
            src = os.path.join(static_dir, entry)
            if src != safe_candidate and not os.path.exists(safe_candidate):
                shutil.copy(src, safe_candidate)
                return os.path.basename(safe_candidate)
            return os.path.basename(entry)
    return None


def save_ifc_for_viewer(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
    os.makedirs(static_dir, exist_ok=True)
    filename = getattr(uploaded_file, "name", None)
    if not filename:
        return None
    safe_filename = to_safe_filename(filename)
    save_path = os.path.join(static_dir, safe_filename)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return safe_filename


def render_viewer_bridge(selected_guid: str | None, selected_guids: list[str] | None = None) -> str | None:
    if not isinstance(selected_guid, str):
        selected_guid = None
    if not isinstance(selected_guids, list):
        selected_guids = []
    selected_guids = [guid for guid in selected_guids if isinstance(guid, str) and guid.strip()]
    payload = json.dumps({"guid": selected_guid, "guids": selected_guids})
    bridge_html = f"""
<script>
(() => {{
    const selected = {payload};
    const getViewerFrame = () => window.parent.document.querySelector('iframe.viewer-iframe');

    const sendToViewer = () => {{
        const frame = getViewerFrame();
        if (frame && frame.contentWindow) {{
            if (Array.isArray(selected.guids) && selected.guids.length > 1) {{
                frame.contentWindow.postMessage({{ type: 'ifc-lite-select-guids', guids: selected.guids }}, '*');
            }} else {{
                frame.contentWindow.postMessage({{ type: 'ifc-lite-select-guid', guid: selected.guid || null }}, '*');
            }}
        }}
    }};

    try {{
        sendToViewer();
    }} catch (err) {{
        console.warn('Viewer bridge failed to post selection', err);
    }}
}})();
</script>
"""
    components.html(bridge_html, height=0, width=0)
    return None


def set_active_guid(guid: str | None, guids: list[str] | None = None) -> None:
    st.session_state["viewer_selected_guid"] = guid if isinstance(guid, str) else None
    if isinstance(guids, list):
        st.session_state["viewer_selected_guids"] = [entry for entry in guids if isinstance(entry, str) and entry.strip()]
    elif isinstance(guid, str):
        st.session_state["viewer_selected_guids"] = [guid]
    else:
        st.session_state["viewer_selected_guids"] = []

def parse_ifc(uploaded_file):
    # Run IFC export as a subprocess, but execute SBERT matching in-process to avoid
    # reloading the SBERT model on every run during Streamlit development.
    ifc_export_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "IFC_Extraction", "IFC-extraction-main.py")
    python_exe = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".venv", "Scripts", "python.exe")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    import time
    try:
        result = subprocess.run(
            [python_exe, ifc_export_script, tmp_path],
            capture_output=True,
            text=True,
            check=True,
        )
        base = os.path.splitext(os.path.basename(tmp_path))[0]
        jsonl_path = os.path.join(os.path.dirname(tmp_path), base + ".jsonl")
        # Warte, bis die jsonl-Datei existiert und nicht mehr wächst
        timeout = 30  # Sekunden
        poll_interval = 0.2
        waited = 0
        last_size = -1
        stable_count = 0
        while waited < timeout:
            if os.path.exists(jsonl_path):
                size = os.path.getsize(jsonl_path)
                if size == last_size and size > 0:
                    stable_count += 1
                    if stable_count >= 3:
                        break
                else:
                    stable_count = 0
                last_size = size
            time.sleep(poll_interval)
            waited += poll_interval
        # Zielpfad im Dashboard/data/-Ordner
        dashboard_data_dir = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(dashboard_data_dir):
            os.makedirs(dashboard_data_dir)
        # Name der hochgeladenen IFC-Datei (ohne Endung)
        if hasattr(uploaded_file, 'name'):
            ifc_base = os.path.splitext(os.path.basename(uploaded_file.name))[0]
        else:
            ifc_base = base
        target_jsonl_path = os.path.join(dashboard_data_dir, ifc_base + ".jsonl")
        if os.path.exists(jsonl_path):
            # SBERT matching (in-process, model stays cached across Streamlit reruns)
            from SBERT.Sentence_Transformer_V00 import run_sbert_matching
            run_sbert_matching(jsonl_path)

            import shutil
            shutil.copy(jsonl_path, target_jsonl_path)
            with open(target_jsonl_path, "r", encoding="utf-8") as f:
                records = [json.loads(line) for line in f]
            df = pd.DataFrame(records)
            if 'index' in df.columns:
                df = df.drop(columns=['index'])
            # Optional: temporäre Dateien löschen
            os.remove(tmp_path)
            os.remove(jsonl_path)
            return df, target_jsonl_path
        else:
            st.error("JSONL-Export nicht gefunden. Pipeline-Ausführung fehlgeschlagen.")
            return None, None
    except Exception as e:
        st.error(f"Pipeline-Ausführung fehlgeschlagen: {e}.")
        return None, None

# Hilfsfunktion zum Laden der Daten (nur IFC)
def load_data(upload):
    if upload is None:
        return None, None
    return parse_ifc(upload)

def get_upload_key(upload) -> tuple | None:
    if upload is None:
        return None
    name = getattr(upload, "name", None)
    size = getattr(upload, "size", None)
    return (name, size)

def add_domain_defaults(df: pd.DataFrame) -> pd.DataFrame:
    # Platzhalter: Dichten, KBOB-Zuordnung, Indikatoren
    df = df.copy()
    # Mapping für externe JSONL-Felder
    colmap = {
        "ifc_entity": "IfcEntity",
        "element_name": "Name",
        "ifc_material": "Material",
        "volume_m3": "NetVolume",
    }
    df = df.copy()
    # Füge ggf. die "alten" Spaltennamen als Alias für die neuen hinzu
    for old, new in colmap.items():
        if old not in df.columns and new in df.columns:
            df[old] = df[new]
    # Sicherstellen, dass alle benötigten Spalten existieren
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
    # Masse berechnen
    df["mass_kg"] = df["volume_m3"] * df["density_kg_m3"]
    # Indikatoren falls leer
    for col in ["gwp_kgco2eq", "ubp", "penre_kwh_oil_eq"]:
        if col not in df:
            df[col] = 0.0
        df[col] = df[col].fillna(0.0)
    return df


def apply_ubp_results(df: pd.DataFrame, results: list) -> pd.DataFrame:
    if not results:
        return df
    results_df = pd.DataFrame(results)
    col_map = {
        "UBP21Total": "ubp",
        "TreibhausgasemissionenTotalkgCO2-eq": "gwp_kgco2eq",
        "PrimärenergiegesamtTotalkWhoil-eq": "penre_kwh_oil_eq",
    }
    for src, dst in col_map.items():
        if src in results_df.columns:
            results_df[dst] = results_df[src]
    keep_cols = ["GUID"] + [dst for dst in col_map.values() if dst in results_df.columns]
    results_df = results_df[keep_cols].copy()
    merged = df.merge(results_df, on="GUID", how="left", suffixes=("", "_calc"))
    for dst in col_map.values():
        calc_col = f"{dst}_calc"
        if calc_col in merged.columns:
            merged[dst] = merged[calc_col].fillna(merged[dst])
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

def kpi_block(df: pd.DataFrame):
    total_gwp = df["gwp_kgco2eq"].sum()
    total_ubp = df["ubp"].sum()
    total_penre = df["penre_kwh_oil_eq"].sum()
    c1, c2, c3 = st.columns(3)
    def chf_thousands(x):
        # Format with apostrophe as thousands separator, no decimals
        return f"{int(round(x)):,}".replace(",", "'")
    c1.metric("Global Warming Potential", f"{chf_thousands(total_gwp)} kg CO₂ eq")
    c2.metric("Environmental Impact Points", f"{chf_thousands(total_ubp)} UBP")
    c3.metric("Primary Energy Non-Renewable", f"{chf_thousands(total_penre)} kWh oil‑eq")

def group_and_aggregate(df: pd.DataFrame, group_mode: str, indicator: str) -> pd.DataFrame:
    group_cols = {
        "Group by Elements": ["element_name"],
        "Group by KBOB Materials": ["kbob_material"],
        "Group by Ifc Materials": ["ifc_material"],
        "Group by Ifc Entity": ["ifc_entity"],
    }[group_mode]
    agg = (
        df.groupby(group_cols, dropna=False)[indicator]
        .sum()
        .reset_index()
        .rename(columns={indicator: "value"})
    )
    return agg


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
    fields = ["IfcEntity", "PredefinedType", "Name", "Description", "Material", "Durchmesser"]
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

# ---------- App ----------
st.set_page_config(page_title="IFC-basierte Ökobilanzierung", layout="wide")

# Preload AI model so the first IFC upload is faster.
if "sbert_preloaded" not in st.session_state:
    with st.spinner("AI-Modell wird geladen..."):
        _preload_sbert_resources()
    st.session_state["sbert_preloaded"] = True

st.title("IFC-material mapping with AI")

if "viewer_server_started" not in st.session_state:
    viewer_root = os.path.join(os.path.dirname(__file__), "ifc-viewer", "ifc-lite")
    ensure_ifclite_viewer(viewer_root, port=3000)
    st.session_state["viewer_server_started"] = True

# Header-Kacheln
mid, right = st.columns([1, 1])
with mid:
    c1, c2, c3 = st.columns(3)
    df = st.session_state.get("data")
    # Elements: Anzahl Zeilen
    if df is not None:
        num_elements = len(df)
        # Materials: Anzahl unterschiedlicher "Material Ifc"
        mat_col = "Material Ifc"
        if mat_col in df.columns:
            num_materials = df[mat_col].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x)).nunique()
        elif "Material" in df.columns:
            num_materials = df["Material"].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x)).nunique()
        else:
            num_materials = "–"
    else:
        num_elements = "–"
        num_materials = "–"
    # Uploads: Anzahl IFC-Uploads (Dateien im data-Ordner mit .jsonl-Endung)
    dashboard_data_dir = os.path.join(os.path.dirname(__file__), "data")
    try:
        num_uploads = len([f for f in os.listdir(dashboard_data_dir) if f.endswith('.jsonl')])
    except Exception:
        num_uploads = "–"
    c1.metric("Elements", f"{num_elements}")
    c2.metric("Uploads", f"{num_uploads}")
    c3.metric("Materials", f"{num_materials}")
with right:
    pass

# Tabs


tab_uploads, tab_ai_mapping, tab_charts = st.tabs(["Uploads", "AI-Mapping", "Charts"])

with tab_uploads:
    upload = st.file_uploader("IFC-Datei hochladen", type=["ifc", "ifczip"])
    loaded_path = None
    jsonl_path = None
    upload_key = get_upload_key(upload)
    last_upload_key = st.session_state.get("last_upload_key")
    # Möglichkeit, bereits abgelegte JSONL-Dateien zu laden
    dashboard_data_dir = os.path.join(os.path.dirname(__file__), "data")
    try:
        jsonl_files = [f for f in os.listdir(dashboard_data_dir) if f.endswith('.jsonl')]
    except Exception:
        jsonl_files = []
    if jsonl_files:
        selected_jsonl = st.selectbox("Vorhandene JSONL-Datei laden", jsonl_files, index=0)
        if st.button("JSONL laden"):
            jsonl_path = os.path.join(dashboard_data_dir, selected_jsonl)
            with open(jsonl_path, "r", encoding="utf-8") as f:
                records = [json.loads(line) for line in f]
            df = pd.DataFrame(records)
            if 'index' in df.columns:
                df = df.drop(columns=['index'])
            df = add_domain_defaults(df)
            df, ubp_db_path = run_ubp_calculation(str(jsonl_path), df)
            st.session_state["data"] = df
            st.session_state["jsonl_path"] = str(jsonl_path)
            static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
            resolved_ifc = resolve_ifc_for_jsonl(static_dir, selected_jsonl)
            if resolved_ifc:
                st.session_state["ifc_filename"] = resolved_ifc
            if ubp_db_path:
                st.session_state["ubp_db_path"] = ubp_db_path
            msg = f"JSONL geladen: {jsonl_path}"
            st.session_state["_success_message"] = msg
            st.session_state["_just_loaded_jsonl"] = True
            st.rerun()
    if upload is not None and upload_key != last_upload_key:
        if hasattr(upload, 'name'):
            loaded_path = upload.name
        else:
            loaded_path = str(upload)
        ifc_filename = save_ifc_for_viewer(upload)
        with st.spinner("IFC-Datei wird verarbeitet und exportiert..."):
            df, jsonl_path = load_data(upload)
        if df is not None:
            if 'index' in df.columns:
                df = df.drop(columns=['index'])
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
        # Show success message after rerun
        msg = st.session_state.pop("_success_message", None)
        if msg:
            st.success(msg)
        st.session_state["_just_uploaded"] = False
    elif st.session_state.get("_just_loaded_jsonl"):
        # Show success message after rerun
        msg = st.session_state.pop("_success_message", None)
        if msg:
            st.success(msg)
        st.session_state["_just_loaded_jsonl"] = False

with tab_ai_mapping:
    df = st.session_state.get("data")
    if df is None:
        st.info("Noch keine Daten. Lade in Tab Uploads eine Datei.")
    else:
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
        static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
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

        left_col, right_col = st.columns([1.1, 1])

        with right_col:
            if ifc_filename:
                ifc_path = os.path.join(static_dir, ifc_filename)
            else:
                ifc_path = None
            if ifc_path and os.path.exists(ifc_path):
                ensure_static_server(static_dir, port=8080)
                file_url = f"http://127.0.0.1:8080/{quote(str(ifc_filename))}"
                viewer_url = f"http://localhost:3000/?file_url={file_url}"
                
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

        with left_col:
            active_guid = st.session_state.get("viewer_selected_guid") if isinstance(st.session_state.get("viewer_selected_guid"), str) else None
            # Prepare base columns and matches
            base_cols = ["IfcEntity","PredefinedType","Name","GUID","Description","Material","Durchmesser","top_k_matches"]
            # Defensive: check if df is not None and has columns
            if df is not None and hasattr(df, 'columns'):
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

            # JSONL selection logic only
            from pathlib import Path
            import datetime
            def get_jsonl_path():
                jsonl_path = st.session_state.get("jsonl_path")
                return Path(jsonl_path) if jsonl_path else None

            def load_selection_jsonl(jsonl_path: Path) -> pd.DataFrame:
                if jsonl_path and jsonl_path.exists():
                    with open(jsonl_path, "r", encoding="utf-8") as f:
                        records = [json.loads(line) for line in f]
                    sel = []
                    for rec in records:
                        sel.append({
                            "GUID": rec.get("GUID"),
                            "Material KBOB": rec.get("selected_kbob_material"),
                            "AI Score": rec.get("selected_ai_score"),
                            "SelectedOn": rec.get("selected_on"),
                        })
                    return pd.DataFrame(sel)
                return pd.DataFrame(columns=["GUID", "Material KBOB", "AI Score", "SelectedOn"])

            def update_jsonl_with_selection(jsonl_path: Path, selection_df: pd.DataFrame):
                if not jsonl_path.exists():
                    return
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    records = [json.loads(line) for line in f]
                sel_dict = {row["GUID"]: row for _, row in selection_df.iterrows() if pd.notna(row["GUID"])}
                for rec in records:
                    guid = rec.get("GUID")
                    if guid in sel_dict:
                        rec["selected_kbob_material"] = sel_dict[guid].get("Material KBOB")
                        rec["selected_ai_score"] = sel_dict[guid].get("AI Score")
                        rec["selected_on"] = sel_dict[guid].get("SelectedOn")
                with open(jsonl_path, "w", encoding="utf-8") as f:
                    for rec in records:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        
            def as_selection_dict(sel_df: pd.DataFrame) -> dict:
                material_col = "Material KBOB" if "Material KBOB" in sel_df.columns else (
                    "SelectedMaterial" if "SelectedMaterial" in sel_df.columns else None
                )
                if material_col is None:
                    return {}
                return {r["GUID"]: r[material_col] for _, r in sel_df.iterrows()}
                
            def get_score_lookup(matches: list) -> dict:
                return {m.get("material"): m.get("score") for m in matches or []}

            jsonl_path = get_jsonl_path()
            if jsonl_path is not None:
                sel_df = load_selection_jsonl(jsonl_path)
                prev_sel = as_selection_dict(sel_df)
            else:
                sel_df = pd.DataFrame(columns=["GUID", "Material KBOB", "AI Score", "SelectedOn"])
                prev_sel = {}

            grouped_base = build_ai_mapping_groups(base)

            updates = []
            for group_index, group in enumerate(grouped_base):
                r = group["row"]
                guids = [guid for guid in group["guids"] if isinstance(guid, str)]
                if not guids:
                    continue
                primary_guid = guids[0]
                def is_valid(val):
                    if val is None:
                        return False
                    sval = str(val).strip()
                    if not sval:
                        return False
                    normalized = re.sub(r"[\s_\-]+", "", sval).lower()
                    invalid_tokens = {
                        "nan",
                        "none",
                        "null",
                        "undefined",
                        "notdefined",
                        "n/a",
                        "na",
                        "-",
                    }
                    return normalized not in invalid_tokens

                def format_label_value(val):
                    if isinstance(val, list):
                        cleaned = [str(item).strip() for item in val if item is not None and str(item).strip()]
                        return ", ".join(cleaned)
                    return str(val).strip()

                label_parts = []
                for key in ["IfcEntity", "PredefinedType", "Name", "Description", "Material"]:
                    val = r.get(key)
                    formatted_val = format_label_value(val)
                    if is_valid(formatted_val):
                        label_parts.append(formatted_val)
                durchmesser = r.get("Durchmesser")
                if is_valid(durchmesser):
                    label_parts.append(f"Ø {durchmesser}")
                element_label = " | ".join(label_parts)
                if len(guids) > 1:
                    element_label = f"{element_label} <span style='color: #999;'>({len(guids)} Elemente)</span>"
                is_active = bool(active_guid) and active_guid in guids
                active_style = "background-color: #fff3cd; padding: 0.15rem 0.35rem; border-radius: 4px;" if is_active else ""
                st.markdown(
                    f"<div style='font-size: 1.1em; font-weight: bold; margin-bottom: 0.2em; text-align: left; width: 100%; {active_style}'>{element_label}</div>",
                    unsafe_allow_html=True
                )
                matches = group["matches"]
                options = [
                    f"{m.get('material')} (Score: {m.get('score'):.3f})" if m.get("score") is not None else m.get("material")
                    for m in matches
                ]
                material_lookup = {
                    f"{m.get('material')} (Score: {m.get('score'):.3f})" if m.get("score") is not None else m.get("material"): m.get("material")
                    for m in matches
                }
                scores = get_score_lookup(matches)
                existing_materials = {prev_sel.get(guid) for guid in guids if prev_sel.get(guid)}
                if len(existing_materials) == 1:
                    default_material = next(iter(existing_materials))
                else:
                    default_material = matches[0].get("material") if matches else None
                if matches:
                    default_label = next(
                        (label for label, mat in material_lookup.items() if mat == default_material),
                        options[0]
                    )
                else:
                    default_label = "kein Vorschlag"
                if options:
                    sel_label = st.selectbox(
                        "Materialauswahl",
                        options=options,
                        index=(options.index(default_label) if default_label in options else 0),
                        key=f"sel_group_{group_index}_{primary_guid}",
                        on_change=set_active_guid,
                        args=(primary_guid, guids),
                        label_visibility="collapsed"
                    )
                else:
                    sel_label = st.selectbox(
                        "Materialauswahl",
                        options=["kein Vorschlag"],
                        index=0,
                        key=f"sel_group_{group_index}_{primary_guid}",
                        on_change=set_active_guid,
                        args=(primary_guid, guids),
                        label_visibility="collapsed"
                    )
                sel_material = material_lookup.get(sel_label) if options else None
                for guid in guids:
                    updates.append({
                        "GUID": guid,
                        "Material KBOB": sel_material,
                        "AI Score": scores.get(sel_material) if options else None
                    })
            submitted = st.button("Auswahl speichern")
            if submitted:
                out = pd.DataFrame(updates)
                out["SelectedOn"] = pd.Timestamp.utcnow().isoformat()
                out = out.rename(columns={"Material KBOB": "Material KBOB", "AI Score": "AI Score"})
                if jsonl_path is not None:
                    update_jsonl_with_selection(jsonl_path, out)
                    with open(jsonl_path, "r", encoding="utf-8") as f:
                        records = [json.loads(line) for line in f]
                    df_new = pd.DataFrame(records)
                    if df_new is not None and not df_new.empty and 'index' in df_new.columns:
                        df_new = df_new.drop(columns=['index'])
                    if df_new is not None and not df_new.empty:
                        df_new = add_domain_defaults(df_new)
                    df_new, ubp_db_path = run_ubp_calculation(str(jsonl_path), df_new)
                    if df_new is None:
                        st.error("UBP-Berechnung lieferte keine Daten.")
                        st.stop()
                    else:
                        st.session_state["data"] = df_new
                        if ubp_db_path:
                            st.session_state["ubp_db_path"] = ubp_db_path
                        base_cols = ["IfcEntity","PredefinedType","Name","GUID","Description","Material","Durchmesser","top_k_matches"]
                        for col in base_cols:
                            if col not in df_new.columns:
                                df_new[col] = None
                        base = df_new[base_cols].copy()
                        base["Durchmesser"] = base["Durchmesser"].astype(str)
                        st.success("Auswahl gespeichert und in JSONL übernommen")
                else:
                    st.error("Kein JSONL-Pfad gefunden. Auswahl konnte nicht gespeichert werden.")

        # Übersicht
        if jsonl_path is not None:
            sel_df = load_selection_jsonl(jsonl_path)
            merge_cols = [c for c in ["GUID", "Material KBOB", "AI Score"] if c in sel_df.columns]
            merged = base.merge(sel_df[merge_cols], on="GUID", how="left")
            st.subheader("Übersicht")
            uebersicht = merged.rename(columns={"Description": "Beschrieb"})
            df_display = uebersicht[["IfcEntity", "PredefinedType", "Name", "Beschrieb", "Durchmesser", "Material KBOB", "AI Score"]].copy()
            if "AI Score" in df_display.columns:
                df_display["AI Score"] = df_display["AI Score"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "")
            st.dataframe(
                df_display,
                hide_index=True,
                width="stretch"
            )
        else:
            st.info("Keine JSONL-Datei geladen. Keine Übersicht möglich.")

with tab_charts:
    df = st.session_state.get("data")
    if df is None or not hasattr(df, 'columns'):
        st.info("Noch keine Daten.")
    else:
        st.subheader("Chart Configuration")

        # Auswahl
        # Liste dynamisch basierend auf Grouping
        grouping_mode = st.selectbox(
            "Grouping Mode",
            options=["Group by Elements", "Group by KBOB Materials", "Group by Ifc Materials", "Group by Ifc Entity"],
            index=3,
        )
        indicator_label_map = {
            "Global Warming Potential (kg CO₂ eq)": "gwp_kgco2eq",
            "Environmental Impact Points (UBP)": "ubp",
            "Primary Energy Non-Renewable (kWh oil‑eq)": "penre_kwh_oil_eq",
        }
        indicator_ui = st.selectbox("Environmental Indicator", list(indicator_label_map.keys()), index=1)
        indicator = indicator_label_map[indicator_ui]

        # Dynamische Auswahl abhängig vom Grouping
        if grouping_mode == "Group by Elements":
            col = "element_name" if "element_name" in df.columns else ("Name" if "Name" in df.columns else None)
            if col:
                universe = df[col].dropna().unique().tolist()
            else:
                universe = []
            label = "Select Elements"
        elif grouping_mode == "Group by KBOB Materials":
            col = "kbob_material" if "kbob_material" in df.columns else None
            if col:
                universe = df[col].dropna().unique().tolist()
            else:
                universe = []
            label = "Select KBOB materials"
        elif grouping_mode == "Group by Ifc Materials":
            col = "ifc_material" if "ifc_material" in df.columns else ("Material" if "Material" in df.columns else None)
            if col:
                universe = df[col].dropna().unique().tolist()
            else:
                universe = []
            label = "Select Ifc materials"
        else:
            col = "ifc_entity" if "ifc_entity" in df.columns else ("IfcEntity" if "IfcEntity" in df.columns else None)
            if col:
                universe = df[col].dropna().unique().tolist()
            else:
                universe = []
            label = "Select Ifc entities"

        selection = st.multiselect("Selection", options=universe, default=universe, placeholder=label)

        chart_type = st.segmented_control("Chart Type", options=["Bar", "Line", "Pie", "Bubble"], default="Bar")

        # Filter und Aggregation
        fdf = df.copy()
        if grouping_mode == "Group by Elements":
            fdf = fdf[fdf["element_name"].isin(selection)]
        elif grouping_mode == "Group by KBOB Materials":
            fdf = fdf[fdf["kbob_material"].isin(selection)]
        elif grouping_mode == "Group by Ifc Materials":
            fdf = fdf[fdf["ifc_material"].isin(selection)]
        else:
            fdf = fdf[fdf["ifc_entity"].isin(selection)]

        agg = group_and_aggregate(fdf, grouping_mode, indicator)

        # KPIs
        kpi_block(fdf)

        # Chart
        if chart_type == "Bar":
            fig = px.bar(agg, x=agg.columns[0], y="value", title="Environmental Impact Visualization")
        elif chart_type == "Line":
            fig = px.line(agg, x=agg.columns[0], y="value", markers=True, title="Environmental Impact Visualization")
        elif chart_type == "Pie":
            fig = px.pie(agg, names=agg.columns[0], values="value", title="Environmental Impact Visualization")
        else:
            # Bubble: x = Gruppenindex, y = value, size = value
            agg = agg.reset_index(drop=True)
            agg["x"] = agg.index
            fig = px.scatter(agg, x="x", y="value", size="value", hover_name=agg.columns[0], title="Environmental Impact Visualization")
        fig.update_layout(xaxis_title=None, yaxis_title=indicator_ui)
        st.plotly_chart(fig, width="stretch")

        # Export
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("Export CSV", data=agg.to_csv(index=False), file_name="chart_data.csv", mime="text/csv")
        with col2:
            st.download_button("Export IFC Mapping", data=fdf.to_csv(index=False), file_name="materials_table.csv", mime="text/csv")
