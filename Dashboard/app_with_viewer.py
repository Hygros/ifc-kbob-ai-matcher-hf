import sys
import os

# python -m streamlit run Dashboard/app_with_viewer.py --server.port 8501

if __name__ == "__main__" and not os.environ.get("_ST_LAUNCHED"):
    import subprocess
    env = {**os.environ, "_ST_LAUNCHED": "1"}
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__, "--server.port", "8501"], env=env)
    sys.exit(0)

import streamlit as st
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.append(str(APP_ROOT))

from Dashboard.services.bootstrap import initialize_app_runtime  # noqa: E402
from Dashboard.ui.header import render_header_metrics  # noqa: E402
from Dashboard.ui.tab_ai_mapping import render_tab_ai_mapping  # noqa: E402
from Dashboard.ui.tab_charts import render_tab_charts  # noqa: E402
from Dashboard.ui.tab_uploads import render_tab_uploads  # noqa: E402

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
