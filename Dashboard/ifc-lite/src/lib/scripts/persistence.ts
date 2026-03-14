/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * Script persistence — localStorage-backed storage for user scripts.
 */

const STORAGE_KEY = 'ifc-lite:scripts';
const MAX_SCRIPTS = 50;
const MAX_SCRIPT_SIZE = 512 * 1024; // 512 KB per script
const MAX_NAME_LENGTH = 100;

export interface SavedScript {
  id: string;
  name: string;
  code: string;
  createdAt: number;
  updatedAt: number;
  version: number;
}

/** Load saved scripts from localStorage */
export function loadSavedScripts(): SavedScript[] {
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

/** Save scripts to localStorage */
export function saveScripts(scripts: SavedScript[]): { ok: boolean; message?: string } {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(scripts));
    return { ok: true };
  } catch (e) {
    return { ok: false, message: e instanceof Error ? e.message : 'Storage error' };
  }
}

/** Validate and sanitize a script name. Returns null if invalid. */
export function validateScriptName(name: string): string | null {
  const trimmed = name.trim();
  if (!trimmed) return null;
  if (trimmed.length > MAX_NAME_LENGTH) return trimmed.slice(0, MAX_NAME_LENGTH);
  return trimmed;
}

/** Check if the user can create more scripts */
export function canCreateScript(currentCount: number): boolean {
  return currentCount < MAX_SCRIPTS;
}

/** Check if script code is within size limits */
export function isScriptWithinSizeLimit(code: string): boolean {
  return new Blob([code]).size <= MAX_SCRIPT_SIZE;
}
