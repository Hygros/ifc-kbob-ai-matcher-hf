import os

import streamlit as st


def render_header_metrics(df) -> None:
    mid, right = st.columns([1, 1])
    with mid:
        c1, c2, c3 = st.columns(3)

        if df is not None:
            num_elements = len(df)
            mat_col = "Material Ifc"
            if mat_col in df.columns:
                num_materials = df[mat_col].apply(lambda value: ", ".join(value) if isinstance(value, list) else str(value)).nunique()
            elif "Material" in df.columns:
                num_materials = df["Material"].apply(lambda value: ", ".join(value) if isinstance(value, list) else str(value)).nunique()
            else:
                num_materials = "–"
        else:
            num_elements = "–"
            num_materials = "–"

        dashboard_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        try:
            num_uploads = len([entry for entry in os.listdir(dashboard_data_dir) if entry.endswith(".jsonl")])
        except Exception:
            num_uploads = "–"

        c1.metric("Elements in current IFC", f"{num_elements}")
        c2.metric("Total Uploaded IFC-Files", f"{num_uploads}")
        c3.metric("Nr of different Materials in the IFC", f"{num_materials}")
    with right:
        pass
