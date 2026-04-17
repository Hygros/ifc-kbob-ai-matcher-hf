import json
import os
from urllib.parse import quote, urlencode

import streamlit as st

from Dashboard.config import IS_HF_SPACE


DASHBOARD_DIR = os.path.dirname(os.path.dirname(__file__))
STREAMLIT_STATIC_PREFIX = "/app/static"
STREAMLIT_VIEWER_INDEX_URL = f"{STREAMLIT_STATIC_PREFIX}/viewer/index.html"


def _use_streamlit_static_delivery() -> bool:
    mode = str(os.environ.get("COMPONENT_SERVE_MODE", "")).strip().lower()
    if mode in {"streamlit", "streamlit-static"}:
        return True
    if mode in {"viewer-dev-server", "legacy"}:
        return False

    if IS_HF_SPACE:
        return True

    viewer_index = os.path.join(DASHBOARD_DIR, "static", "viewer", "index.html")
    return os.path.exists(viewer_index)


def _normalize_selected_guids(active_guid: str | None, active_guids: list[str] | None) -> tuple[str | None, list[str]]:
    guid = active_guid if isinstance(active_guid, str) and active_guid.strip() else None
    guids = [entry for entry in (active_guids or []) if isinstance(entry, str) and entry.strip()]
    if guid and guid not in guids:
        guids.append(guid)
    return guid, guids


def selection_signature(active_guid: str | None, active_guids: list[str] | None) -> str:
    guid, guids = _normalize_selected_guids(active_guid, active_guids)
    return json.dumps({"guid": guid, "guids": guids}, separators=(",", ":"), ensure_ascii=True)


def build_component_file_url(ifc_filename: str, cache_bust: str) -> str:
    encoded = quote(str(ifc_filename), safe="/")

    static_origin = str(os.environ.get("COMPONENT_STATIC_ORIGIN", "")).strip().rstrip("/")
    if static_origin:
        return f"{static_origin}/{encoded}?v={cache_bust}"

    if _use_streamlit_static_delivery():
        return f"{STREAMLIT_STATIC_PREFIX}/{encoded}?v={cache_bust}"

    return f"http://127.0.0.1:8080/{encoded}?v={cache_bust}"


def build_component_viewer_url(file_url: str, cache_bust: str) -> str:
    viewer_base = str(os.environ.get("COMPONENT_VIEWER_URL", "")).strip()
    if not viewer_base:
        if _use_streamlit_static_delivery():
            viewer_base = STREAMLIT_VIEWER_INDEX_URL
        else:
            viewer_base = "http://localhost:3000/"

    query = urlencode({"file_url": file_url, "v": cache_bust})
    separator = "&" if "?" in viewer_base else "?"
    return f"{viewer_base}{separator}{query}"


def render_ifc_viewer_component(viewer_url: str) -> None:
    st.markdown(
        f"<div class='viewer-sticky'><iframe class='viewer-iframe' src='{viewer_url}'></iframe></div>",
        unsafe_allow_html=True,
    )


def render_component_viewer_bridge(
    selected_guid: str | None,
    selected_guids: list[str] | None,
    guid_map: dict[str, list[int]] | None = None,
    bridge_selection_signature: str | None = None,
) -> None:
    guid, guids = _normalize_selected_guids(selected_guid, selected_guids)
    payload = json.dumps({"guid": guid, "guids": guids})
    guid_map_json = json.dumps(guid_map or {})
    selection_sig = bridge_selection_signature or selection_signature(guid, guids)

    bridge_html = f"""
<script>
(() => {{
    const selected = {payload};
    const GUID_MAP = {guid_map_json};
    const selectionSig = {json.dumps(selection_sig)};
    const parentWindow = window.parent;
    const getViewerFrame = () => parentWindow.document.querySelector('iframe.viewer-iframe');
    const maxSendAttempts = 20;

    const ensureBridgeState = () => {{
        if (!parentWindow.__ifcLiteComponentBridgeState) {{
            parentWindow.__ifcLiteComponentBridgeState = {{
                lastSentSignature: '',
                pendingSignature: '',
                pendingMessage: null,
                viewerReady: false,
            }};
        }}
        return parentWindow.__ifcLiteComponentBridgeState;
    }};

    const state = ensureBridgeState();

    const resolveViewerOrigin = (frameCandidate) => {{
        if (frameCandidate && frameCandidate.src) {{
            try {{
                return new URL(frameCandidate.src, parentWindow.location.href).origin;
            }} catch (e) {{}}
        }}
        return window.location.origin;
    }};

    const makeMessageId = (prefix) => `${{prefix}}-${{Date.now()}}-${{Math.random().toString(36).slice(2, 8)}}`;

    let highlighted = [];
    const clearHighlight = () => {{
        highlighted.forEach((el) => {{
            el.style.backgroundColor = '';
            el.style.padding = '';
            el.style.borderRadius = '';
        }});
        highlighted = [];
    }};

    const highlightGuid = (guidValue, shouldScroll = false) => {{
        clearHighlight();
        if (!guidValue) return;

        const groupIndices = GUID_MAP[guidValue] || [];
        if (!groupIndices.length) {{
            console.warn('[component-bridge] incoming GUID not mapped in current list', guidValue, Object.keys(GUID_MAP).slice(0, 10));
            return;
        }}

        const labels = parentWindow.document.querySelectorAll('.ai-map-group-label');
        let firstLabel = null;
        groupIndices.forEach((idx) => {{
            const el = labels[idx];
            if (!el) return;
            el.style.backgroundColor = '#d9ffcd';
            el.style.padding = '0.15rem 0.35rem';
            el.style.borderRadius = '4px';
            highlighted.push(el);
            if (!firstLabel) firstLabel = el;
        }});

        if (shouldScroll && firstLabel) {{
            try {{
                firstLabel.scrollIntoView({{ behavior: 'instant', block: 'center', inline: 'nearest' }});
            }} catch (err) {{
                firstLabel.scrollIntoView();
            }}
        }}
    }};

    const postSelection = (guidsValue) => {{
        const viewerFrame = getViewerFrame();
        const viewerOrigin = resolveViewerOrigin(viewerFrame);
        return {{
            origin: viewerOrigin,
            message: {{
                source: 'ifc-lite-embed',
                version: '1',
                type: 'SELECT_BY_GUID',
                messageId: makeMessageId('select'),
                data: {{ guids: guidsValue }}
            }}
        }};
    }};

    const postClear = () => {{
        const viewerFrame = getViewerFrame();
        const viewerOrigin = resolveViewerOrigin(viewerFrame);
        return {{
            origin: viewerOrigin,
            message: {{
                source: 'ifc-lite-embed',
                version: '1',
                type: 'CLEAR_SELECTION',
                messageId: makeMessageId('clear')
            }}
        }};
    }};

    const sendMessageWithRetry = (wrapped, attempt = 0) => {{
        const frameNow = getViewerFrame();
        const origin = resolveViewerOrigin(frameNow);
        if (!frameNow || !frameNow.contentWindow) {{
            if (attempt >= maxSendAttempts) {{
                console.warn('[component-bridge] viewer iframe unavailable, dropping message after retries');
                return;
            }}
            setTimeout(() => sendMessageWithRetry(wrapped, attempt + 1), 100);
            return;
        }}

        try {{
            frameNow.contentWindow.postMessage(wrapped.message, origin || wrapped.origin);
            state.lastSentSignature = state.pendingSignature || selectionSig;
            state.pendingSignature = '';
            state.pendingMessage = null;
        }} catch (err) {{
            if (attempt >= maxSendAttempts) {{
                console.warn('[component-bridge] failed to post selection message', err);
                return;
            }}
            setTimeout(() => sendMessageWithRetry(wrapped, attempt + 1), 100);
        }}
    }};

    const queueSelection = (wrapped) => {{
        state.pendingSignature = selectionSig;
        state.pendingMessage = wrapped;
        if (!state.viewerReady) {{
            sendMessageWithRetry(wrapped, 0);
            return;
        }}
        sendMessageWithRetry(wrapped, 0);
    }};

    const flushPendingSelection = () => {{
        if (!state.pendingMessage) return;
        sendMessageWithRetry(state.pendingMessage, 0);
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

    const clearSelectionInViewer = () => {{
        const wrapped = postClear();
        queueSelection(wrapped);
    }};

    if (parentWindow.__ifcLiteComponentPointerDownHandler) {{
        parentWindow.document.removeEventListener('pointerdown', parentWindow.__ifcLiteComponentPointerDownHandler, true);
    }}

    parentWindow.__ifcLiteComponentPointerDownHandler = (event) => {{
        const target = event.target;
        if (isViewerInteraction(target)) return;
        if (isSelectInteraction(target)) return;
        clearSelectionInViewer();
        highlightGuid(null, false);
    }};
    parentWindow.document.addEventListener('pointerdown', parentWindow.__ifcLiteComponentPointerDownHandler, true);

    if (parentWindow.__ifcLiteComponentSelectionHandler) {{
        parentWindow.removeEventListener('message', parentWindow.__ifcLiteComponentSelectionHandler);
    }}

    parentWindow.__ifcLiteComponentSelectionHandler = (event) => {{
        const msg = event.data;
        if (!msg || typeof msg !== 'object') return;

        if (msg.type === 'ifc-lite-viewer-ready' || (msg.source === 'ifc-lite-embed' && msg.type === 'VIEWER_READY')) {{
            state.viewerReady = true;
            flushPendingSelection();
            return;
        }}

        const viewerFrame = getViewerFrame();
        const viewerOrigin = resolveViewerOrigin(viewerFrame);
        if (event.origin !== viewerOrigin && event.origin !== window.location.origin && event.origin !== parentWindow.location.origin) return;

        if (msg.type === 'ifc-lite-viewer-error') {{
            console.warn('[component-bridge] viewer error', msg);
            return;
        }}

        if (msg.type !== 'ifc-lite-viewer-selection') return;
        const incomingGuid = typeof msg.guid === 'string' ? msg.guid : null;
        highlightGuid(incomingGuid, true);
    }};

    parentWindow.addEventListener('message', parentWindow.__ifcLiteComponentSelectionHandler);

    if (state.lastSentSignature !== selectionSig) {{
        if (selected.guids.length > 0) {{
            queueSelection(postSelection(selected.guids));
        }} else {{
            queueSelection(postClear());
        }}
    }}

    highlightGuid(selected.guid || null, false);
}})();
</script>
"""

    st.html(bridge_html, unsafe_allow_javascript=True)
