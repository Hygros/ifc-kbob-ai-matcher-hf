import json
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Matching Dashboard", layout="wide")
st.title("Matching Dashboard")

st.sidebar.header("Datenquelle")
data_input = st.sidebar.text_area(
	"JSON-Lines einfügen",
	height=200,
	help="Eine Zeile pro JSON-Objekt.",
)

def parse_jsonl(text: str) -> List[Dict[str, Any]]:
	rows = []
	for line in text.splitlines():
		line = line.strip()
		if not line:
			continue
		rows.append(json.loads(line))
	return rows

if data_input.strip():
	data = parse_jsonl(data_input)
else:
	st.info("Bitte JSON-Lines links einfügen.")
	st.stop()

df = pd.DataFrame(data)
base_cols = ["IfcEntity", "PredefinedType", "Name", "comment", "Durchmesser"]
base_df = df.reindex(columns=base_cols)

def format_matches(matches: List[Dict[str, Any]]) -> str:
	if not isinstance(matches, list):
		return ""
	return "\n".join([f"{m.get('material','')} ({m.get('score',0):.3f})" for m in matches])

base_df["top_k_matches"] = df["top_k_matches"].apply(format_matches)

st.subheader("Tabelle")
st.dataframe(base_df, use_container_width=True, height=350)

st.subheader("Manuelle Auswahl")
selections = []
for idx, row in df.iterrows():
	options = [m.get("material", "") for m in row.get("top_k_matches", [])]
	default = 0 if options else None
	choice = st.selectbox(
		f"{row.get('Name','')} | {row.get('GUID','')}",
		options=options,
		index=default,
		key=f"select_{idx}",
		placeholder="Kein Match verfügbar" if not options else None,
	)
	selections.append(choice)

result_df = base_df.copy()
result_df["selected_match"] = selections

st.subheader("Auswahl-Ergebnis")
st.dataframe(result_df, use_container_width=True, height=300)

csv = result_df.to_csv(index=False).encode("utf-8")
st.download_button("Auswahl als CSV herunterladen", data=csv, file_name="selected_matches.csv", mime="text/csv")