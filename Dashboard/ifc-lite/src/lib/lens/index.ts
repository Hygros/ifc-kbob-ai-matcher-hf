/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * Bridge between the app's data model (IfcDataStore + FederatedModel)
 * and the @ifc-lite/lens engine's LensDataProvider interface.
 *
 * Handles both single-model and multi-model (federated) scenarios.
 */

import type { LensDataProvider, PropertySetInfo, ClassificationInfo } from '@ifc-lite/lens';
import type { IfcDataStore } from '@ifc-lite/parser';
import { extractPropertiesOnDemand, extractClassificationsOnDemand, extractMaterialsOnDemand, extractEntityAttributesOnDemand } from '@ifc-lite/parser';
import type { FederatedModel } from '@/store/types';

/**
 * Create a LensDataProvider that bridges IfcDataStore(s) to the lens engine.
 *
 * @param models  Map of federated models (may be empty for single-model mode)
 * @param ifcDataStore  Single-model data store (fallback when models is empty)
 */
export function createLensDataProvider(
  models: Map<string, FederatedModel>,
  ifcDataStore?: IfcDataStore | null,
): LensDataProvider {
  // Collect all (modelId, dataStore, idOffset) tuples
  const sources: Array<{ modelId: string; store: IfcDataStore; idOffset: number }> = [];

  if (models.size > 0) {
    for (const [id, model] of models) {
      if (model.visible) {
        sources.push({ modelId: id, store: model.ifcDataStore, idOffset: model.idOffset });
      }
    }
  } else if (ifcDataStore) {
    sources.push({ modelId: 'default', store: ifcDataStore, idOffset: 0 });
  }

  // Reverse lookup: globalId → (store, localId, modelId)
  const resolve = (globalId: number): { store: IfcDataStore; localId: number; modelId: string } | null => {
    for (const src of sources) {
      const localId = globalId - src.idOffset;
      if (localId > 0 && localId <= (src.store.entityCount ?? 0)) {
        return { store: src.store, localId, modelId: src.modelId };
      }
    }
    return null;
  };

  return {
    getEntityCount(): number {
      let total = 0;
      for (const src of sources) total += src.store.entityCount;
      return total;
    },

    forEachEntity(callback: (globalId: number, modelId: string) => void): void {
      for (const src of sources) {
        const entities = src.store.entities;
        for (let i = 0; i < entities.count; i++) {
          const expressId = entities.expressId[i];
          callback(expressId + src.idOffset, src.modelId);
        }
      }
    },

    getEntityType(globalId: number): string | undefined {
      const r = resolve(globalId);
      if (!r) return undefined;
      return r.store.entities.getTypeName(r.localId) || undefined;
    },

    getPropertyValue(globalId: number, propertySetName: string, propertyName: string): unknown {
      const r = resolve(globalId);
      if (!r) return undefined;
      // Try columnar table first, fall back to on-demand extraction
      if (r.store.properties) {
        const val = r.store.properties.getPropertyValue(r.localId, propertySetName, propertyName);
        if (val !== null) return val;
      }
      const psets = extractPropertiesOnDemand(r.store, r.localId);
      for (const pset of psets) {
        if (pset.name === propertySetName) {
          for (const prop of pset.properties) {
            if (prop.name === propertyName) return prop.value;
          }
        }
      }
      return undefined;
    },

    getPropertySets(globalId: number): PropertySetInfo[] {
      const r = resolve(globalId);
      if (!r) return [];
      if (r.store.properties) {
        return r.store.properties.getForEntity(r.localId).map(ps => ({
          name: ps.name,
          properties: ps.properties.map(p => ({ name: p.name, value: p.value })),
        }));
      }
      return extractPropertiesOnDemand(r.store, r.localId).map(ps => ({
        name: ps.name,
        properties: ps.properties.map(p => ({ name: p.name, value: p.value })),
      }));
    },

    getEntityAttribute(globalId: number, attrName: string): string | undefined {
      const r = resolve(globalId);
      if (!r) return undefined;
      // Fast path: columnar entity table has common attributes
      const entities = r.store.entities;
      switch (attrName) {
        case 'Name': return entities.getName(r.localId) || undefined;
        case 'Description': return entities.getDescription(r.localId) || undefined;
        case 'ObjectType': return entities.getObjectType(r.localId) || undefined;
        case 'Tag': {
          const attrs = extractEntityAttributesOnDemand(r.store, r.localId);
          return attrs.tag || undefined;
        }
        default: {
          const attrs = extractEntityAttributesOnDemand(r.store, r.localId);
          return (attrs as Record<string, string>)[attrName.toLowerCase()] || undefined;
        }
      }
    },

    getQuantityValue(globalId: number, qsetName: string, quantName: string): number | string | undefined {
      const r = resolve(globalId);
      if (!r) return undefined;
      if (r.store.quantities) {
        const val = r.store.quantities.getQuantityValue(r.localId, qsetName, quantName);
        if (val !== null) return val;
      }
      return undefined;
    },

    getQuantitySets(globalId: number): ReadonlyArray<{ name: string; quantities: ReadonlyArray<{ name: string }> }> {
      const r = resolve(globalId);
      if (!r) return [];
      if (r.store.quantities) {
        return r.store.quantities.getForEntity(r.localId).map(qs => ({
          name: qs.name,
          quantities: qs.quantities.map(q => ({ name: q.name })),
        }));
      }
      return [];
    },

    getClassifications(globalId: number): ClassificationInfo[] {
      const r = resolve(globalId);
      if (!r) return [];
      return extractClassificationsOnDemand(r.store, r.localId).map(c => ({
        system: c.system,
        identification: c.identification,
        name: c.name,
      }));
    },

    getMaterialName(globalId: number): string | undefined {
      const r = resolve(globalId);
      if (!r) return undefined;
      const mat = extractMaterialsOnDemand(r.store, r.localId);
      if (!mat) return undefined;
      if (mat.name) return mat.name;
      if (mat.layers?.[0]?.materialName) return mat.layers[0].materialName;
      if (mat.constituents?.[0]?.materialName) return mat.constituents[0].materialName;
      if (mat.profiles?.[0]?.materialName) return mat.profiles[0].materialName;
      if (mat.materials?.[0]) return mat.materials[0];
      return undefined;
    },
  };
}
