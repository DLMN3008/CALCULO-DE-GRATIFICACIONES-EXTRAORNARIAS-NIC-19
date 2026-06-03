# ==========================================================
# NIC 19 - GRATIFICACION POR TIEMPO DE SERVICIO
# PARTE 1 CORREGIDA
# ==========================================================

import streamlit as st
import pandas as pd
import numpy as np

from datetime import datetime
from datetime import date

import plotly.express as px
import plotly.graph_objects as go

from io import BytesIO

# ==========================================================
# CONFIGURACION
# ==========================================================

st.set_page_config(
    page_title="NIC 19 - Sistema Actuarial",
    page_icon="📊",
    layout="wide"
)

# ==========================================================
# PARAMETROS GENERALES
# ==========================================================

FECHA_VALORACION = datetime(
    2025,
    12,
    31
)

# ==========================================================
# FUNCIONES FINANCIERAS
# ==========================================================

def valor_presente(
    flujo_futuro,
    tasa,
    anios
):

    if anios <= 0:
        return flujo_futuro

    return flujo_futuro / (
        (1 + tasa) ** anios
    )

# ----------------------------------------------------------

def sueldo_proyectado(
    sueldo,
    incremento,
    anios
):

    if anios <= 0:
        return sueldo

    return sueldo * (
        (1 + incremento) ** anios
    )

# ==========================================================
# FECHAS
# ==========================================================

def calcular_edad(
    fecha_nacimiento
):

    if pd.isna(
        fecha_nacimiento
    ):
        return np.nan

    return (
        FECHA_VALORACION -
        fecha_nacimiento
    ).days / 365.25

# ----------------------------------------------------------

def calcular_antiguedad(
    fecha_ingreso
):

    if pd.isna(
        fecha_ingreso
    ):
        return np.nan

    return (
        FECHA_VALORACION -
        fecha_ingreso
    ).days / 365.25

# ==========================================================
# CARGA DE PARAMETROS
# VERSION ROBUSTA
# ==========================================================

def cargar_parametros(
    df_param
):

    parametros = {}

    # --------------------------------------------
    # LIMPIEZA
    # --------------------------------------------

    df_param = df_param.copy()

    df_param = df_param.fillna("")

    # --------------------------------------------
    # BUSCAR FILA DE SINDICATOS
    # --------------------------------------------

    fila_sindicatos = None

    for fila in range(
        min(
            10,
            len(df_param)
        )
    ):

        fila_texto = " ".join(
            df_param.iloc[fila]
            .astype(str)
            .tolist()
        ).upper()

        if (
            "SITE" in fila_texto
            or
            "SITECORPAC" in fila_texto
            or
            "SITPRUCOR" in fila_texto
            or
            "SINEACOR" in fila_texto
            or
            "SIPEACOR" in fila_texto
        ):

            fila_sindicatos = fila
            break

    if fila_sindicatos is None:

        raise Exception(
            "No se encontró la fila de sindicatos en PARAMETROS."
        )

    # --------------------------------------------
    # LEER SINDICATOS
    # --------------------------------------------

    sindicatos = (
        df_param
        .iloc[
            fila_sindicatos,
            2:
        ]
        .astype(str)
        .str.strip()
        .tolist()
    )

    sindicatos = [

        s

        for s in sindicatos

        if s != ""
        and s.lower() != "nan"

    ]

    # --------------------------------------------
    # CREAR DICCIONARIO
    # --------------------------------------------

    for sindicato in sindicatos:

        parametros[
            sindicato
        ] = {}

    # --------------------------------------------
    # LEER HITOS
    # --------------------------------------------

    for fila in range(

        fila_sindicatos + 1,

        len(df_param)

    ):

        texto = str(
            df_param.iloc[
                fila,
                1
            ]
        ).upper()

        if "AÑOS" not in texto:
            continue

        try:

            anio = int(

                texto
                .replace(
                    "AÑOS",
                    ""
                )
                .strip()

            )

        except:

            continue

        # ----------------------------------------

        for idx,sindicato in enumerate(
            sindicatos
        ):

            try:

                factor = df_param.iloc[
                    fila,
                    idx + 2
                ]

                if (
                    factor == ""
                    or
                    pd.isna(factor)
                ):
                    continue

                parametros[
                    sindicato
                ][anio] = factor

            except:

                continue

    return parametros

# ==========================================================
# VALIDACIONES
# ==========================================================

def validar_base(
    base,
    parametros
):

    errores = []

    columnas = [

        "CODIGO DEL TRABAJADOR",

        "NOMBRES",

        "SINDICATO",

        "FECHA DE INGRESO",

        "FECHA DE NACIMIENTO",

        "SUELDO BASICO"

    ]

    for col in columnas:

        if col not in base.columns:

            errores.append(
                f"Falta columna: {col}"
            )

    if len(errores) > 0:

        return errores

    # --------------------------------------------

    for i,row in base.iterrows():

        sindicato = str(
            row["SINDICATO"]
        ).strip()

        if sindicato not in parametros:

            errores.append(
                f"Fila {i+1}: sindicato no parametrizado ({sindicato})"
            )

    # --------------------------------------------

    for i,row in base.iterrows():

        try:

            sueldo = float(
                row[
                    "SUELDO BASICO"
                ]
            )

            if sueldo <= 0:

                errores.append(
                    f"Fila {i+1}: sueldo <= 0"
                )

        except:

            errores.append(
                f"Fila {i+1}: sueldo inválido"
            )

    # --------------------------------------------

    duplicados = (

        base[
            "CODIGO DEL TRABAJADOR"
        ]

        .duplicated()

        .sum()

    )

    if duplicados > 0:

        errores.append(
            f"Existen {duplicados} códigos duplicados"
        )

    return errores

# ==========================================================
# PUCM
# ==========================================================

def calcular_hitos_pucm(
    trabajador,
    parametros,
    tasa_descuento,
    incremento
):

    sindicato = str(
        trabajador[
            "SINDICATO"
        ]
    ).strip()

    if sindicato not in parametros:

        return pd.DataFrame()

    sueldo = float(
        trabajador[
            "SUELDO BASICO"
        ]
    )

    antiguedad = float(
        trabajador[
            "ANTIGUEDAD"
        ]
    )

    resultados = []

    for hito,factor in parametros[
        sindicato
    ].items():

        if str(factor).strip() == "-":
            continue

        if antiguedad >= hito:
            continue

        anios_faltantes = (
            hito -
            antiguedad
        )

        sueldo_futuro = (
            sueldo_proyectado(
                sueldo,
                incremento,
                anios_faltantes
            )
        )

        beneficio = (
            sueldo_futuro *
            float(factor)
        )

        vp = valor_presente(
            beneficio,
            tasa_descuento,
            anios_faltantes
        )

        dbo = (
            vp *
            (
                antiguedad /
                hito
            )
        )

        resultados.append({

            "CODIGO":
            trabajador[
                "CODIGO DEL TRABAJADOR"
            ],

            "NOMBRE":
            trabajador[
                "NOMBRES"
            ],

            "SINDICATO":
            sindicato,

            "HITO":
            hito,

            "FACTOR":
            factor,

            "BENEFICIO":
            beneficio,

            "VP":
            vp,

            "DBO":
            dbo

        })

    return pd.DataFrame(
        resultados
    )
    # ==========================================================
# CARGA DEL ARCHIVO
# ==========================================================

st.title(
    "📊 NIC 19 - Gratificación por Tiempo de Servicio"
)

st.markdown(
    """
Sistema Actuarial desarrollado bajo
NIC 19 utilizando el método PUCM
(Projected Unit Credit Method).
"""
)

archivo = st.file_uploader(
    "Seleccione archivo Excel",
    type=["xlsx"]
)

# ==========================================================
# PARAMETROS DEL MODELO
# ==========================================================

col1,col2,col3,col4 = st.columns(4)

with col1:

    fecha_val = st.date_input(
        "Fecha Valuación",
        value=date(
            2025,
            12,
            31
        )
    )

with col2:

    tasa_descuento = st.number_input(
        "Tasa Descuento",
        min_value=0.00,
        max_value=0.20,
        value=0.07,
        step=0.005,
        format="%.3f"
    )

with col3:

    incremento_salarial = st.number_input(
        "Incremento Salarial",
        min_value=0.00,
        max_value=0.20,
        value=0.03,
        step=0.005,
        format="%.3f"
    )

with col4:

    edad_jubilacion = st.number_input(
        "Edad Jubilación",
        min_value=55,
        max_value=90,
        value=70
    )

# ==========================================================
# EJECUCION
# ==========================================================

if archivo:

    # ======================================================
    # LECTURA DE EXCEL
    # ======================================================

    try:

        base = pd.read_excel(
            archivo,
            sheet_name="BASE DE DATOS"
        )

        parametros_excel = pd.read_excel(
            archivo,
            sheet_name="PARAMETROS",
            header=None
        )

    except Exception as e:

        st.error(
            f"Error leyendo archivo: {e}"
        )

        st.stop()

    # ======================================================
    # LIMPIEZA COLUMNAS
    # ======================================================

    base.columns = (

        base.columns

        .astype(str)

        .str.strip()

    )

    # ======================================================
    # DIAGNOSTICO
    # ======================================================

    with st.expander(
        "Vista previa hoja PARAMETROS"
    ):

        st.dataframe(
            parametros_excel.head(15),
            use_container_width=True
        )

    # ======================================================
    # PARAMETROS
    # ======================================================

    try:

        parametros = cargar_parametros(
            parametros_excel
        )

    except Exception as e:

        st.error(
            f"Error cargando parámetros: {e}"
        )

        st.stop()

    # ======================================================
    # PARAMETROS LEIDOS
    # ======================================================

    with st.expander(
        "Parámetros detectados"
    ):

        st.json(
            parametros
        )

    if len(parametros) == 0:

        st.error(
            """
            No se encontraron
            sindicatos válidos.
            """
        )

        st.stop()

    # ======================================================
    # FECHAS
    # ======================================================

    try:

        base[
            "FECHA DE INGRESO"
        ] = pd.to_datetime(

            base[
                "FECHA DE INGRESO"
            ],

            errors="coerce"

        )

        base[
            "FECHA DE NACIMIENTO"
        ] = pd.to_datetime(

            base[
                "FECHA DE NACIMIENTO"
            ],

            errors="coerce"

        )

    except Exception as e:

        st.error(
            f"Error convirtiendo fechas: {e}"
        )

        st.stop()

    # ======================================================
    # EDAD Y ANTIGUEDAD
    # ======================================================

    base[
        "ANTIGUEDAD"
    ] = (

        base[
            "FECHA DE INGRESO"
        ]

        .apply(
            calcular_antiguedad
        )

    )

    base[
        "EDAD"
    ] = (

        base[
            "FECHA DE NACIMIENTO"
        ]

        .apply(
            calcular_edad
        )

    )

    # ======================================================
    # VALIDACIONES
    # ======================================================

    errores = validar_base(

        base,

        parametros

    )

    if len(errores) > 0:

        st.warning(
            f"Se detectaron {len(errores)} observaciones."
        )

        with st.expander(
            "Detalle observaciones"
        ):

            st.dataframe(

                pd.DataFrame({

                    "Observación":
                    errores

                }),

                use_container_width=True

            )

    # ======================================================
    # MOTOR ACTUARIAL
    # ======================================================

    st.info(
        "Calculando obligaciones actuariales..."
    )

    barra = st.progress(0)

    flujos = []

    total_registros = len(base)

    for i,row in base.iterrows():

        try:

            resultado = (

                calcular_hitos_pucm(

                    trabajador=row,

                    parametros=parametros,

                    tasa_descuento=tasa_descuento,

                    incremento=incremento_salarial

                )

            )

            if not resultado.empty:

                flujos.append(
                    resultado
                )

        except Exception as e:

            st.warning(

                f"Error trabajador "

                f"{row.get('CODIGO DEL TRABAJADOR','')} : "

                f"{e}"

            )

        barra.progress(
            (i + 1)
            /
            total_registros
        )

    barra.empty()

    # ======================================================
    # VALIDAR RESULTADOS
    # ======================================================

    if len(flujos) == 0:

        st.error(
            """
            No se generaron flujos actuariales.
            """
        )

        st.stop()

    # ======================================================
    # FLUJOS
    # ======================================================

    df_flujos = pd.concat(

        flujos,

        ignore_index=True

    )

    # ======================================================
    # RESUMEN TRABAJADOR
    # ======================================================

    dbo_trabajador = (

        df_flujos

        .groupby(

            [

                "CODIGO",

                "NOMBRE",

                "SINDICATO"

            ]

        )

        .agg({

            "BENEFICIO":"sum",

            "VP":"sum",

            "DBO":"sum"

        })

        .reset_index()

    )

    dbo_trabajador.rename(

        columns={

            "BENEFICIO":
            "BENEFICIO_TOTAL",

            "VP":
            "VP_TOTAL",

            "DBO":
            "DBO_TOTAL"

        },

        inplace=True

    )

    # ======================================================
    # SERVICE COST
    # ======================================================

    dbo_trabajador[
        "SERVICE_COST"
    ] = (

        dbo_trabajador[
            "DBO_TOTAL"
        ]
        /
        edad_jubilacion

    )

    # ======================================================
    # INTEREST COST
    # ======================================================

    dbo_trabajador[
        "INTEREST_COST"
    ] = (

        dbo_trabajador[
            "DBO_TOTAL"
        ]
        *
        tasa_descuento

    )

    # ======================================================
    # GASTO NIC 19
    # ======================================================

    dbo_trabajador[
        "GASTO_NIC19"
    ] = (

        dbo_trabajador[
            "SERVICE_COST"
        ]
        +
        dbo_trabajador[
            "INTEREST_COST"
        ]

    )

    # ======================================================
    # KPI GLOBALES
    # ======================================================

    TOTAL_DBO = (

        dbo_trabajador[
            "DBO_TOTAL"
        ].sum()

    )

    TOTAL_VP = (

        dbo_trabajador[
            "VP_TOTAL"
        ].sum()

    )

    TOTAL_BENEFICIO = (

        dbo_trabajador[
            "BENEFICIO_TOTAL"
        ].sum()

    )

    TOTAL_SERVICE = (

        dbo_trabajador[
            "SERVICE_COST"
        ].sum()

    )

    TOTAL_INTEREST = (

        dbo_trabajador[
            "INTEREST_COST"
        ].sum()

    )

    TOTAL_GASTO = (

        dbo_trabajador[
            "GASTO_NIC19"
        ].sum()

    )

    # ======================================================
    # SENSIBILIDAD
    # ======================================================

    sensibilidad = []

    for tasa in [

        0.06,

        0.07,

        0.08

    ]:

        dbo_sens = 0

        for _,fila in df_flujos.iterrows():

            hito = fila["HITO"]

            dbo_sens += (

                fila["BENEFICIO"]

                /

                ((1 + tasa) ** hito)

            )

        sensibilidad.append({

            "TASA": tasa,

            "DBO": dbo_sens

        })

    sensibilidad = pd.DataFrame(
        sensibilidad
    )

    st.success(
        "Cálculo actuarial finalizado."
    )
    # ==========================================================
# KPIs EJECUTIVOS
# ==========================================================

st.markdown("---")

st.header(
    "📊 Dashboard Ejecutivo NIC 19"
)

c1,c2,c3,c4,c5,c6 = st.columns(6)

c1.metric(
    "DBO Total",
    f"S/ {TOTAL_DBO:,.0f}"
)

c2.metric(
    "Valor Presente",
    f"S/ {TOTAL_VP:,.0f}"
)

c3.metric(
    "Beneficio Futuro",
    f"S/ {TOTAL_BENEFICIO:,.0f}"
)

c4.metric(
    "Service Cost",
    f"S/ {TOTAL_SERVICE:,.0f}"
)

c5.metric(
    "Interest Cost",
    f"S/ {TOTAL_INTEREST:,.0f}"
)

c6.metric(
    "Gasto NIC19",
    f"S/ {TOTAL_GASTO:,.0f}"
)

# ==========================================================
# TABS
# ==========================================================

tab1,tab2,tab3,tab4,tab5 = st.tabs([

    "📈 Dashboard",

    "📋 Detalle Actuarial",

    "📊 Sensibilidad",

    "🛡️ Calidad Datos",

    "📖 Glosario"

])

# ==========================================================
# TAB DASHBOARD
# ==========================================================

with tab1:

    st.subheader(
        "Indicadores Estratégicos"
    )

    # ------------------------------------------------------
    # PASIVO POR SINDICATO
    # ------------------------------------------------------

    sindicato_dbo = (

        dbo_trabajador

        .groupby(
            "SINDICATO"
        )["DBO_TOTAL"]

        .sum()

        .reset_index()

    )

    fig1 = px.bar(

        sindicato_dbo,

        x="SINDICATO",

        y="DBO_TOTAL",

        text_auto=".2s",

        title="Pasivo Actuarial por Sindicato"

    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # ------------------------------------------------------
    # TOP 20
    # ------------------------------------------------------

    top20 = (

        dbo_trabajador

        .nlargest(
            20,
            "DBO_TOTAL"
        )

    )

    fig2 = px.bar(

        top20,

        x="NOMBRE",

        y="DBO_TOTAL",

        title="Top 20 Trabajadores"

    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # ------------------------------------------------------
    # EDAD
    # ------------------------------------------------------

    fig3 = px.histogram(

        base,

        x="EDAD",

        nbins=20,

        title="Distribución de Edad"

    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # ------------------------------------------------------
    # ANTIGUEDAD
    # ------------------------------------------------------

    fig4 = px.histogram(

        base,

        x="ANTIGUEDAD",

        nbins=20,

        title="Distribución de Antigüedad"

    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    # ------------------------------------------------------
    # SUNBURST
    # ------------------------------------------------------

    if len(dbo_trabajador) > 0:

        st.subheader(
            "Sunburst Sindicato → Trabajador"
        )

        fig5 = px.sunburst(

            dbo_trabajador,

            path=[
                "SINDICATO",
                "NOMBRE"
            ],

            values="DBO_TOTAL"

        )

        st.plotly_chart(
            fig5,
            use_container_width=True
        )

    # ------------------------------------------------------
    # HEATMAP
    # ------------------------------------------------------

    if len(df_flujos) > 0:

        st.subheader(
            "Heatmap de Obligaciones"
        )

        heatmap = pd.pivot_table(

            df_flujos,

            values="DBO",

            index="SINDICATO",

            columns="HITO",

            aggfunc="sum",

            fill_value=0

        )

        fig6 = px.imshow(

            heatmap,

            text_auto=".0f",

            aspect="auto",

            title="Concentración del DBO por Hito"

        )

        st.plotly_chart(
            fig6,
            use_container_width=True
        )

    # ------------------------------------------------------
    # WATERFALL
    # ------------------------------------------------------

    st.subheader(
        "Composición del Pasivo"
    )

    fig7 = go.Figure(

        go.Waterfall(

            measure=[
                "relative",
                "relative",
                "total"
            ],

            x=[

                "Service Cost",

                "Interest Cost",

                "DBO"

            ],

            y=[

                TOTAL_SERVICE,

                TOTAL_INTEREST,

                TOTAL_DBO

            ]

        )

    )

    st.plotly_chart(
        fig7,
        use_container_width=True
    )

    # ------------------------------------------------------
    # CURVA VENCIMIENTOS
    # ------------------------------------------------------

    vencimientos = (

        df_flujos

        .groupby(
            "HITO"
        )["BENEFICIO"]

        .sum()

        .reset_index()

    )

    fig8 = px.line(

        vencimientos,

        x="HITO",

        y="BENEFICIO",

        markers=True,

        title="Curva de Beneficios Futuros"

    )

    st.plotly_chart(
        fig8,
        use_container_width=True
    )

# ==========================================================
# TAB DETALLE ACTUARIAL
# ==========================================================

with tab2:

    st.subheader(
        "Resumen por Trabajador"
    )

    st.dataframe(

        dbo_trabajador,

        use_container_width=True,

        height=500

    )

    st.subheader(
        "Flujos Actuariales"
    )

    st.dataframe(

        df_flujos,

        use_container_width=True,

        height=500

    )

# ==========================================================
# TAB SENSIBILIDAD
# ==========================================================

with tab3:

    st.subheader(
        "Análisis de Sensibilidad"
    )

    fig9 = px.line(

        sensibilidad,

        x="TASA",

        y="DBO",

        markers=True,

        title="Impacto de la Tasa de Descuento"

    )

    st.plotly_chart(
        fig9,
        use_container_width=True
    )

    st.dataframe(

        sensibilidad,

        use_container_width=True

    )

# ==========================================================
# TAB CALIDAD DE DATOS
# ==========================================================

with tab4:

    st.subheader(
        "Control de Calidad"
    )

    total_registros = len(base)

    total_sindicatos = (
        base["SINDICATO"]
        .nunique()
    )

    total_sedes = (
        base["SEDES"]
        .nunique()
        if "SEDES" in base.columns
        else 0
    )

    q1,q2,q3 = st.columns(3)

    q1.metric(
        "Trabajadores",
        total_registros
    )

    q2.metric(
        "Sindicatos",
        total_sindicatos
    )

    q3.metric(
        "Sedes",
        total_sedes
    )
    # ==========================================================
# VALIDACIONES DETALLADAS
# ==========================================================

    validaciones = []

    # ------------------------------------------------------

    sueldos_cero = len(

        base[
            base["SUELDO BASICO"] <= 0
        ]

    )

    validaciones.append([

        "Sueldos <= 0",

        sueldos_cero

    ])

    # ------------------------------------------------------

    edades_invalidas = len(

        base[
            base["EDAD"] < 18
        ]

    )

    validaciones.append([

        "Edad menor a 18",

        edades_invalidas

    ])

    # ------------------------------------------------------

    jubilados = len(

        base[
            base["EDAD"] >= edad_jubilacion
        ]

    )

    validaciones.append([

        "Edad >= Jubilación",

        jubilados

    ])

    # ------------------------------------------------------

    if (
        "CODIGO DEL TRABAJADOR"
        in base.columns
    ):

        duplicados = (

            base[
                "CODIGO DEL TRABAJADOR"
            ]

            .duplicated()

            .sum()

        )

    else:

        duplicados = 0

    validaciones.append([

        "Códigos duplicados",

        duplicados

    ])

    # ------------------------------------------------------

    sindicatos_sin_parametro = 0

    for sindicato in (

        base[
            "SINDICATO"
        ]

        .astype(str)

        .str.strip()

        .unique()

    ):

        if sindicato not in parametros:

            sindicatos_sin_parametro += 1

    validaciones.append([

        "Sindicatos sin parametrizar",

        sindicatos_sin_parametro

    ])

    # ------------------------------------------------------

    df_validaciones = pd.DataFrame(

        validaciones,

        columns=[

            "Validación",

            "Cantidad"

        ]

    )

    st.dataframe(

        df_validaciones,

        use_container_width=True

    )

    if (

        df_validaciones[
            "Cantidad"
        ].sum()

        == 0

    ):

        st.success(
            "No se encontraron observaciones."
        )

    else:

        st.warning(
            "Existen observaciones por revisar."
        )

# ==========================================================
# GLOSARIO NIC 19
# ==========================================================

with tab5:

    glosario = pd.DataFrame({

        "Término":[

            "DBO",

            "PUCM",

            "Valor Presente",

            "Service Cost",

            "Interest Cost",

            "Beneficio Futuro",

            "Hito",

            "Sensibilidad",

            "Ganancia/Pérdida Actuarial"

        ],

        "Definición":[

            "Defined Benefit Obligation.",

            "Projected Unit Credit Method.",

            "Valor descontado de un flujo futuro.",

            "Costo del servicio del período.",

            "Costo financiero de la obligación.",

            "Beneficio proyectado al momento del pago.",

            "Año de servicio que genera beneficio.",

            "Impacto de cambios en hipótesis.",

            "Variación actuarial reconocida en OCI."

        ]

    })

    st.subheader(
        "Glosario NIC 19"
    )

    st.dataframe(

        glosario,

        use_container_width=True

    )

    # ------------------------------------------------------

    st.subheader(
        "Leyenda del Dashboard"
    )

    st.markdown("""

### DBO
Obligación actuarial acumulada.

### Valor Presente
Valor actual de pagos futuros.

### Service Cost
Costo generado por servicios del período.

### Interest Cost
Costo financiero por actualización del pasivo.

### Sunburst
Composición Sindicato → Trabajador.

### Heatmap
Distribución del DBO por hitos.

### Waterfall
Composición del pasivo actuarial.

### Curva de Vencimientos
Pagos futuros esperados.

### Sensibilidad
Impacto por cambios en la tasa de descuento.

""")

# ==========================================================
# EXPORTACION EXCEL
# ==========================================================

st.markdown("---")

st.subheader(
    "Exportación de Resultados"
)

salida_excel = BytesIO()

try:

    with pd.ExcelWriter(

        salida_excel,

        engine="openpyxl"

    ) as writer:

        # --------------------------------------------------

        resumen = pd.DataFrame({

            "Concepto":[

                "DBO",

                "Valor Presente",

                "Beneficio Futuro",

                "Service Cost",

                "Interest Cost",

                "Gasto NIC19"

            ],

            "Monto":[

                TOTAL_DBO,

                TOTAL_VP,

                TOTAL_BENEFICIO,

                TOTAL_SERVICE,

                TOTAL_INTEREST,

                TOTAL_GASTO

            ]

        })

        resumen.to_excel(

            writer,

            sheet_name="00_RESUMEN",

            index=False

        )

        # --------------------------------------------------

        dbo_trabajador.to_excel(

            writer,

            sheet_name="01_DBO_TRABAJADOR",

            index=False

        )

        # --------------------------------------------------

        df_flujos.to_excel(

            writer,

            sheet_name="02_FLUJOS",

            index=False

        )

        # --------------------------------------------------

        sensibilidad.to_excel(

            writer,

            sheet_name="03_SENSIBILIDAD",

            index=False

        )

        # --------------------------------------------------

        df_validaciones.to_excel(

            writer,

            sheet_name="04_VALIDACIONES",

            index=False

        )

        # --------------------------------------------------

        glosario.to_excel(

            writer,

            sheet_name="05_GLOSARIO",

            index=False

        )

    st.download_button(

        label="📥 Descargar Excel NIC19",

        data=salida_excel.getvalue(),

        file_name="NIC19_RESULTADOS.xlsx",

        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    )

except Exception as e:

    st.error(
        f"Error generando Excel: {e}"
    )

# ==========================================================
# REPORTE EJECUTIVO
# ==========================================================

st.markdown("---")

st.subheader(
    "Reporte Ejecutivo"
)

texto_reporte = f"""
NIC 19 - GRATIFICACIÓN POR TIEMPO DE SERVICIO

Fecha de Valuación:
{fecha_val}

------------------------------------------------

DBO TOTAL:
S/ {TOTAL_DBO:,.2f}

VALOR PRESENTE:
S/ {TOTAL_VP:,.2f}

BENEFICIOS FUTUROS:
S/ {TOTAL_BENEFICIO:,.2f}

SERVICE COST:
S/ {TOTAL_SERVICE:,.2f}

INTEREST COST:
S/ {TOTAL_INTEREST:,.2f}

GASTO NIC19:
S/ {TOTAL_GASTO:,.2f}

------------------------------------------------

HIPÓTESIS ACTUARIALES

Tasa de descuento:
{tasa_descuento:.2%}

Incremento salarial:
{incremento_salarial:.2%}

Edad jubilación:
{edad_jubilacion}

------------------------------------------------

Sistema desarrollado bajo
NIC 19 - Projected Unit Credit Method
(PUCM)
"""

st.download_button(

    label="📄 Descargar Resumen Ejecutivo",

    data=texto_reporte,

    file_name="NIC19_REPORTE_EJECUTIVO.txt",

    mime="text/plain"

)

# ==========================================================
# FIN DEL SISTEMA
# ==========================================================

st.success(
    "Proceso actuarial completado correctamente."
)
