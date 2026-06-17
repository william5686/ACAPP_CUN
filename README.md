# Comparador de ACA's Consolidados

App en Streamlit para comparar dos cortes (fechas) de los archivos "ACA Consolidado"
sin tener que filtrar manualmente en Excel.

## ¿Qué hace?

1. Subes el Excel consolidado (el archivo donde cada hoja es una fecha, ej. "01 Junio", "02 Junio", etc.).
2. Eliges **Fecha 1** y **Fecha 2** a comparar.
3. Opcionalmente filtras por **Área** (columna `Nom_unidad`, ej. "CIENCIAS BÁSICAS VIRTUAL").
4. La app te muestra:
   - Grupos nuevos (aparecieron en la fecha 2 pero no en la fecha 1).
   - Grupos que desaparecieron.
   - Cambios en **Ocupación de aula**, **Capacidad**, **Inscritos** e **Inscritos neto** por grupo.
   - Totales agregados con la diferencia (delta) entre las dos fechas.
   - Botón para descargar la comparación en CSV.

## Cómo correrlo localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abrirá en el navegador en `http://localhost:8501`.

## Cómo subirlo a GitHub y desplegarlo gratis (Streamlit Community Cloud)

1. Crea un repositorio nuevo en tu GitHub (puede ser privado) y sube estos archivos
   (`app.py`, `requirements.txt`, este `README.md`).
2. Ve a [share.streamlit.io](https://share.streamlit.io), conecta tu cuenta de GitHub.
3. Selecciona el repositorio y el archivo `app.py` como punto de entrada.
4. Streamlit Cloud instalará las dependencias del `requirements.txt` y te dará una URL pública
   (o restringida, según configuración) para usar la app desde cualquier navegador, sin instalar nada.

Cada vez que llegue el ACA del día, simplemente lo subes en la app y seleccionas las fechas
que quieras comparar — no hace falta tocar el Excel original.

## Estructura esperada del archivo

- Cada hoja del Excel = una fecha (un "ACA").
- Columna clave por grupo: `Id_grupo`.
- Columna de área/programa: `Nom_unidad`.
- Columnas numéricas comparadas: `Porcentaje Ocupacion Aula`, `Capacidad`, `Num_inscritos`, `Inscritos_neto`.

Si en el futuro cambian los nombres de columnas, ajusta las constantes `COLS_NUM`, `COL_KEY`
y `COL_AREA` al inicio de `app.py`.

## Notas

- Si una hoja tiene varias filas por el mismo `Id_grupo` (p. ej. una fila por estudiante inscrito),
  la app las agrupa automáticamente tomando el valor máximo de las columnas numéricas y el primer
  valor de las columnas descriptivas (materia, sede, etc.) por grupo.
- El procesamiento del archivo se cachea (`st.cache_data`) para que cambiar de fecha o área sea
  instantáneo sin tener que releer el Excel completo.
