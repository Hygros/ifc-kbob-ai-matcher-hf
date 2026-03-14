/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * Recent files persistence — tracks recently opened IFC files
 * using localStorage for metadata and IndexedDB for cached file blobs.
 */

const STORAGE_KEY = 'ifc-lite:recent-files';
const DB_NAME = 'ifc-lite-files';
const STORE_NAME = 'blobs';
const MAX_RECENT = 10;

export interface RecentFileEntry {
  name: string;
  size: number;
  timestamp: number;
}

/** Record files as recently opened */
export function recordRecentFiles(files: Array<{ name: string; size: number }>): void {
  try {
    const existing = getRecentFiles();
    const now = Date.now();
    const newEntries: RecentFileEntry[] = files.map(f => ({
      name: f.name,
      size: f.size,
      timestamp: now,
    }));
    // Merge: new files on top, deduplicate by name
    const merged = [...newEntries, ...existing.filter(e => !files.some(f => f.name === e.name))];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged.slice(0, MAX_RECENT)));
  } catch {
    // Silently ignore storage errors
  }
}

/** Get recently opened files */
export function getRecentFiles(): RecentFileEntry[] {
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

/** Format file size for display (e.g. "5.2 MB") */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, i);
  return `${value < 10 && i > 0 ? value.toFixed(1) : Math.round(value)} ${units[i]}`;
}

// ── IndexedDB helpers for blob caching ──

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Cache file blobs in IndexedDB for instant re-opening */
export async function cacheFileBlobs(files: File[]): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    for (const file of files) {
      store.put(file, file.name);
    }
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    // Silently ignore IndexedDB errors
  }
}

/** Retrieve a cached file blob by name */
export async function getCachedFile(fileName: string): Promise<File | null> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.get(fileName);
    const result = await new Promise<File | null>((resolve, reject) => {
      request.onsuccess = () => resolve(request.result ?? null);
      request.onerror = () => reject(request.error);
    });
    db.close();
    return result;
  } catch {
    return null;
  }
}
