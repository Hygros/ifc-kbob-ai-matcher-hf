import pandas as pd
import plotly.express as px
import streamlit as st

from Dashboard.config import CHART_HEIGHT, get_available_indicator_definitions


def _normalize_group_value(value):
    if isinstance(value, (list, tuple)):
        cleaned = [str(item).strip() for item in value if item is not None and str(item).strip()]
        return " | ".join(cleaned) if cleaned else None
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _kpi_block(df: pd.DataFrame) -> None:
    total_gwp = df["gwp_kgco2eq"].sum()
    total_ubp = df["ubp"].sum()
    total_penre = df["penre_kwh_oil_eq"].sum()
    c1, c2, c3 = st.columns(3)

    def chf_thousands(value):
        return f"{int(round(value)):,}".replace(",", "'")

    c1.metric("Total Global Warming Potential", f"{chf_thousands(total_gwp)} kg CO₂ eq")
    c2.metric("Total Environmental Impact Points", f"{chf_thousands(total_ubp)} UBP")
    c3.metric("Total Primary Energy Non-Renewable", f"{chf_thousands(total_penre)} kWh oil‑eq")


def render_tab_charts(df: pd.DataFrame | None) -> None:
    if df is None or not hasattr(df, "columns"):
        st.info("Noch keine Daten.")
        return

    st.subheader("Chart Configuration")

    grouping_mode = st.selectbox(
        "Grouping Mode",
        options=["Group by Element Name", "Group by KBOB Materials", "Group by Ifc Entity"],
        index=2,
    )

    available_indicators = get_available_indicator_definitions(df)
    if not available_indicators:
        st.warning("Keine berechneten Umweltindikatoren verfügbar.")
        return

    family_options = list(dict.fromkeys([item["family"] for item in available_indicators]))
    default_family = "Umweltbelastungspunkte (UBP21)"
    family_index = family_options.index(default_family) if default_family in family_options else 0
    selected_family = st.selectbox("Indikator-Familie", options=family_options, index=family_index)

    family_indicators = [item for item in available_indicators if item["family"] == selected_family]
    indicator_options = [f"{item['label']} ({item['unit']})" for item in family_indicators]
    default_indicator_index = next(
        (idx for idx, item in enumerate(family_indicators) if item.get("phase") == "Total"),
        0,
    )
    selected_indicator_labels = st.multiselect(
        "Kennwerte",
        options=indicator_options,
        default=[indicator_options[default_indicator_index]],
    )
    if not selected_indicator_labels:
        st.info("Bitte mindestens einen Kennwert auswählen.")
        return

    selected_indicator_meta = [
        family_indicators[indicator_options.index(label)] for label in selected_indicator_labels
    ]
    selected_indicator_columns = [
        item.get("active_column") or item["column"] for item in selected_indicator_meta
    ]

    if grouping_mode == "Group by Element Name":
        col = "element_name" if "element_name" in df.columns else ("Name" if "Name" in df.columns else None)
        label = "Select Elements"
    elif grouping_mode == "Group by KBOB Materials":
        col = "kbob_material" if "kbob_material" in df.columns else None
        label = "Select KBOB materials"
    else:
        col = "ifc_entity" if "ifc_entity" in df.columns else ("IfcEntity" if "IfcEntity" in df.columns else None)
        label = "Select Ifc entities"

    if not col:
        st.warning("Für die gewählte Gruppierung ist keine passende Spalte vorhanden.")
        return

    group_col = "_group_key"
    fdf = df.copy()
    fdf[group_col] = fdf[col].apply(_normalize_group_value)
    universe = fdf[group_col].dropna().unique().tolist()

    selection = st.multiselect("Selection", options=universe, default=universe, placeholder=label)
    chart_type = st.segmented_control("Chart Type", options=["Bar", "Line", "Pie", "Bubble"], default="Bar")

    fdf = fdf[fdf[group_col].isin(selection)]

    agg_wide = fdf.groupby(group_col, dropna=False)[selected_indicator_columns].sum().reset_index()
    rename_map = {col_name: label for col_name, label in zip(selected_indicator_columns, selected_indicator_labels)}
    agg_wide = agg_wide.rename(columns=rename_map)
    agg = agg_wide.melt(
        id_vars=[group_col],
        value_vars=selected_indicator_labels,
        var_name="Kennwert",
        value_name="value",
    )
    total_value = agg["value"].sum(skipna=True)
    agg["percent"] = agg["value"].apply(
        lambda x: (float(x) / float(total_value) * 100.0) if pd.notna(x) and total_value not in [0, 0.0] else 0.0
    )
    agg["value_label"] = agg["value"].apply(
        lambda x: f"{int(round(x)):,}".replace(",", "'") if pd.notna(x) else ""
    )
    agg["percent_label"] = agg["percent"].apply(lambda x: f"{x:.1f}%")
    agg["value_percent_label"] = agg["value_label"].astype(str) + " (" + agg["percent_label"].astype(str) + ")"

    _kpi_block(fdf)

    if chart_type == "Bar":
        fig = px.bar(
            agg,
            x=group_col,
            y="value",
            color="Kennwert",
            text="value_percent_label",
            barmode="group",
            title="Environmental Impact Visualization",
        )
        fig.update_traces(texttemplate="%{text}", textposition="inside")
    elif chart_type == "Line":
        fig = px.line(
            agg,
            x=group_col,
            y="value",
            color="Kennwert",
            text="value_percent_label",
            markers=True,
            title="Environmental Impact Visualization",
        )
        fig.update_traces(textposition="top center")
    elif chart_type == "Pie":
        pie_df = agg.copy()
        if len(selected_indicator_labels) > 1:
            pie_df["Segment"] = pie_df[group_col].astype(str) + " | " + pie_df["Kennwert"].astype(str)
            fig = px.pie(
                pie_df,
                names="Segment",
                values="value",
                color="Segment",
                custom_data=["value_label"],
                title="Environmental Impact Visualization",
            )
        else:
            fig = px.pie(
                pie_df,
                names=group_col,
                values="value",
                color=group_col,
                custom_data=["value_label"],
                title="Environmental Impact Visualization",
            )
        fig.update_traces(texttemplate="%{label}<br>%{customdata[0]} (%{percent})")
    else:
        fig = px.scatter(
            agg,
            x=group_col,
            y="value",
            size="value",
            color="Kennwert",
            text="value_percent_label",
            hover_name=group_col,
            title="Environmental Impact Visualization",
        )
        fig.update_traces(textposition="top center")

    y_axis_label = selected_indicator_labels[0] if len(selected_indicator_labels) == 1 else selected_family
    fig.update_layout(xaxis_title=None, yaxis_title=y_axis_label, height=CHART_HEIGHT)
    st.plotly_chart(fig, width="stretch")

    missing_basis_col = _first_existing_column(
        df,
        ["Fehlende Berechnungsgrundlage", "fehlende_berechnungsgrundlage"],
    )
    guid_col = _first_existing_column(df, ["GUID", "guid", "GlobalId", "global_id"])
    reference_basis_col = _first_existing_column(df, ["Bezugsgröße", "Bezugsgroesse", "Bezugsgrösse", "bezugsgroesse"])
    selected_kbob_col = _first_existing_column(df, ["selected_kbob_material", "Material (KBOB)", "kbob_material"])

    if missing_basis_col and guid_col:
        table_cols = [guid_col, missing_basis_col]
        if reference_basis_col:
            table_cols.append(reference_basis_col)
        if selected_kbob_col:
            table_cols.append(selected_kbob_col)

        missing_mask = (
            df[missing_basis_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
        )
        missing_df = df.loc[missing_mask, table_cols].copy()
        st.markdown("### Nicht berechenbare Einträge")
        st.caption(
            "Für die UBP-Berechnung braucht jedes Element eine passende Bezugsgrösse. "
            "Je nach KBOB-Eintrag wird ein Volumen [m³], eine Fläche [m²] oder eine Länge [m] benötigt. "
            "Fehlt diese Grundlage, kann kein Ergebnis berechnet werden."
        )
        if not missing_df.empty:
            rename_map = {
                guid_col: "GUID",
                missing_basis_col: "Fehlende Berechnungsgrundlage",
            }
            if reference_basis_col:
                rename_map[reference_basis_col] = "Bezugsgrösse KBOB"
            if selected_kbob_col:
                rename_map[selected_kbob_col] = "Gewählter KBOB-Eintrag"
            missing_df = missing_df.rename(columns=rename_map)
            st.dataframe(missing_df, width="stretch", hide_index=True)
        else:
            st.info("Keine Einträge mit fehlender Berechnungsgrundlage gefunden.")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Export CSV", data=agg.to_csv(index=False), file_name="chart_data.csv", mime="text/csv")
    with col2:
        st.download_button("Export IFC Mapping", data=fdf.to_csv(index=False), file_name="materials_table.csv", mime="text/csv")
