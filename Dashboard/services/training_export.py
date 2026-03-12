"""Export confirmed AI-mapping selections as training data (query + expected TXT files).

The two line-aligned TXT files can be fed directly into the training pipeline:

python Training/run_training_pipeline.py `
  --query-file Training/data/dashboard_training_queries.txt `
  --expected-file Training/data/dashboard_training_expected.txt `
  --base-model Training/artifacts/models/bge-m3-stage2-real-queries/epochs/epoch-03/bge-m3 `
  --output-dir Training/artifacts/models/bge-m3-finetuned-dashboard `
  --deduplicate --max-per-positive 30 `
  --epochs 3

"""

import math
from pathlib import Path

from Evaluation.export_sbert_queries_to_txt import IFC_EXPORT_FIELDS


QUERIES_FILENAME = "dashboard_training_queries.txt"
EXPECTED_FILENAME = "dashboard_training_expected.txt"

_SKIP_VALUES = {"NOTDEFINED", "Undefined", "nan", "None", "none", "null", ""}


def record_to_query(record: dict) -> str:
    """Build a query string from a record / row dict (same logic as ifc_entry_to_string)."""
    values: list[str] = []
    for field in IFC_EXPORT_FIELDS:
        raw_value = record.get(field, "")
        if raw_value is None or (isinstance(raw_value, float) and math.isnan(raw_value)):
            continue
        if isinstance(raw_value, list):
            raw_value = ", ".join(str(v) for v in raw_value if v is not None and str(v).strip())
        text = str(raw_value).strip()
        if text and text not in _SKIP_VALUES:
            values.append(text)
    return " ".join(values)


def _load_existing_pairs(output_dir: Path) -> list[tuple[str, str]]:
    """Load previously exported (query, expected) pairs from the TXT files."""
    queries_path = output_dir / QUERIES_FILENAME
    expected_path = output_dir / EXPECTED_FILENAME
    if not queries_path.exists() or not expected_path.exists():
        return []
    queries = queries_path.read_text(encoding="utf-8").splitlines()
    expected = expected_path.read_text(encoding="utf-8").splitlines()
    if len(queries) != len(expected):
        return []
    return list(zip(queries, expected))


def export_training_pairs(
    pairs: list[tuple[str, str]],
    output_dir: Path,
) -> tuple[int, int]:
    """Append manually confirmed *(query, expected_material)* pairs to training TXT files.

    Only pairs not yet present (case-insensitive dedup) are added.
    Returns ``(total_pairs, new_pairs_added)``.
    """
    existing_pairs = _load_existing_pairs(output_dir)
    seen: set[tuple[str, str]] = {(q.lower(), e.lower()) for q, e in existing_pairs}

    added = 0
    for query, expected in pairs:
        if not query or not expected:
            continue
        key = (query.lower(), expected.lower())
        if key not in seen:
            existing_pairs.append((query, expected))
            seen.add(key)
            added += 1

    output_dir.mkdir(parents=True, exist_ok=True)
    queries_path = output_dir / QUERIES_FILENAME
    expected_path = output_dir / EXPECTED_FILENAME
    queries_path.write_text(
        "\n".join(q for q, _ in existing_pairs) + ("\n" if existing_pairs else ""),
        encoding="utf-8",
    )
    expected_path.write_text(
        "\n".join(e for _, e in existing_pairs) + ("\n" if existing_pairs else ""),
        encoding="utf-8",
    )

    return len(existing_pairs), added
