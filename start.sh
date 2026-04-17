#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hugging Face Spaces startup script
# Single entrypoint: Streamlit only on the public HF port.
# ---------------------------------------------------------------------------
set -e

# _ST_LAUNCHED prevents the self-launch guard inside app_with_viewer.py
# from spawning another Streamlit subprocess.
export _ST_LAUNCHED=1

# Launch Streamlit (blocking – keeps the container alive)
exec python -m streamlit run Dashboard/app_with_viewer.py \
    --server.port=7860 \
    --server.address=0.0.0.0
