import { useEffect, useMemo, useRef } from 'react';
import { useIfc } from '@/hooks/useIfc';
import { resolveEntityRef, useViewerStore } from '@/store';
import { IfcQuery } from '@ifc-lite/query';

type LegacySelectGuidMessage = {
    type: 'ifc-lite-select-guid';
    guid?: string | null;
};

type LegacySelectGuidsMessage = {
    type: 'ifc-lite-select-guids';
    guids?: string[];
};

type EmbedSelectByGuidMessage = {
    source: 'ifc-lite-embed';
    version?: string;
    type: 'SELECT_BY_GUID';
    data?: {
        guids?: string[];
    };
};

type EmbedClearSelectionMessage = {
    source: 'ifc-lite-embed';
    version?: string;
    type: 'CLEAR_SELECTION';
};

type IncomingMessage =
    | LegacySelectGuidMessage
    | LegacySelectGuidsMessage
    | EmbedSelectByGuidMessage
    | EmbedClearSelectionMessage;

function parseModelUrl(search: string): string | null {
    const params = new URLSearchParams(search);
    return params.get('modelUrl') || params.get('file_url') || params.get('file');
}

function filenameFromUrl(inputUrl: string): string {
    try {
        const parsed = new URL(inputUrl);
        const last = parsed.pathname.split('/').filter(Boolean).pop();
        return last || 'model.ifc';
    } catch {
        const raw = inputUrl.split('?')[0].split('#')[0];
        const last = raw.split('/').filter(Boolean).pop();
        return last || 'model.ifc';
    }
}

function resolveGlobalIdsFromGuids(guids: string[]): number[] {
    const state = useViewerStore.getState();
    const wanted = new Set(guids.filter((entry) => typeof entry === 'string' && entry.trim()).map((entry) => entry.trim()));
    if (wanted.size === 0) {
        return [];
    }

    const resolved = new Set<number>();
    const remaining = new Set(wanted);

    for (const [, model] of state.models) {
        const entities = model.ifcDataStore?.entities;
        if (!entities) {
            continue;
        }

        const offset = model.idOffset ?? 0;
        for (const guid of wanted) {
            const localExpressId = entities.getExpressIdByGlobalId(guid);
            if (localExpressId > 0) {
                resolved.add(localExpressId + offset);
                remaining.delete(guid);
            }
        }
    }

    if (resolved.size === 0 && state.ifcDataStore?.entities) {
        const entities = state.ifcDataStore.entities;
        for (const guid of wanted) {
            const expressId = entities.getExpressIdByGlobalId(guid);
            if (expressId > 0) {
                resolved.add(expressId);
                remaining.delete(guid);
            }
        }
    }

    // Fallback: for GUIDs not in the pre-parsed entity table (e.g. IfcCovering),
    // use on-demand extraction via IfcQuery to search entityIndex.
    // Narrow search to types that have geometry but aren't pre-indexed for GlobalId.
    if (remaining.size > 0) {
        const fallbackTypes = ['IFCCOVERING', 'IFCANNOTATION', 'IFCGRID',
            'IFCBUILDINGSYSTEM', 'IFCDISTRIBUTIONPORT', 'IFCPROXY'];
        for (const [, model] of state.models) {
            const ds = model.ifcDataStore;
            if (!ds?.entityIndex?.byType) continue;
            const offset = model.idOffset ?? 0;
            const q = new IfcQuery(ds);
            for (const typeName of fallbackTypes) {
                const ids = ds.entityIndex.byType.get(typeName);
                if (!ids) continue;
                for (const expressId of ids) {
                    if (remaining.size === 0) break;
                    const node = q.entity(expressId);
                    if (node?.globalId && remaining.has(node.globalId)) {
                        resolved.add(expressId + offset);
                        remaining.delete(node.globalId);
                    }
                }
            }
        }
        // Legacy fallback
        if (remaining.size > 0 && state.ifcDataStore?.entityIndex?.byType) {
            const q = new IfcQuery(state.ifcDataStore);
            for (const typeName of fallbackTypes) {
                const ids = state.ifcDataStore.entityIndex.byType.get(typeName);
                if (!ids) continue;
                for (const expressId of ids) {
                    if (remaining.size === 0) break;
                    const node = q.entity(expressId);
                    if (node?.globalId && remaining.has(node.globalId)) {
                        resolved.add(expressId);
                        remaining.delete(node.globalId);
                    }
                }
            }
        }
    }

    return Array.from(resolved);
}

function applyGuidSelection(guids: string[]): void {
    const state = useViewerStore.getState();
    const resolvedIds = resolveGlobalIdsFromGuids(guids);

    state.clearEntitySelection();

    if (resolvedIds.length === 0) {
        return;
    }

    state.setSelectedEntityIds(resolvedIds);
    const activeGlobalId = resolvedIds[resolvedIds.length - 1];
    state.setSelectedEntityId(activeGlobalId);
    state.setSelectedEntity(resolveEntityRef(activeGlobalId));
}

export function StreamlitBridge() {
    const { loadFile, models, geometryResult, loading } = useIfc();
    const selectedEntity = useViewerStore((state) => state.selectedEntity);
    const selectedEntityIds = useViewerStore((state) => state.selectedEntityIds);
    const attemptedModelUrlRef = useRef<string | null>(null);
    const modelUrl = useMemo(() => parseModelUrl(window.location.search), []);

    const resolveGuidFromGlobalId = (globalId: number): string | null => {
        const state = useViewerStore.getState();
        const resolved = state.resolveGlobalIdFromModels(globalId);
        if (resolved) {
            const model = state.models.get(resolved.modelId);
            const fast = model?.ifcDataStore?.entities?.getGlobalId(resolved.expressId);
            if (fast) return fast;
            // Fallback: on-demand extraction for entity types not in GEOMETRY_TYPES
            // (e.g. IfcCovering whose GlobalId isn't pre-parsed into the entity table)
            if (model?.ifcDataStore) {
                const q = new IfcQuery(model.ifcDataStore);
                const node = q.entity(resolved.expressId);
                if (node?.globalId) return node.globalId;
            }
        }
        if (state.ifcDataStore?.entities) {
            const fast = state.ifcDataStore.entities.getGlobalId(globalId);
            if (fast) return fast;
            const q = new IfcQuery(state.ifcDataStore);
            const node = q.entity(globalId);
            if (node?.globalId) return node.globalId;
        }
        return null;
    };

    const resolveGuidFromEntityRef = (): string | null => {
        if (!selectedEntity) {
            return null;
        }
        const state = useViewerStore.getState();
        const model = state.models.get(selectedEntity.modelId);
        if (model?.ifcDataStore) {
            const fast = model.ifcDataStore.entities?.getGlobalId(selectedEntity.expressId);
            if (fast) return fast;
            // Fallback: on-demand extraction for entity types not in GEOMETRY_TYPES
            const q = new IfcQuery(model.ifcDataStore);
            const node = q.entity(selectedEntity.expressId);
            if (node?.globalId) return node.globalId;
        }
        if (selectedEntity.modelId === 'legacy' && state.ifcDataStore) {
            const fast = state.ifcDataStore.entities?.getGlobalId(selectedEntity.expressId);
            if (fast) return fast;
            const q = new IfcQuery(state.ifcDataStore);
            const node = q.entity(selectedEntity.expressId);
            if (node?.globalId) return node.globalId;
        }
        return null;
    };

    useEffect(() => {
        if (!modelUrl || loading) {
            return;
        }

        if (attemptedModelUrlRef.current === modelUrl) {
            return;
        }

        const alreadyLoaded = models.size > 0 || Boolean(geometryResult?.meshes?.length);
        if (alreadyLoaded) {
            return;
        }

        attemptedModelUrlRef.current = modelUrl;

        (async () => {
            try {
                const response = await fetch(modelUrl);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const buffer = await response.arrayBuffer();
                const file = new File([buffer], filenameFromUrl(modelUrl));
                await loadFile(file);
            } catch (err) {
                console.error('[StreamlitBridge] Failed to auto-load IFC model', err);
            }
        })();
    }, [modelUrl, loadFile, models.size, geometryResult?.meshes?.length, loading]);

    useEffect(() => {
        const onMessage = (event: MessageEvent<IncomingMessage>) => {
            const payload = event.data;
            if (!payload || typeof payload !== 'object') {
                return;
            }

            if (payload.type === 'ifc-lite-select-guid') {
                const guid = payload.guid;
                if (typeof guid === 'string' && guid.trim()) {
                    applyGuidSelection([guid]);
                } else {
                    useViewerStore.getState().clearEntitySelection();
                }
                return;
            }

            if (payload.type === 'ifc-lite-select-guids') {
                const guids = Array.isArray(payload.guids) ? payload.guids : [];
                applyGuidSelection(guids);
                return;
            }

            if (payload.source === 'ifc-lite-embed' && payload.type === 'CLEAR_SELECTION') {
                useViewerStore.getState().clearEntitySelection();
                return;
            }

            if (payload.source === 'ifc-lite-embed' && payload.type === 'SELECT_BY_GUID') {
                const guids = Array.isArray(payload.data?.guids) ? payload.data.guids : [];
                applyGuidSelection(guids);
            }
        };

        window.addEventListener('message', onMessage);
        return () => window.removeEventListener('message', onMessage);
    }, []);

    useEffect(() => {
        const guids: string[] = [];
        for (const globalId of selectedEntityIds) {
            const guid = resolveGuidFromGlobalId(globalId);
            if (guid) {
                guids.push(guid);
            }
        }

        const primaryGuid = resolveGuidFromEntityRef() || (guids.length > 0 ? guids[guids.length - 1] : null);

        if (window.parent !== window) {
            window.parent.postMessage(
                {
                    type: 'ifc-lite-viewer-selection',
                    guid: primaryGuid,
                    guids,
                },
                '*'
            );
        }
    }, [selectedEntity, selectedEntityIds]);

    return null;
}
