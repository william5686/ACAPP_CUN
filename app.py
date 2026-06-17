import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Comparador de ACA's", layout="wide")

COLS_NUM = ["Porcentaje Ocupacion Aula", "Capacidad", "Num_inscritos", "Inscritos_neto"]
COL_KEY = "Id_grupo"
COL_AREA = "Nom_unidad"

st.title("📊 Comparador de ACA's Consolidados")
st.caption("Carga el Excel consolidado (una hoja por fecha) y compara dos cortes por área.")

uploaded = st.file_uploader("Sube el archivo ACA (.xlsx)", type=["xlsx"])

if "data" not in st.session_state:
    st.session_state.data = None
    st.session_state.sheet_names = []


@st.cache_data(show_spinner=False)
def load_excel(file_bytes):
    xls = pd.ExcelFile(file_bytes)
    sheets = {}
    for name in xls.sheet_names:
        df = xls.parse(name)
        for c in COLS_NUM:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        sheets[name] = df
    return sheets


if uploaded is not None:
    sheets = load_excel(uploaded)
    st.session_state.data = sheets
    st.session_state.sheet_names = list(sheets.keys())
    st.success(f"Archivo cargado: {len(sheets)} fechas detectadas ({', '.join(sheets.keys())})")

if st.session_state.data:
    sheets = st.session_state.data
    names = st.session_state.sheet_names

    col1, col2, col3 = st.columns(3)
    with col1:
        fecha_1 = st.selectbox("Fecha 1 (base)", names, index=0)
    with col2:
        fecha_2 = st.selectbox("Fecha 2 (comparar contra)", names, index=len(names) - 1)
    with col3:
        df_ref = sheets[fecha_1]
        areas = ["(Todas las áreas)"] + sorted(df_ref[COL_AREA].dropna().unique().tolist())
        area_sel = st.selectbox("Área (Nom_unidad)", areas, index=0)

    if fecha_1 == fecha_2:
        st.warning("Selecciona dos fechas distintas para comparar.")
        st.stop()

    df1 = sheets[fecha_1].copy()
    df2 = sheets[fecha_2].copy()

    if area_sel != "(Todas las áreas)":
        df1 = df1[df1[COL_AREA] == area_sel]
        df2 = df2[df2[COL_AREA] == area_sel]

    # Agregar por Id_grupo en caso de filas repetidas (ej. una fila por inscrito)
    agg_cols = {c: "first" for c in df1.columns if c not in COLS_NUM + [COL_KEY]}
    agg_cols.update({c: "max" for c in COLS_NUM if c in df1.columns})

    g1 = df1.groupby(COL_KEY, as_index=False).agg(agg_cols)
    g2 = df2.groupby(COL_KEY, as_index=False).agg(agg_cols)

    ids1 = set(g1[COL_KEY])
    ids2 = set(g2[COL_KEY])

    nuevos = ids2 - ids1
    desaparecidos = ids1 - ids2
    comunes = ids1 & ids2

    st.divider()
    st.subheader(f"Resumen: {fecha_1} → {fecha_2}" + (f"  ·  Área: {area_sel}" if area_sel != "(Todas las áreas)" else ""))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Grupos en común", len(comunes))
    m2.metric("Grupos nuevos", len(nuevos))
    m3.metric("Grupos que desaparecieron", len(desaparecidos))
    m4.metric("Total grupos (fecha 2)", len(ids2))

    # Totales agregados
    st.markdown("**Totales agregados (sobre grupos en común)**")
    base = g1[g1[COL_KEY].isin(comunes)].set_index(COL_KEY)
    comp = g2[g2[COL_KEY].isin(comunes)].set_index(COL_KEY)

    tot_cols = st.columns(len(COLS_NUM))
    for i, c in enumerate(COLS_NUM):
        if c in base.columns:
            t1 = base[c].sum()
            t2 = comp[c].sum()
            delta = t2 - t1
            tot_cols[i].metric(c, f"{t2:,.1f}", f"{delta:+,.1f}")

    st.divider()
    st.subheader("Detalle por grupo (cambios)")

    merged = base[COLS_NUM + ["Nom_materia", COL_AREA, "Nom_sede"]].add_suffix("_1").join(
        comp[COLS_NUM + ["Nom_materia", COL_AREA, "Nom_sede"]].add_suffix("_2"),
        how="inner"
    )

    for c in COLS_NUM:
        merged[f"{c}_delta"] = merged[f"{c}_2"] - merged[f"{c}_1"]

    show_only_changes = st.checkbox("Mostrar solo grupos con cambios", value=True)

    delta_cols = [f"{c}_delta" for c in COLS_NUM]
    if show_only_changes:
        mask = (merged[delta_cols].fillna(0) != 0).any(axis=1)
        view = merged[mask]
    else:
        view = merged

    display_cols = [f"Nom_materia_2", f"{COL_AREA}_2", "Nom_sede_2"] + \
        [item for c in COLS_NUM for item in (f"{c}_1", f"{c}_2", f"{c}_delta")]

    view_display = view.reset_index()[[COL_KEY] + display_cols]
    view_display.columns = [COL_KEY, "Materia", "Área", "Sede"] + \
        [item for c in COLS_NUM for item in (f"{c} ({fecha_1})", f"{c} ({fecha_2})", f"{c} (Δ)")]

    st.dataframe(view_display, use_container_width=True, height=450)

    csv = view_display.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar comparación (CSV)", csv, file_name=f"comparacion_{fecha_1}_vs_{fecha_2}.csv", mime="text/csv")

    if nuevos:
        with st.expander(f"Ver grupos nuevos ({len(nuevos)})"):
            st.dataframe(g2[g2[COL_KEY].isin(nuevos)], use_container_width=True)

    if desaparecidos:
        with st.expander(f"Ver grupos que desaparecieron ({len(desaparecidos)})"):
            st.dataframe(g1[g1[COL_KEY].isin(desaparecidos)], use_container_width=True)

else:
    st.info("Sube un archivo .xlsx para comenzar.")
