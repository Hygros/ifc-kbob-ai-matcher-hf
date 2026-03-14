/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * Lists module — bridges IfcDataStore to @ifc-lite/lists engine
 * and provides import/export helpers for list definitions.
 */

import type { IfcDataStore } from '@ifc-lite/parser';
import { extractPropertiesOnDemand, extractQuantitiesOnDemand } from '@ifc-lite/parser';
import type { IfcTypeEnum } from '@ifc-lite/data';
import type { ListDataProvider, ListDefinition } from '@ifc-lite/lists';

// Re-export engine and types from @ifc-lite/lists
export { executeList, listResultToCSV } from '@ifc-lite/lists';
export { LIST_PRESETS } from '@ifc-lite/lists';
export { discoverColumns } from '@ifc-lite/lists';
export type { ListDefinition, ListResult, ListDataProvider, ListRow, CellValue, ColumnDefinition } from '@ifc-lite/lists';

/**
 * Create a ListDataProvider that bridges an IfcDataStore to the list engine.
 */
export function createListDataProvider(ifcDataStore: IfcDataStore): ListDataProvider {
  return {
    getEntitiesByType(type: IfcTypeEnum): number[] {
      return ifcDataStore.entities.getByType(type);
    },
    getEntityName(expressId: number): string {
      return ifcDataStore.entities.getName(expressId) || '';
    },
    getEntityGlobalId(expressId: number): string {
      return ifcDataStore.entities.getGlobalId(expressId) || '';
    },
    getEntityDescription(expressId: number): string {
      return ifcDataStore.entities.getDescription(expressId) || '';
    },
    getEntityObjectType(expressId: number): string {
      return ifcDataStore.entities.getObjectType(expressId) || '';
    },
    getEntityTag(expressId: number): string {
      // Tag is extracted on-demand from source buffer
      return '';
    },
    getEntityTypeName(expressId: number): string {
      return ifcDataStore.entities.getTypeName(expressId) || '';
    },
    getPropertySets(expressId: number) {
      if (ifcDataStore.properties) {
        return ifcDataStore.properties.getForEntity(expressId);
      }
      return extractPropertiesOnDemand(ifcDataStore, expressId);
    },
    getQuantitySets(expressId: number) {
      if (ifcDataStore.quantities) {
        return ifcDataStore.quantities.getForEntity(expressId);
      }
      return extractQuantitiesOnDemand(ifcDataStore, expressId);
    },
  };
}

/**
 * Import a list definition from a JSON file.
 */
export async function importListDefinition(file: File): Promise<ListDefinition> {
  const text = await file.text();
  const parsed = JSON.parse(text) as ListDefinition;
  // Assign a new ID to avoid collisions
  parsed.id = crypto.randomUUID();
  parsed.createdAt = Date.now();
  parsed.updatedAt = Date.now();
  return parsed;
}

/**
 * Export a list definition as a downloadable JSON file.
 */
export function exportListDefinition(definition: ListDefinition): void {
  const json = JSON.stringify(definition, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${definition.name || 'list'}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
