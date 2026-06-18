import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Comparador de ACA's", layout="wide")

COLS_NUM = ["Porcentaje Ocupacion Aula", "Capacidad", "Num_inscritos", "Inscritos_neto"]
COL_KEY = "Id_grupo"
COL_PERIODO = "Cod_periodo"
COL_AREA = "Nom_unidad"
COL_MATERIA = "Nom_materia"
COLS_DETALLE = ["Num_grupo", "Nom_sede", "Nom_aula", "Dia", "Hora_inicial", "Hora_final", "Nom_largo"]

st.title("📊 Comparador de ACA's Consolidados")
st.caption("Carga el Excel consolidado (una hoja por fecha) y compara dos cortes filtrando por período, área y asignatura.")

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


def aggregate(df):
    """Agrupa por Id_grupo en caso de filas repetidas (ej. una fila por inscrito)."""
    agg_cols = {c: "first" for c in df.columns if c not in COLS_NUM + [COL_KEY]}
    agg_cols.update({c: "max" for c in COLS_NUM if c in df.columns})
    return df.groupby(COL_KEY, as_index=False).agg(agg_cols)


if uploaded is not None:
    sheets = load_excel(uploaded)
    st.session_state.data = sheets
    st.session_state.sheet_names = list(sheets.keys())
    st.success(f"Archivo cargado: {len(sheets)} fechas detectadas ({', '.join(sheets.keys())})")

if st.session_state.data:
    sheets = st.session_state.data
    names = st.session_state.sheet_names

    col1, col2 = st.columns(2)
    with col1:
        fecha_1 = st.selectbox("Fecha 1 (base)", names, index=0)
    with col2:
        fecha_2 = st.selectbox("Fecha 2 (comparar contra)", names, index=len(names) - 1)

    if fecha_1 == fecha_2:
        st.warning("Selecciona dos fechas distintas para comparar.")
        st.stop()

    df1_full = sheets[fecha_1].copy()
    df2_full = sheets[fecha_2].copy()

    # Universo de referencia para construir las listas de filtros: unión de ambas fechas
    df_ref = pd.concat([df1_full, df2_full], ignore_index=True)

    st.divider()
    st.markdown("**Filtros**: Período → Área (en cascada) y Asignatura (todas, independiente)")
    f1, f2, f3 = st.columns(3)

    with f1:
        periodos = sorted(df_ref[COL_PERIODO].dropna().unique().tolist())
        periodo_sel = st.selectbox("1️⃣ Período (Cod_periodo)", periodos)

    df_ref_periodo = df_ref[df_ref[COL_PERIODO] == periodo_sel]

    with f2:
        areas = sorted(df_ref_periodo[COL_AREA].dropna().unique().tolist())
        area_sel = st.selectbox("2️⃣ Área (Nom_unidad)", areas)

    with f3:
        # A diferencia de Área (que depende del Período), Asignatura siempre muestra
        # TODAS las materias del archivo, sin que el Período/Área la filtren primero.
        materias = sorted(df_ref[COL_MATERIA].dropna().unique().tolist())
        materia_sel = st.selectbox("3️⃣ Asignatura (Nom_materia)", materias)

    # Aplicar los 3 filtros a cada fecha
    def filtrar(df):
        return df[
            (df[COL_PERIODO] == periodo_sel)
            & (df[COL_AREA] == area_sel)
            & (df[COL_MATERIA] == materia_sel)
        ]

    df1 = filtrar(df1_full)
    df2 = filtrar(df2_full)

    g1 = aggregate(df1)
    g2 = aggregate(df2)

    ids1 = set(g1[COL_KEY])
    ids2 = set(g2[COL_KEY])

    nuevos = ids2 - ids1
    desaparecidos = ids1 - ids2
    comunes = ids1 & ids2

    st.divider()
    st.subheader(f"{materia_sel}")
    st.caption(f"{area_sel}  ·  Período {periodo_sel}  ·  {fecha_1} → {fecha_2}")

    if len(ids1) == 0 and len(ids2) == 0:
        st.warning("No hay grupos para esta combinación de período, área y asignatura en ninguna de las dos fechas.")
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Grupos en común", len(comunes))
    m2.metric("Grupos nuevos", len(nuevos))
    m3.metric("Grupos que desaparecieron", len(desaparecidos))
    m4.metric("Total grupos (fecha 2)", len(ids2))

    base = g1.set_index(COL_KEY)
    comp = g2.set_index(COL_KEY)

    # Totales agregados (inscritos e inscritos neto) sobre grupos en comun
    st.markdown("**Totales — Inscritos e Inscritos neto (grupos en común)**")
    foco_cols = ["Num_inscritos", "Inscritos_neto"]
    tot_cols = st.columns(len(foco_cols))
    for i, c in enumerate(foco_cols):
        t1 = base.loc[list(comunes), c].sum() if comunes else 0
        t2 = comp.loc[list(comunes), c].sum() if comunes else 0
        delta = t2 - t1
        tot_cols[i].metric(c, f"{t2:,.0f}", f"{delta:+,.0f}")

    st.divider()
    st.subheader("Detalle por grupo")

    cols_join = ["Num_inscritos", "Inscritos_neto"] + COLS_DETALLE
    cols_join_1 = [c for c in cols_join if c in base.columns]
    cols_join_2 = [c for c in cols_join if c in comp.columns]

    if comunes:
        merged = base.loc[list(comunes), cols_join_1].add_suffix("_1").join(
            comp.loc[list(comunes), cols_join_2].add_suffix("_2"),
            how="inner"
        )
        merged["Num_inscritos_delta"] = merged["Num_inscritos_2"] - merged["Num_inscritos_1"]
        merged["Inscritos_neto_delta"] = merged["Inscritos_neto_2"] - merged["Inscritos_neto_1"]

        show_only_changes = st.checkbox("Mostrar solo grupos con cambios en inscritos", value=False)
        if show_only_changes:
            mask = (merged[["Num_inscritos_delta", "Inscritos_neto_delta"]].fillna(0) != 0).any(axis=1)
            view = merged[mask]
        else:
            view = merged

        display_cols = [
            "Num_grupo_2", "Nom_sede_2", "Nom_aula_2", "Dia_2", "Hora_inicial_2", "Hora_final_2",
            "Num_inscritos_1", "Num_inscritos_2", "Num_inscritos_delta",
            "Inscritos_neto_1", "Inscritos_neto_2", "Inscritos_neto_delta",
        ]
        display_cols = [c for c in display_cols if c in view.columns]

        view_display = view.reset_index()[[COL_KEY] + display_cols]
        rename_map = {
            "Num_grupo_2": "Grupo", "Nom_sede_2": "Sede", "Nom_aula_2": "Salón",
            "Dia_2": "Día", "Hora_inicial_2": "Hora inicio", "Hora_final_2": "Hora fin",
            "Num_inscritos_1": f"Inscritos ({fecha_1})", "Num_inscritos_2": f"Inscritos ({fecha_2})",
            "Num_inscritos_delta": "Inscritos (Δ)",
            "Inscritos_neto_1": f"Inscritos neto ({fecha_1})", "Inscritos_neto_2": f"Inscritos neto ({fecha_2})",
            "Inscritos_neto_delta": "Inscritos neto (Δ)",
        }
        view_display = view_display.rename(columns=rename_map)

        st.dataframe(view_display, use_container_width=True, height=420)

        csv = view_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Descargar detalle (CSV)", csv,
            file_name=f"detalle_{materia_sel[:30]}_{fecha_1}_vs_{fecha_2}.csv",
            mime="text/csv",
        )
    else:
        st.info("No hay grupos en común entre las dos fechas para esta asignatura.")

    if nuevos:
        with st.expander(f"Ver grupos nuevos ({len(nuevos)})"):
            cols_show = [c for c in [COL_KEY, "Num_grupo", "Nom_sede", "Nom_aula", "Num_inscritos", "Inscritos_neto"] if c in g2.columns]
            st.dataframe(g2[g2[COL_KEY].isin(nuevos)][cols_show], use_container_width=True)

    if desaparecidos:
        with st.expander(f"Ver grupos que desaparecieron ({len(desaparecidos)})"):
            cols_show = [c for c in [COL_KEY, "Num_grupo", "Nom_sede", "Nom_aula", "Num_inscritos", "Inscritos_neto"] if c in g1.columns]
            st.dataframe(g1[g1[COL_KEY].isin(desaparecidos)][cols_show], use_container_width=True)

else:
    st.info("Sube un archivo .xlsx para comenzar.")
