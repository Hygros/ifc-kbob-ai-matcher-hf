import json
import os
import socket
import subprocess
import shutil
import sys

import streamlit as st
import streamlit.components.v1 as components


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def ensure_static_server(static_dir: str, port: int = 8080) -> None:
    if _is_port_in_use(port):
        return
    cors_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "serve_static_with_cors.py")
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
