import streamlit as st
import sys

# python -m streamlit run Dashboard/app_with_viewer.py

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.append(str(APP_ROOT))

from Dashboard.services.bootstrap import initialize_app_runtime
from Dashboard.ui.header import render_header_metrics
from Dashboard.ui.tab_ai_mapping import render_tab_ai_mapping
from Dashboard.ui.tab_charts import render_tab_charts
from Dashboard.ui.tab_uploads import render_tab_uploads

# ---------- App ----------
st.set_page_config(page_title="IFC-basierte Ökobilanzierung", layout="wide")

initialize_app_runtime()

st.title("IFC-material mapping with AI")
render_header_metrics(st.session_state.get("data"))

# Tabs


tab_uploads, tab_ai_mapping, tab_charts = st.tabs(["Uploads", "AI-Mapping", "Charts"])

with tab_uploads:
    render_tab_uploads()

with tab_ai_mapping:
    render_tab_ai_mapping(st.session_state.get("data"))

with tab_charts:
    render_tab_charts(st.session_state.get("data"))
