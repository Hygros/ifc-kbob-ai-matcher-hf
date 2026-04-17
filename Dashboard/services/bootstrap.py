import os
import secrets

import streamlit as st

from Dashboard.config import DEFAULT_SBERT_MODEL
from Dashboard.config import USE_COMPONENT_VIEWER
from Dashboard.services.ifc_pipeline import preload_sbert_resources
from Dashboard.services.viewer import ensure_ifclite_viewer
from Dashboard.services.session_cleanup import start_cleanup_thread


def _ensure_session_id() -> str:
    """Return or create a cryptographically strong per-session identifier.

    The token is stored in ``st.session_state`` which Streamlit scopes
    to an individual WebSocket connection.  Each browser tab that opens
    the app gets its own connection and therefore its own token.  Note
    that if two tabs share a Streamlit session cookie they may share
    state; this is a Streamlit framework behaviour and the session
    directories already use random tokens, so file paths remain
    unpredictable regardless.

    The token is used to derive session-specific file-system paths for
    uploaded IFC and generated JSONL files so that different sessions
    cannot see each other's data.
    """
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = secrets.token_hex(16)
    return st.session_state["session_id"]


def initialize_app_runtime() -> None:
    # --- Session isolation token ---
    _ensure_session_id()

    if "selected_sbert_model" not in st.session_state:
        st.session_state["selected_sbert_model"] = DEFAULT_SBERT_MODEL
    elif st.session_state["selected_sbert_model"] is None:
        st.session_state["selected_sbert_model"] = DEFAULT_SBERT_MODEL

    if "sbert_preloaded" not in st.session_state:
        with st.spinner("AI-Modell wird geladen..."):
            preload_sbert_resources(st.session_state["selected_sbert_model"])
        st.session_state["sbert_preloaded"] = True
        st.session_state["preloaded_sbert_model"] = st.session_state["selected_sbert_model"]

    if "viewer_server_started" not in st.session_state:
        if not USE_COMPONENT_VIEWER:
            viewer_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ifc-lite")
            if not os.path.isdir(viewer_root):
                viewer_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ifc-viewer", "ifc-lite")
            ensure_ifclite_viewer(viewer_root, port=3000)
        st.session_state["viewer_server_started"] = True

    if "viewer_selected_guid" not in st.session_state:
        st.session_state["viewer_selected_guid"] = None

    if "viewer_selected_guids" not in st.session_state:
        st.session_state["viewer_selected_guids"] = []

    # --- TTL cleanup for expired session directories ---
    dashboard_dir = os.path.dirname(os.path.dirname(__file__))
    start_cleanup_thread(
        os.path.join(dashboard_dir, "static"),
        os.path.join(dashboard_dir, "data"),
    )
