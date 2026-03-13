#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hugging Face Spaces startup script
# Launches nginx (reverse proxy) and Streamlit side-by-side.
# The ifc-lite viewer server and the IFC static-file server are started
# automatically by the Streamlit application (bootstrap.py).
# ---------------------------------------------------------------------------
set -e

# Start nginx in the background
nginx &

# _ST_LAUNCHED prevents the self-launch guard inside app_with_viewer.py
# from spawning another Streamlit subprocess.
export _ST_LAUNCHED=1

# Launch Streamlit (blocking – keeps the container alive)
exec python -m streamlit run Dashboard/app_with_viewer.py \
    --server.port=8501 \
    --server.address=127.0.0.1
