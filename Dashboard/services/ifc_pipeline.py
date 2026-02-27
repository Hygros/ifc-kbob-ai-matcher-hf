import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

import pandas as pd
import streamlit as st


DASHBOARD_DIR = os.path.dirname(os.path.dirname(__file__))
APP_ROOT = os.path.dirname(DASHBOARD_DIR)
if APP_ROOT not in sys.path:
    sys.path.append(APP_ROOT)


@st.cache_resource(show_spinner=False)
def preload_sbert_resources(model_name: str) -> bool:
    """Load SBERT model + DB corpus embeddings once per Streamlit server process."""
    import SBERT.Sentence_Transformer_V00 as sbert_mod

    try:
        _ = sbert_mod.get_global_sbert_model(model_name=model_name)
        _ = sbert_mod.get_cached_corpus(model_name=model_name)
    except TypeError:
        if hasattr(sbert_mod, "MODEL_NAME"):
            sbert_mod.MODEL_NAME = model_name
        _ = sbert_mod.get_global_sbert_model()
        _ = sbert_mod.get_cached_corpus()
    return True


@st.cache_resource(show_spinner=False)
def preload_cross_encoder_resources(model_name: str) -> bool:
    """Load Cross-Encoder model once per Streamlit server process."""
    import SBERT.Sentence_Transformer_V00 as sbert_mod

    device = sbert_mod.resolve_runtime_device(0)
    sbert_mod.load_or_get_cross_encoder(model_name=model_name, device=device)
    return True


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
    static_dir = os.path.abspath(os.path.join(DASHBOARD_DIR, "static"))
    os.makedirs(static_dir, exist_ok=True)
    filename = getattr(uploaded_file, "name", None)
    if not filename:
        return None
    safe_filename = to_safe_filename(filename)
    save_path = os.path.join(static_dir, safe_filename)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return safe_filename


def parse_ifc(uploaded_file, model_name: str, cross_encoder_model_name: str | None = None):
    ifc_export_script = os.path.join(APP_ROOT, "IFC_Extraction", "IFC-extraction-main.py")
    python_exe = os.path.join(APP_ROOT, ".venv", "Scripts", "python.exe")
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        subprocess.run(
            [python_exe, ifc_export_script, tmp_path],
            capture_output=True,
            text=True,
            check=True,
        )
        base = os.path.splitext(os.path.basename(tmp_path))[0]
        jsonl_path = os.path.join(os.path.dirname(tmp_path), base + ".jsonl")
        timeout = 30
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

        dashboard_data_dir = os.path.join(DASHBOARD_DIR, "data")
        if not os.path.exists(dashboard_data_dir):
            os.makedirs(dashboard_data_dir)

        if hasattr(uploaded_file, "name"):
            ifc_base = os.path.splitext(os.path.basename(uploaded_file.name))[0]
        else:
            ifc_base = base

        target_jsonl_path = os.path.join(dashboard_data_dir, ifc_base + ".jsonl")
        if os.path.exists(jsonl_path):
            import SBERT.Sentence_Transformer_V00 as sbert_mod

            try:
                sbert_mod.run_sbert_matching(
                    jsonl_path,
                    model_name=model_name,
                    cross_encoder_model_name=cross_encoder_model_name,
                )
            except TypeError:
                if hasattr(sbert_mod, "MODEL_NAME"):
                    sbert_mod.MODEL_NAME = model_name
                sbert_mod.run_sbert_matching(jsonl_path)
            shutil.copy(jsonl_path, target_jsonl_path)
            with open(target_jsonl_path, "r", encoding="utf-8") as f:
                records = [json.loads(line) for line in f]
            df = pd.DataFrame(records)
            if "index" in df.columns:
                df = df.drop(columns=["index"])
            os.remove(tmp_path)
            os.remove(jsonl_path)
            return df, target_jsonl_path

        st.error("JSONL-Export nicht gefunden. Pipeline-Ausführung fehlgeschlagen.")
        return None, None
    except Exception as e:
        st.error(f"Pipeline-Ausführung fehlgeschlagen: {e}.")
        return None, None


def load_data(upload, model_name: str, cross_encoder_model_name: str | None = None):
    if upload is None:
        return None, None
    return parse_ifc(upload, model_name=model_name, cross_encoder_model_name=cross_encoder_model_name)


def get_upload_key(upload) -> tuple | None:
    if upload is None:
        return None
    name = getattr(upload, "name", None)
    size = getattr(upload, "size", None)
    file_id = getattr(upload, "file_id", None)
    upload_id = getattr(upload, "id", None)
    return (name, size, file_id, upload_id)
