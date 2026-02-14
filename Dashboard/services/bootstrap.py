import os

import streamlit as st

from Dashboard.services.ifc_pipeline import preload_sbert_resources
from Dashboard.services.viewer import ensure_ifclite_viewer


def initialize_app_runtime() -> None:
    if "sbert_preloaded" not in st.session_state:
        with st.spinner("AI-Modell wird geladen..."):
            preload_sbert_resources()
        st.session_state["sbert_preloaded"] = True

    if "viewer_server_started" not in st.session_state:
        viewer_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ifc-viewer", "ifc-lite")
        ensure_ifclite_viewer(viewer_root, port=3000)
        st.session_state["viewer_server_started"] = True
