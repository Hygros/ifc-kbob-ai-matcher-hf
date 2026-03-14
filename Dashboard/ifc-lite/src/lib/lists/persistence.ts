/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * List definitions persistence — localStorage-backed storage for saved list definitions.
 */

import type { ListDefinition } from '@ifc-lite/lists';

const STORAGE_KEY = 'ifc-lite:list-definitions';

/** Load saved list definitions from localStorage */
export function loadListDefinitions(): ListDefinition[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

/** Save list definitions to localStorage */
export function saveListDefinitions(definitions: ListDefinition[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(definitions));
  } catch {
    // Silently ignore storage errors
  }
}
