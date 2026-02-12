from __future__ import annotations

import re
import sys
import time
from typing import Dict, Iterable, List, Tuple

import requests
from bs4 import BeautifulSoup

TERMS = ["Pfahl"]  # adjust terms here

API_BASE_URL = "https://api.conceptnet.io/query"
SITE_QUERY_URL = "https://conceptnet.io/query"
DEFAULT_LANG = "de"
USER_AGENT = "AAA_Python_MTH/ConceptNetClient (+https://example.invalid)"


def conceptnet_synonyms(
	term: str,
	*,
	lang: str = DEFAULT_LANG,
	limit: int = 20,
	min_weight: float = 1.0,
	retries: int = 3,
	backoff: float = 0.5,
) -> List[str]:
	"""Fetch ConceptNet synonyms for ``term`` and return plain text strings."""

	node_uri = f"/c/{lang}/{term.replace(' ', '_').lower()}"
	params = {"node": node_uri, "rel": "/r/Synonym", "limit": str(limit * 4)}
	try:
		edges = list(
			_fetch_edges_from_api(params=params, retries=retries, backoff=backoff)
		)
	except ConceptNetAPIUnavailable:
		edges = list(_fetch_edges_from_html(params=params))

	results: Dict[str, float] = {}
	for edge in edges:
		weight = float(edge.get("weight", 1.0))
		if weight < min_weight:
			continue

		start = edge.get("start", {})
		end = edge.get("end", {})
		other = _other_node(start, end, node_uri)
		if other.get("language") != lang:
			continue

		label = (other.get("label") or other.get("term") or "").strip()
		if label:
			norm = label.replace(" ", "_").lower()
			current_weight = results.get(label, 0.0)
			if weight > current_weight:
				results[label] = weight

	origin_norm = term.replace(" ", "_").lower()
	filtered: List[Tuple[str, float]] = [
		(label, weight) for label, weight in results.items() if label.replace(" ", "_").lower() != origin_norm
	]
	sorted_synonyms = [
		label for label, _ in sorted(filtered, key=lambda item: (-item[1], item[0].casefold()))
	]

	return sorted_synonyms[:limit]


class ConceptNetAPIUnavailable(Exception):
	"""Raised when the ConceptNet JSON API cannot be reached."""


def _fetch_edges_from_api(*, params: Dict[str, str], retries: int, backoff: float) -> Iterable[dict]:
	headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
	last_error: Exception | None = None

	for attempt in range(1, retries + 1):
		try:
			response = requests.get(API_BASE_URL, params=params, headers=headers, timeout=10)
			if response.status_code in {429, 500, 502, 503, 504}:
				raise requests.HTTPError(response=response)
			response.raise_for_status()
			if "application/json" not in response.headers.get("Content-Type", ""):
				raise requests.HTTPError("Unexpected content type")
			data = response.json()
			edges = data.get("edges", []) if isinstance(data, dict) else []
			return edges
		except (requests.Timeout, requests.ConnectionError, requests.HTTPError, requests.JSONDecodeError) as exc:
			last_error = exc
			if attempt < retries:
				time.sleep(backoff * (2 ** (attempt - 1)))
			continue

	raise ConceptNetAPIUnavailable(last_error)


def _fetch_edges_from_html(*, params: Dict[str, str]) -> Iterable[dict]:
	headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
	response = requests.get(SITE_QUERY_URL, params=params, headers=headers, timeout=10)
	response.raise_for_status()
	soup = BeautifulSoup(response.text, "html.parser")
	table = soup.select_one("table.edge-table")
	if not table:
		return []

	edges: List[dict] = []
	for row in table.select("tr.edge-main"):
		start_link = row.select_one("td.edge-start a[href]")
		end_link = row.select_one("td.edge-end a[href]")
		if not (start_link and end_link):
			continue

		start_href_attr = start_link.get("href")
		end_href_attr = end_link.get("href")
		if not (isinstance(start_href_attr, str) and isinstance(end_href_attr, str)):
			continue
		start_href = start_href_attr
		end_href = end_href_attr

		rel_cell = row.select_one("td.edge-rel")
		weight = 1.0
		if rel_cell:
			match = re.search(r"Weight:\s*([0-9.]+)", rel_cell.get_text(" ", strip=True))
			if match:
				try:
					weight = float(match.group(1))
				except ValueError:
					pass

		edges.append(
			{
				"weight": weight,
				"start": {
					"@id": start_href,
					"label": start_link.get_text(strip=True),
					"language": _language_from_uri(start_href),
				},
				"end": {
					"@id": end_href,
					"label": end_link.get_text(strip=True),
					"language": _language_from_uri(end_href),
				},
			}
		)

	return edges


def _other_node(start: dict, end: dict, node_uri: str) -> dict:
	"""Return the node on the opposite side of the relation."""

	if start.get("@id") == node_uri:
		return end
	if end.get("@id") == node_uri:
		return start

	target = node_uri.rsplit("/", 1)[-1]
	start_norm = _normalize_label(start.get("label"))
	end_norm = _normalize_label(end.get("label"))
	if target in {start_norm, end_norm}:
		return end if start_norm == target else start

	return {}


def _normalize_label(label: str | None) -> str:
	if not label:
		return ""
	return label.strip().replace(" ", "_").lower()


def _language_from_uri(uri: str) -> str:
	parts = uri.strip("/").split("/")
	if len(parts) >= 2:
		return parts[1]
	return ""


LANG = DEFAULT_LANG
LIMIT = 20
MIN_WEIGHT = 1.0


def main() -> int:
	for idx, term in enumerate(TERMS):
		synonyms = conceptnet_synonyms(
			term,
			lang=LANG,
			limit=LIMIT,
			min_weight=MIN_WEIGHT,
		)
		print("\n" if idx else "", end="")
		if synonyms:
			for synonym in synonyms:
				print(synonym)
		else:
			print(f"<no synonyms found for '{term}'>")
	return 0


if __name__ == "__main__":
	sys.exit(main())