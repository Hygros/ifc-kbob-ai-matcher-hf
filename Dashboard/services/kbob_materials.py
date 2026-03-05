import os
import sqlite3
import sys
from pathlib import Path

import streamlit as st

from Dashboard.config import REINFORCEMENT_KBOB_MATERIAL, REINFORCEMENT_STEEL_DENSITY_FALLBACK


TABLE_NAME = "Oekobilanzdaten"
COLUMN_MATERIAL = "Material"
COLUMN_DENSITY = "Rohdichte"

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


# ---------------------------------------------------------------------------
# Armierungsstahl-Rohdichte aus KBOB-DB
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_reinforcement_density_cached(db_path: str) -> float | None:
    """Query the ``Rohdichte`` column for the reinforcement steel entry."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT [{COLUMN_DENSITY}] FROM {TABLE_NAME} "
            f"WHERE {COLUMN_MATERIAL} = ?",
            (REINFORCEMENT_KBOB_MATERIAL,),
        )
        row = cursor.fetchone()
        if row and row[0] is not None:
            try:
                return float(row[0])
            except (TypeError, ValueError):
                return None
    return None


def get_reinforcement_steel_density() -> float:
    """Return the density (kg/m³) for *Armierungsstahl* from the KBOB DB.

    Falls back to ``REINFORCEMENT_STEEL_DENSITY_FALLBACK`` (7 850 kg/m³)
    when the database is unreachable or the value is missing.
    """
    db_path = resolve_kbob_db_path()
    if db_path is None:
        return REINFORCEMENT_STEEL_DENSITY_FALLBACK
    try:
        density = _load_reinforcement_density_cached(str(db_path))
        if density is not None and density > 0:
            return density
    except Exception:
        pass
    return REINFORCEMENT_STEEL_DENSITY_FALLBACK
