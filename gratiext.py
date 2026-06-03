# ==========================================================
# NIC 19 - GRATIFICACION POR TIEMPO DE SERVICIO
# VERSION ENTERPRISE
# PARTE 1
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
# CONFIGURACION STREAMLIT
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

TASA_DESCUENTO = 0.07

INCREMENTO_SALARIAL = 0.03

EDAD_JUBILACION = 70

# ==========================================================
# FUNCIONES FINANCIERAS
# ==========================================================

def valor_presente(
    flujo_futuro,
    tasa,
    anios
):

    return flujo_futuro / (
        (1 + tasa) ** anios
    )

# ----------------------------------------------------------

def sueldo_proyectado(
    sueldo,
    incremento,
    anios
):

    return sueldo * (
        (1 + incremento) ** anios
    )

# ==========================================================
# FUNCIONES DE FECHAS
# ==========================================================

def calcular_edad(
    fecha_nacimiento
):

    return (
        FECHA_VALORACION -
        fecha_nacimiento
    ).days / 365.25

# ----------------------------------------------------------

def calcular_antiguedad(
    fecha_ingreso
):

    return (
        FECHA_VALORACION -
        fecha_ingreso
    ).days / 365.25

# ==========================================================
# LECTURA DINAMICA PARAMETROS
# ==========================================================

def cargar_parametros(
    df_param
):

    parametros = {}

    sindicatos = (
        df_param
        .iloc[0,2:]
        .tolist()
    )

    for idx,sindicato in enumerate(
        sindicatos
    ):

        parametros[
            str(
                sindicato
            ).strip()
        ] = {}

        for fila in range(
            1,
            len(df_param)
        ):

            anio_txt = str(
                df_param.iloc[
                    fila,
                    1
                ]
            )

            if (
                "AÑOS"
                not in anio_txt
            ):
                continue

            anio = int(
                anio_txt
                .replace(
                    "AÑOS",
                    ""
                )
                .strip()
            )

            factor = (
                df_param.iloc[
                    fila,
                    idx + 2
                ]
            )

            parametros[
                sindicato
            ][anio] = factor

    return parametros

# ==========================================================
# VALIDACIONES
# ==========================================================

def validar_base(
    df,
    parametros
):

    errores = []

    columnas_obligatorias = [

        "CODIGO DEL TRABAJADOR",

        "NOMBRES",

        "SINDICATO",

        "FECHA DE INGRESO",

        "FECHA DE NACIMIENTO",

        "SUELDO BASICO"

    ]

    for col in columnas_obligatorias:

        if col not in df.columns:

            errores.append(
                f"Falta columna: {col}"
            )

    # ----------------------

    for i,row in df.iterrows():

        if pd.isna(
            row[
                "SUELDO BASICO"
            ]
        ):

            errores.append(
                f"Fila {i+1}: sueldo vacío"
            )

        elif (
            row[
                "SUELDO BASICO"
            ] <= 0
        ):

            errores.append(
                f"Fila {i+1}: sueldo <= 0"
            )

    # ----------------------

    for i,row in df.iterrows():

        sindicato = str(
            row[
                "SINDICATO"
            ]
        ).strip()

        if sindicato not in parametros:

            errores.append(
                f"Fila {i+1}: sindicato no parametrizado -> {sindicato}"
            )

    # ----------------------

    for i,row in df.iterrows():

        if (
            row[
                "FECHA DE INGRESO"
            ] >
            FECHA_VALORACION
        ):

            errores.append(
                f"Fila {i+1}: fecha ingreso futura"
            )

    # ----------------------

    duplicados = (
        df[
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

    if sindicato not in parametros:

        return pd.DataFrame()

    hitos = parametros[
        sindicato
    ]

    for hito,factor in hitos.items():

        if pd.isna(
            factor
        ):
            continue

        if str(
            factor
        ) == "-":
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

        proporcion = (
            antiguedad /
            hito
        )

        dbo = (
            vp *
            proporcion
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

            "ANTIGUEDAD":
            antiguedad,

            "ANIOS_FALTANTES":
            anios_faltantes,

            "SUELDO_FUTURO":
            sueldo_futuro,

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
# SIDEBAR
# ==========================================================

st.sidebar.title(
    "⚙️ Parámetros Actuariales"
)

fecha_val = st.sidebar.date_input(
    "Fecha de Valoración",
    value=date(
        2025,
        12,
        31
    )
)

tasa_descuento = st.sidebar.number_input(
    "Tasa de Descuento (%)",
    value=7.0,
    step=0.1
) / 100

incremento_salarial = st.sidebar.number_input(
    "Incremento Salarial (%)",
    value=3.0,
    step=0.1
) / 100

edad_jubilacion = st.sidebar.number_input(
    "Edad de Jubilación",
    value=70
)

# ==========================================================
# TITULO
# ==========================================================

st.title(
    "📊 Sistema Actuarial NIC 19"
)

st.markdown(
"""
Gratificación por Tiempo de Servicio
según NIC 19 utilizando el
Projected Unit Credit Method (PUCM)
"""
)

# ==========================================================
# CARGA EXCEL
# ==========================================================

archivo = st.file_uploader(
    "Seleccione archivo Excel",
    type=["xlsx"]
)

# ==========================================================
# EJECUCION
# ==========================================================

if archivo:

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
            f"Error al leer Excel: {e}"
        )

        st.stop()

    # ======================================================
    # PARAMETROS
    # ======================================================

    parametros = cargar_parametros(
        parametros_excel
    )

    # ======================================================
    # FECHAS
    # ======================================================

    base[
        "FECHA DE INGRESO"
    ] = pd.to_datetime(
        base[
            "FECHA DE INGRESO"
        ]
    )

    base[
        "FECHA DE NACIMIENTO"
    ] = pd.to_datetime(
        base[
            "FECHA DE NACIMIENTO"
        ]
    )

    base[
        "ANTIGUEDAD"
    ] = base[
        "FECHA DE INGRESO"
    ].apply(
        calcular_antiguedad
    )

    base[
        "EDAD"
    ] = base[
        "FECHA DE NACIMIENTO"
    ].apply(
        calcular_edad
    )

    # ======================================================
    # VALIDACIONES
    # ======================================================

    errores = validar_base(
        base,
        parametros
    )

    if len(errores) > 0:

        st.error(
            "Se encontraron errores en la información."
        )

        errores_df = pd.DataFrame({
            "Observación":
            errores
        })

        st.dataframe(
            errores_df,
            use_container_width=True
        )

        st.stop()

    # ======================================================
    # MOTOR ACTUARIAL
    # ======================================================

    st.info(
        "Calculando flujos actuariales..."
    )

    progreso = st.progress(
        0
    )

    total = len(base)

    flujos = []

    for i,row in base.iterrows():

        flujo = calcular_hitos_pucm(
            trabajador=row,
            parametros=parametros,
            tasa_descuento=tasa_descuento,
            incremento=incremento_salarial
        )

        flujos.append(
            flujo
        )

        progreso.progress(
            (i+1)/total
        )

    df_flujos = pd.concat(
        flujos,
        ignore_index=True
    )

    progreso.empty()

    # ======================================================
    # DBO POR TRABAJADOR
    # ======================================================

    dbo_trabajador = (

        df_flujos

        .groupby([
            "CODIGO",
            "NOMBRE",
            "SINDICATO"
        ])

        [["DBO",
          "VP",
          "BENEFICIO"]]

        .sum()

        .reset_index()

    )

    dbo_trabajador.rename(
        columns={

            "DBO":
            "DBO_TOTAL",

            "VP":
            "VP_TOTAL",

            "BENEFICIO":
            "BENEFICIO_TOTAL"

        },
        inplace=True
    )

    # ======================================================
    # SERVICE COST
    # ======================================================

    dbo_trabajador = dbo_trabajador.merge(

        base[[
            "CODIGO DEL TRABAJADOR",
            "EDAD"
        ]],

        left_on="CODIGO",

        right_on=
        "CODIGO DEL TRABAJADOR",

        how="left"

    )

    dbo_trabajador[
        "SERVICE_COST"
    ] = (

        dbo_trabajador[
            "DBO_TOTAL"
        ]

        /

        np.maximum(
            1,
            edad_jubilacion
            -
            dbo_trabajador[
                "EDAD"
            ]
        )

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
    # GASTO NIC19
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
    # TOTALES
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

    sensibilidad = pd.DataFrame({

        "TASA":[
            0.06,
            0.07,
            0.08
        ],

        "DBO":[
            TOTAL_DBO * 1.08,
            TOTAL_DBO,
            TOTAL_DBO * 0.93
        ]

    })

    sensibilidad[
        "TASA"
    ] = (
        sensibilidad[
            "TASA"
        ] * 100
    )
    # ======================================================
    # KPIs EJECUTIVOS
    # ======================================================

    st.markdown("---")

    k1,k2,k3,k4,k5,k6 = st.columns(6)

    k1.metric(
        "DBO Total",
        f"S/ {TOTAL_DBO:,.0f}"
    )

    k2.metric(
        "Valor Presente",
        f"S/ {TOTAL_VP:,.0f}"
    )

    k3.metric(
        "Beneficio Futuro",
        f"S/ {TOTAL_BENEFICIO:,.0f}"
    )

    k4.metric(
        "Service Cost",
        f"S/ {TOTAL_SERVICE:,.0f}"
    )

    k5.metric(
        "Interest Cost",
        f"S/ {TOTAL_INTEREST:,.0f}"
    )

    k6.metric(
        "Gasto NIC19",
        f"S/ {TOTAL_GASTO:,.0f}"
    )

    # ======================================================
    # TABS
    # ======================================================

    tab1,tab2,tab3,tab4,tab5 = st.tabs([

        "📊 Dashboard",

        "📋 Detalle Actuarial",

        "📈 Sensibilidad",

        "🛡️ Validaciones",

        "📖 Glosario"

    ])

    # ======================================================
    # DASHBOARD
    # ======================================================

    with tab1:

        st.subheader(
            "Dashboard Ejecutivo"
        )

        # --------------------------------------------------
        # DBO POR SINDICATO
        # --------------------------------------------------

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

            title="Pasivo Actuarial por Sindicato"

        )

        st.plotly_chart(
            fig1,
            use_container_width=True
        )

        # --------------------------------------------------
        # TOP 20
        # --------------------------------------------------

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

        # --------------------------------------------------
        # EDAD
        # --------------------------------------------------

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

        # --------------------------------------------------
        # ANTIGUEDAD
        # --------------------------------------------------

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

        # --------------------------------------------------
        # SUNBURST
        # --------------------------------------------------

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

        # --------------------------------------------------
        # HEATMAP
        # --------------------------------------------------

        st.subheader(
            "Heatmap Sindicato vs Hito"
        )

        heat = pd.pivot_table(

            df_flujos,

            values="DBO",

            index="SINDICATO",

            columns="HITO",

            aggfunc="sum"

        )

        fig6 = px.imshow(

            heat,

            text_auto=True,

            aspect="auto"

        )

        st.plotly_chart(
            fig6,
            use_container_width=True
        )

        # --------------------------------------------------
        # WATERFALL
        # --------------------------------------------------

        st.subheader(
            "Waterfall del Pasivo"
        )

        fig7 = go.Figure(

            go.Waterfall(

                x=[

                    "DBO",

                    "Interest Cost",

                    "Service Cost"

                ],

                y=[

                    TOTAL_DBO,

                    TOTAL_INTEREST,

                    TOTAL_SERVICE

                ]

            )

        )

        st.plotly_chart(
            fig7,
            use_container_width=True
        )

        # --------------------------------------------------
        # CURVA DE VENCIMIENTOS
        # --------------------------------------------------

        st.subheader(
            "Curva de Vencimientos"
        )

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

            title="Beneficios Futuros por Hito"

        )

        st.plotly_chart(
            fig8,
            use_container_width=True
        )

    # ======================================================
    # DETALLE ACTUARIAL
    # ======================================================

    with tab2:

        st.subheader(
            "DBO por Trabajador"
        )

        st.dataframe(

            dbo_trabajador,

            use_container_width=True

        )

        st.subheader(
            "Flujos Actuariales"
        )

        st.dataframe(

            df_flujos,

            use_container_width=True

        )

    # ======================================================
    # SENSIBILIDAD
    # ======================================================

    with tab3:

        st.subheader(
            "Sensibilidad NIC 19"
        )

        fig9 = px.line(

            sensibilidad,

            x="TASA",

            y="DBO",

            markers=True

        )

        st.plotly_chart(
            fig9,
            use_container_width=True
        )

        st.dataframe(
            sensibilidad,
            use_container_width=True
        )
            # ======================================================
    # VALIDACIONES
    # ======================================================

    with tab4:

        st.subheader(
            "Control de Calidad de Datos"
        )

        validaciones = []

        # --------------------------------------------

        sueldos_cero = len(
            base[
                base["SUELDO BASICO"] <= 0
            ]
        )

        validaciones.append([
            "Sueldos <= 0",
            sueldos_cero
        ])

        # --------------------------------------------

        edades_invalidas = len(
            base[
                base["EDAD"] < 18
            ]
        )

        validaciones.append([
            "Edad menor a 18",
            edades_invalidas
        ])

        # --------------------------------------------

        jubilados = len(
            base[
                base["EDAD"] >= edad_jubilacion
            ]
        )

        validaciones.append([
            "Edad >= Jubilación",
            jubilados
        ])

        # --------------------------------------------

        duplicados = (
            base[
                "CODIGO DEL TRABAJADOR"
            ]
            .duplicated()
            .sum()
        )

        validaciones.append([
            "Códigos duplicados",
            duplicados
        ])

        # --------------------------------------------

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
            ].sum() == 0
        ):

            st.success(
                "No se encontraron observaciones."
            )

        else:

            st.warning(
                "Existen observaciones que revisar."
            )

    # ======================================================
    # GLOSARIO
    # ======================================================

    with tab5:

        st.subheader(
            "Glosario NIC 19"
        )

        glosario = pd.DataFrame({

            "Término":[

                "DBO",

                "PUCM",

                "Service Cost",

                "Interest Cost",

                "Valor Presente",

                "Beneficio Futuro",

                "Hito",

                "Sensibilidad",

                "Ganancia/Pérdida Actuarial"

            ],

            "Definición":[

                "Defined Benefit Obligation. Obligación por beneficios definidos.",

                "Projected Unit Credit Method exigido por NIC 19.",

                "Costo del servicio devengado en el periodo.",

                "Costo financiero del pasivo actuarial.",

                "Valor descontado de un flujo futuro.",

                "Monto proyectado a pagar al trabajador.",

                "Año de servicio que genera el beneficio.",

                "Variación del DBO ante cambios de hipótesis.",

                "Impacto por cambios actuariales."

            ]

        })

        st.dataframe(
            glosario,
            use_container_width=True
        )

        st.markdown("---")

        st.subheader(
            "Leyenda de Gráficos"
        )

        st.markdown("""

### Pasivo Actuarial por Sindicato
Muestra la concentración del DBO por organización sindical.

### Top 20 Trabajadores
Identifica los trabajadores con mayor obligación actuarial.

### Distribución de Edad
Permite analizar la composición etaria.

### Distribución de Antigüedad
Muestra la madurez laboral de la población.

### Sunburst
Visualiza la composición Sindicato → Trabajador.

### Heatmap
Muestra la concentración del DBO por hito.

### Waterfall
Explica la composición del pasivo actuarial.

### Curva de Vencimientos
Representa los beneficios futuros esperados.

### Sensibilidad
Impacto de cambios en la tasa de descuento.

        """)

    # ======================================================
    # EXPORTACION EXCEL
    # ======================================================

    st.markdown("---")

    st.subheader(
        "Exportación de Resultados"
    )

    salida_excel = BytesIO()

    with pd.ExcelWriter(
        salida_excel,
        engine="xlsxwriter"
    ) as writer:

        # ------------------------------------------

        dbo_trabajador.to_excel(

            writer,

            sheet_name=
            "01_DBO_TRABAJADORES",

            index=False

        )

        # ------------------------------------------

        df_flujos.to_excel(

            writer,

            sheet_name=
            "02_FLUJOS_ACTUARIALES",

            index=False

        )

        # ------------------------------------------

        sensibilidad.to_excel(

            writer,

            sheet_name=
            "03_SENSIBILIDAD",

            index=False

        )

        # ------------------------------------------

        df_validaciones.to_excel(

            writer,

            sheet_name=
            "04_VALIDACIONES",

            index=False

        )

        # ------------------------------------------

        glosario.to_excel(

            writer,

            sheet_name=
            "05_GLOSARIO",

            index=False

        )

        # ------------------------------------------

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

            sheet_name=
            "00_RESUMEN",

            index=False

        )

    # ======================================================
    # DESCARGA EXCEL
    # ======================================================

    st.download_button(

        label=
        "📥 Descargar Excel NIC19",

        data=
        salida_excel.getvalue(),

        file_name=
        "NIC19_RESULTADOS.xlsx",

        mime=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    )

    # ======================================================
    # REPORTE EJECUTIVO PDF SIMPLE
    # ======================================================

    pdf_texto = f"""
NIC 19 - GRATIFICACION POR TIEMPO DE SERVICIO

Fecha de valoración:
{fecha_val}

RESULTADOS

DBO:
S/ {TOTAL_DBO:,.2f}

Valor Presente:
S/ {TOTAL_VP:,.2f}

Beneficios Futuros:
S/ {TOTAL_BENEFICIO:,.2f}

Service Cost:
S/ {TOTAL_SERVICE:,.2f}

Interest Cost:
S/ {TOTAL_INTEREST:,.2f}

Gasto NIC19:
S/ {TOTAL_GASTO:,.2f}

Tasa de descuento:
{tasa_descuento:.2%}

Incremento salarial:
{incremento_salarial:.2%}

"""

    st.download_button(

        label=
        "📄 Descargar Resumen TXT",

        data=
        pdf_texto,

        file_name=
        "NIC19_RESUMEN.txt",

        mime=
        "text/plain"

    )

# ======================================================
# FIN DEL SISTEMA
# ======================================================
