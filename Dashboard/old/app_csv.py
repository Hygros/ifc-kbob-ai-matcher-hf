# app_csv.py
# Ziel: pro Element den richtigen Match aus top_k_matches wählen, Auswahl persistent in CSV speichern
# Start:  streamlit run Dashboard/app_csv.py

import json
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide", page_title="IFC Match Auswahl")

DATA_PATH = Path(r"c:\Users\wpx619\AAA_Python_MTH\Matching\Dashboard\data\Bohrpfahl_4.3.jsonl") # JSONL-Quelle
SELECTION_PATH = Path(r"c:\Users\wpx619\AAA_Python_MTH\Matching\Dashboard\auswahl.csv")     # Persistente Auswahl

@st.cache_data
def load_rows(jsonl_path: Path) -> list[dict]:
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]

def normalize(rows: list[dict]) -> pd.DataFrame:
    # relevante Spalten und Matches
    base_cols = ["IfcEntity","PredefinedType","Name","GUID","comment","Durchmesser","top_k_matches"]
    df = pd.json_normalize(rows)
    for col in base_cols:
        if col not in df.columns:
            df[col] = None
    df = df[base_cols].copy()
    df["Durchmesser"] = df["Durchmesser"].astype(str)
    return df

def load_selection_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        df = pd.read_csv(path, dtype={"GUID":"string"})
        # Schema absichern
        need_cols = ["GUID", "Material KBOB", "AI Score", "SelectedOn", "SelectedBy"]
        for c in need_cols:
            if c not in df.columns:
                df[c] = None
        return df[need_cols].copy()
    return pd.DataFrame(columns=["GUID", "Material KBOB", "AI Score", "SelectedOn", "SelectedBy"])

def save_selection_csv(path: Path, updates: pd.DataFrame):
    # pro GUID letzte Entscheidung behalten
    if path.exists():
        current = pd.read_csv(path, dtype={"GUID":"string"})
        merged = pd.concat([current, updates], ignore_index=True)
    else:
        merged = updates
    merged = merged.sort_values("SelectedOn").drop_duplicates(subset=["GUID"], keep="last")
    merged.to_csv(path, index=False)

def as_selection_dict(sel_df: pd.DataFrame) -> dict:
    # Robust: nutze "Material KBOB" falls vorhanden, sonst "SelectedMaterial"
    material_col = "Material KBOB" if "Material KBOB" in sel_df.columns else (
        "SelectedMaterial" if "SelectedMaterial" in sel_df.columns else None
    )
    if material_col is None:
        return {}
    return {r["GUID"]: r[material_col] for _, r in sel_df.iterrows()}

def get_score_lookup(matches: list[dict]) -> dict:
    return {m.get("material"): m.get("score") for m in matches or []}

# Daten laden
rows = load_rows(DATA_PATH)
base = normalize(rows)
sel_df = load_selection_csv(SELECTION_PATH)
prev_sel = as_selection_dict(sel_df)

#st.header("Manuelle Auswahl je Element")
#st.caption("Die Auswahl wird lokal in auswahl.csv gespeichert und für weitere Schritte wiederverwendet.")

# Formular verhindert Re-Runs bei jeder Auswahl
with st.form("select_form"):
    updates = []
    for _, r in base.iterrows():
        guid = r["GUID"]
        element_label = f"{r['IfcEntity']} | {r['PredefinedType']} | {r['Name']} | {r['comment']} | Ø {r['Durchmesser']}"
        # Label groß und über die volle Breite
        st.markdown(
            f"<div style='font-size: 1.1em; font-weight: bold; margin-bottom: 0.2em; text-align: left; width: 100%;'>{element_label}</div>",
            unsafe_allow_html=True
        )
        matches = r["top_k_matches"] or []
        # Optionen als "Material (Score: ...)" anzeigen
        options = [
            f"{m.get('material')} (Score: {m.get('score'):.3f})" if m.get("score") is not None else m.get("material")
            for m in matches
        ]
        material_lookup = {
            f"{m.get('material')} (Score: {m.get('score'):.3f})" if m.get("score") is not None else m.get("material"): m.get("material")
            for m in matches
        }
        scores = get_score_lookup(matches)
        # Default-Auswahl anpassen
        default_material = prev_sel.get(guid, matches[0].get("material") if matches else None)
        if matches:
            default_label = next(
                (label for label, mat in material_lookup.items() if mat == default_material),
                options[0]
            )
        else:
            default_label = "kein Vorschlag"
        
        if options:
            sel_label = st.selectbox(
                "Materialauswahl",  # Nicht-leeres Label
                options=options,
                index=(options.index(default_label) if default_label in options else 0),
                key=f"sel_{guid}",
                label_visibility="collapsed"  # Label verstecken
            )
        else:
            sel_label = st.selectbox(
                "Materialauswahl",  # Nicht-leeres Label
                options=["kein Vorschlag"],
                index=0,
                key=f"sel_{guid}",
                label_visibility="collapsed"  # Label verstecken
            )
        sel_material = material_lookup.get(sel_label) if options else None
        updates.append({
            "GUID": guid,
            "Material KBOB": sel_material,
            "AI Score": scores.get(sel_material) if options else None
        })

    submitted = st.form_submit_button("Auswahl speichern")

if submitted:
    out = pd.DataFrame(updates)
    out["SelectedOn"] = pd.Timestamp.utcnow().isoformat()
    # Optional: Benutzername, falls Auth davor gelöst ist
    out["SelectedBy"] = "unbekannt"
    # Spaltennamen anpassen für Speicherung
    out = out.rename(columns={"Material KBOB": "Material KBOB", "AI Score": "AI Score"})
    save_selection_csv(SELECTION_PATH, out)
    st.success("Auswahl gespeichert")

# Ergebnisansicht und Verfügbarkeit für weitere Schritte
sel_df = load_selection_csv(SELECTION_PATH)
# Merge mit neuen Spaltennamen, robust gegen fehlende Spalten
merge_cols = [c for c in ["GUID", "Material KBOB", "AI Score"] if c in sel_df.columns]
merged = base.merge(sel_df[merge_cols], on="GUID", how="left")

st.subheader("Übersicht")
# Spalte "comment" umbenennen, "GUID" ausblenden, Index ausblenden
uebersicht = merged.rename(columns={"comment": "Beschrieb"})
st.dataframe(
    uebersicht[["IfcEntity", "PredefinedType", "Name", "Beschrieb", "Durchmesser", "Material KBOB", "AI Score"]],
    hide_index=True,
    width="stretch"
)

st.subheader("Weitere Schritte, Beispiel: Aggregation nach gewähltem Material")
agg = merged.groupby("Material KBOB", dropna=False).agg(
    Anzahl=("GUID", "count")
).reset_index()
st.dataframe(agg, width="stretch")