import os
import sqlite3
import sys
from pathlib import Path

import streamlit as st


TABLE_NAME = "Oekobilanzdaten"
COLUMN_MATERIAL = "Material"

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
APP_ROOT = DASHBOARD_DIR.parent
if str(APP_ROOT) not in sys.path:
    sys.path.append(str(APP_ROOT))


def _candidate_db_paths() -> list[Path]:
    env_candidates = [
        os.environ.get("KBOB_DB_PATH", "").strip(),
        os.environ.get("ECOBILANZ_DB_PATH", "").strip(),
    ]
    candidates = [Path(path) for path in env_candidates if path]

    fallback_candidates = [
        APP_ROOT.parent / "Ökobilanzdaten.sqlite3",
        APP_ROOT.parent / "Oekobilanzdaten.sqlite3",
        APP_ROOT / "Ökobilanzdaten.sqlite3",
        APP_ROOT / "Oekobilanzdaten.sqlite3",
    ]
    candidates.extend(fallback_candidates)

    unique_candidates: list[Path] = []
    seen = set()
    for candidate in candidates:
        normalized = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(candidate)
    return unique_candidates


def resolve_kbob_db_path() -> Path | None:
    for candidate in _candidate_db_paths():
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


@st.cache_data(show_spinner=False)
def _load_all_kbob_materials_cached(db_path: str) -> list[str]:
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"SELECT {COLUMN_MATERIAL} FROM {TABLE_NAME} "
            f"WHERE {COLUMN_MATERIAL} IS NOT NULL AND TRIM({COLUMN_MATERIAL}) <> ''"
        )
        materials = [str(row[0]).strip() for row in cursor.fetchall() if row and row[0] is not None]
    deduped_materials = list(dict.fromkeys(materials))
    return sorted(deduped_materials, key=lambda value: value.lower())


def load_all_kbob_materials() -> tuple[list[str], str | None, str | None]:
    db_path = resolve_kbob_db_path()
    if db_path is None:
        return [], None, "KBOB-Datenbank nicht gefunden (KBOB_DB_PATH/ECOBILANZ_DB_PATH oder Standardpfade)."
    try:
        materials = _load_all_kbob_materials_cached(str(db_path))
        return materials, str(db_path), None
    except Exception as exc:
        return [], str(db_path), f"KBOB-Datenbank konnte nicht gelesen werden: {exc}"
