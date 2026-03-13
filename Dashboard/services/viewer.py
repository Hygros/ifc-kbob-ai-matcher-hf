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

    # If a pre-built dist/ exists (e.g. Docker / HF Spaces), serve it as
    # static files instead of starting a Vite dev server.
    dist_dir = os.path.join(viewer_root, "dist")
    if os.path.isdir(dist_dir):
        ensure_static_server(dist_dir, port)
        return

    npm_cmd = shutil.which("npm") or shutil.which("npm.cmd")
    pnpm_cmd = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    if not npm_cmd and not pnpm_cmd:
        return
    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

    if npm_cmd:
        command = [npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port), "--strictPort"]
    else:
        command = [pnpm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port), "--strictPort"]

    subprocess.Popen(
        command,
        cwd=viewer_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )


def render_viewer_bridge(
    selected_guid: str | None,
    selected_guids: list[str] | None = None,
    guid_map: dict[str, list[int]] | None = None,
) -> None:
    if not isinstance(selected_guid, str):
        selected_guid = None
    if not isinstance(selected_guids, list):
        selected_guids = []
    selected_guids = [guid for guid in selected_guids if isinstance(guid, str) and guid.strip()]
    payload = json.dumps({"guid": selected_guid, "guids": selected_guids})
    guid_map_json = json.dumps(guid_map or {})
    bridge_html = f"""
<script>
(() => {{
    const selected = {payload};
    const GUID_MAP = {guid_map_json};
    const parentWindow = window.parent;
    const _viewerFrame = parentWindow.document.querySelector('iframe.viewer-iframe');
    let VIEWER_ORIGIN = 'http://localhost:3000';
    if (_viewerFrame && _viewerFrame.src) {{
        try {{ VIEWER_ORIGIN = new URL(_viewerFrame.src).origin; }} catch(e) {{}}
    }}
    const getViewerFrame = () => parentWindow.document.querySelector('iframe.viewer-iframe');

    let _highlightedEls = [];
    const highlightGuid = (guid, shouldScroll = false) => {{
        _highlightedEls.forEach((el) => {{
            el.style.backgroundColor = '';
            el.style.padding = '';
            el.style.borderRadius = '';
        }});
        _highlightedEls = [];

        if (!guid) return;

        const groupIndices = GUID_MAP[guid];
        if (!groupIndices || !groupIndices.length) return;

        const labels = parentWindow.document.querySelectorAll('.ai-map-group-label');
        let firstEl = null;
        groupIndices.forEach((idx) => {{
            const el = labels[idx];
            if (el) {{
                el.style.backgroundColor = '#d9ffcd';
                el.style.padding = '0.15rem 0.35rem';
                el.style.borderRadius = '4px';
                _highlightedEls.push(el);
                if (!firstEl) firstEl = el;
            }}
        }});

        if (shouldScroll && firstEl) {{
            try {{
                firstEl.scrollIntoView({{ behavior: 'instant', block: 'center', inline: 'nearest' }});
            }} catch (err) {{
                firstEl.scrollIntoView();
            }}
        }}
    }};

    const postClearSelection = () => {{
        const frame = getViewerFrame();
        if (frame && frame.contentWindow) {{
            frame.contentWindow.postMessage({{ type: 'ifc-lite-select-guid', guid: null }}, VIEWER_ORIGIN);
            frame.contentWindow.postMessage({{ type: 'ifc-lite-select-guids', guids: [] }}, VIEWER_ORIGIN);
        }}
        highlightGuid(null);
    }};

    const isSelectInteraction = (target) => {{
        if (!target || !(target instanceof Element)) return false;
        return Boolean(
            target.closest('[data-testid="stSelectbox"]') ||
            target.closest('[data-baseweb="select"]') ||
            target.closest('[role="listbox"]') ||
            target.closest('[role="option"]') ||
            target.closest('[data-testid="stPopover"]')
        );
    }};

    const isViewerInteraction = (target) => {{
        if (!target || !(target instanceof Element)) return false;
        return Boolean(
            target.closest('.viewer-sticky') ||
            target.closest('iframe.viewer-iframe') ||
            target.closest('.viewer-iframe')
        );
    }};

    if (typeof parentWindow.__ifcLiteForceDeselect === 'undefined') {{
        parentWindow.__ifcLiteForceDeselect = false;
    }}
    if (typeof parentWindow.__ifcLiteLastSelectionSig === 'undefined') {{
        parentWindow.__ifcLiteLastSelectionSig = '';
    }}

    if (parentWindow.__ifcLiteSelectionMessageHandler) {{
        parentWindow.removeEventListener('message', parentWindow.__ifcLiteSelectionMessageHandler);
    }}
    parentWindow.__ifcLiteSelectionMessageHandler = (event) => {{
        if (event.origin !== VIEWER_ORIGIN && event.origin !== window.location.origin) return;
        const msg = event.data;
        if (!msg || typeof msg !== 'object') return;
        if (msg.type === 'ifc-lite-viewer-selection') {{
            const guid = typeof msg.guid === 'string' ? msg.guid : null;
            const mapHit = guid ? GUID_MAP[guid] : null;
            console.log('[viewer-bridge] viewer-selection guid=', guid,
                        'mapHit=', mapHit,
                        'labels=', parentWindow.document.querySelectorAll('.ai-map-group-label').length);
            highlightGuid(guid, true);
        }}
    }};
    parentWindow.addEventListener('message', parentWindow.__ifcLiteSelectionMessageHandler);

    if (parentWindow.__ifcLitePointerDownHandler) {{
        parentWindow.document.removeEventListener('pointerdown', parentWindow.__ifcLitePointerDownHandler, true);
    }}
    parentWindow.__ifcLitePointerDownHandler = (event) => {{
        const target = event.target;
        if (isViewerInteraction(target)) {{
            return;
        }}

        if (isSelectInteraction(target)) {{
            parentWindow.__ifcLiteForceDeselect = false;
            return;
        }}

        parentWindow.__ifcLiteForceDeselect = true;
        postClearSelection();
    }};
    parentWindow.document.addEventListener('pointerdown', parentWindow.__ifcLitePointerDownHandler, true);

    const sendToViewer = () => {{
        const currentSelectionSig = JSON.stringify({{
            guid: typeof selected.guid === 'string' ? selected.guid : null,
            guids: Array.isArray(selected.guids) ? selected.guids : []
        }});

        const hasRequestedSelection = Boolean(
            (typeof selected.guid === 'string' && selected.guid.trim()) ||
            (Array.isArray(selected.guids) && selected.guids.length > 0)
        );

        if (hasRequestedSelection && currentSelectionSig !== parentWindow.__ifcLiteLastSelectionSig) {{
            parentWindow.__ifcLiteForceDeselect = false;
        }}

        if (parentWindow.__ifcLiteForceDeselect && !hasRequestedSelection) {{
            postClearSelection();
            return;
        }}

        if (parentWindow.__ifcLiteForceDeselect && currentSelectionSig === parentWindow.__ifcLiteLastSelectionSig) {{
            postClearSelection();
            return;
        }}

        const frame = getViewerFrame();
        if (frame && frame.contentWindow) {{
            if (Array.isArray(selected.guids) && selected.guids.length > 1) {{
                frame.contentWindow.postMessage({{ type: 'ifc-lite-select-guids', guids: selected.guids }}, VIEWER_ORIGIN);
            }} else {{
                frame.contentWindow.postMessage({{ type: 'ifc-lite-select-guid', guid: selected.guid || null }}, VIEWER_ORIGIN);
            }}
            parentWindow.__ifcLiteLastSelectionSig = currentSelectionSig;
        }}
    }};

    try {{
        sendToViewer();
        highlightGuid(selected.guid || null);
    }} catch (err) {{
        console.warn('Viewer bridge failed to post selection', err);
    }}

    if (window.Streamlit && typeof window.Streamlit.setFrameHeight === 'function') {{
        window.Streamlit.setFrameHeight(0);
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
