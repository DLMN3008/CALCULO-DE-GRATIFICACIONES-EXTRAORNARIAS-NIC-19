# CALCULO-DE-GRATIFICACIONES-EXTRAORNARIAS-NIC-19
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from modules.actuarial_engine import (
    cargar_parametros,
    calcular_edad,
    calcular_antiguedad,
    calcular_flujos_trabajador
)

from modules.validator import (
    validar_base_datos
)

from modules.excel_export import (
    generar_excel
)

from modules.pdf_report import (
    generar_pdf
)

# =====================================================
# CONFIGURACION
# =====================================================

st.set_page_config(
    page_title="NIC 19 - Gratificación por Tiempo de Servicio",
    page_icon="📊",
    layout="wide"
)

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("NIC 19")

st.sidebar.markdown("### Parámetros Actuariales")

fecha_valoracion = st.sidebar.date_input(
    "Fecha de Valoración",
    datetime(2025,12,31)
)

tasa_descuento = st.sidebar.number_input(
    "Tasa de Descuento %",
    value=7.0
) / 100

incremento_salarial = st.sidebar.number_input(
    "Incremento Salarial %",
    value=3.0
) / 100

edad_jubilacion = st.sidebar.number_input(
    "Edad Jubilación",
    value=70
)

# =====================================================
# TITULO
# =====================================================

st.title("📊 Sistema Actuarial NIC 19")
st.caption(
    "Gratificación por Tiempo de Servicio"
)

# =====================================================
# CARGA ARCHIVO
# =====================================================

archivo = st.file_uploader(
    "Seleccione archivo Excel",
    type=["xlsx"]
)

if archivo:

    # =================================================
    # LECTURA
    # =================================================

    try:

        df_base = pd.read_excel(
            archivo,
            sheet_name="BASE DE DATOS"
        )

        df_param = pd.read_excel(
            archivo,
            sheet_name="PARAMETROS",
            header=None
        )

    except Exception as e:

        st.error(str(e))
        st.stop()

    # =================================================
    # VALIDACION
    # =================================================

    errores = validar_base_datos(df_base)

    if len(errores) > 0:

        st.error(
            "Se encontraron errores."
        )

        st.dataframe(
            pd.DataFrame(
                errores,
                columns=["Observación"]
            )
        )

        st.stop()

    # =================================================
    # PREPARACION
    # =================================================

    df_base["FECHA DE INGRESO"] = pd.to_datetime(
        df_base["FECHA DE INGRESO"]
    )

    df_base["FECHA DE NACIMIENTO"] = pd.to_datetime(
        df_base["FECHA DE NACIMIENTO"]
    )

    df_base["EDAD"] = df_base[
        "FECHA DE NACIMIENTO"
    ].apply(calcular_edad)

    df_base["ANTIGUEDAD"] = df_base[
        "FECHA DE INGRESO"
    ].apply(calcular_antiguedad)

    parametros = cargar_parametros(
        df_param
    )

    # =================================================
    # MOTOR ACTUARIAL
    # =================================================

    flujos = []

    progress = st.progress(0)

    total = len(df_base)

    for i,row in df_base.iterrows():

        flujo = calcular_flujos_trabajador(
            row,
            parametros,
            tasa_descuento,
            incremento_salarial
        )

        flujos.append(flujo)

        progress.progress(
            (i+1)/total
        )

    df_flujos = pd.concat(
        flujos,
        ignore_index=True
    )

    # =================================================
    # DBO
    # =================================================

    dbo_trabajador = (
        df_flujos
        .groupby(
            ["CODIGO","NOMBRE"]
        )
        ["DBO"]
        .sum()
        .reset_index()
    )

    dbo_trabajador.rename(
        columns={
            "DBO":"DBO_TOTAL"
        },
        inplace=True
    )

    total_dbo = (
        dbo_trabajador[
            "DBO_TOTAL"
        ].sum()
    )

    total_beneficio = (
        df_flujos[
            "BENEFICIO"
        ].sum()
    )

    total_vp = (
        df_flujos[
            "VP"
        ].sum()
    )

    interest_cost = (
        total_dbo *
        tasa_descuento
    )

    service_cost = (
        total_dbo /
        edad_jubilacion
    )

    gasto_nic19 = (
        interest_cost +
        service_cost
    )

    # =================================================
    # KPIs
    # =================================================

    st.subheader("Indicadores")

    c1,c2,c3,c4,c5 = st.columns(5)

    c1.metric(
        "DBO",
        f"S/ {total_dbo:,.0f}"
    )

    c2.metric(
        "Valor Presente",
        f"S/ {total_vp:,.0f}"
    )

    c3.metric(
        "Beneficios Futuros",
        f"S/ {total_beneficio:,.0f}"
    )

    c4.metric(
        "Interest Cost",
        f"S/ {interest_cost:,.0f}"
    )

    c5.metric(
        "Gasto NIC19",
        f"S/ {gasto_nic19:,.0f}"
    )

    # =================================================
    # DASHBOARD
    # =================================================

    tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs([
        "Dashboard",
        "Flujos",
        "Sensibilidad",
        "Validaciones",
        "Glosario",
        "Exportar"
    ])

    # =================================================
    # DASHBOARD
    # =================================================

    with tab1:

        st.subheader(
            "DBO por Sindicato"
        )

        sind = (
            df_flujos
            .groupby("SINDICATO")
            ["DBO"]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            sind,
            x="SINDICATO",
            y="DBO"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader(
            "Top 20 Trabajadores"
        )

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
            y="DBO_TOTAL"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

        st.subheader(
            "Sunburst"
        )

        sun = px.sunburst(
            df_flujos,
            path=[
                "SINDICATO",
                "NOMBRE"
            ],
            values="DBO"
        )

        st.plotly_chart(
            sun,
            use_container_width=True
        )

        st.subheader(
            "Heatmap"
        )

        pivot = pd.pivot_table(
            df_flujos,
            values="DBO",
            index="SINDICATO",
            columns="HITO",
            aggfunc="sum"
        )

        heat = px.imshow(
            pivot,
            text_auto=True
        )

        st.plotly_chart(
            heat,
            use_container_width=True
        )

        st.subheader(
            "Waterfall DBO"
        )

        waterfall = go.Figure(
            go.Waterfall(
                x=[
                    "DBO",
                    "Interest",
                    "Service"
                ],
                y=[
                    total_dbo,
                    interest_cost,
                    service_cost
                ]
            )
        )

        st.plotly_chart(
            waterfall,
            use_container_width=True
        )

    # =================================================
    # FLUJOS
    # =================================================

    with tab2:

        st.dataframe(
            df_flujos,
            use_container_width=True
        )

    # =================================================
    # SENSIBILIDAD
    # =================================================

    with tab3:

        sensibilidad = pd.DataFrame({
            "Tasa":[6,7,8],
            "DBO":[
                total_dbo*1.08,
                total_dbo,
                total_dbo*0.93
            ]
        })

        fig = px.line(
            sensibilidad,
            x="Tasa",
            y="DBO",
            markers=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.dataframe(
            sensibilidad
        )

    # =================================================
    # VALIDACIONES
    # =================================================

    with tab4:

        st.success(
            "Base validada correctamente."
        )

        st.dataframe(df_base)

    # =================================================
    # GLOSARIO
    # =================================================

    with tab5:

        st.markdown("""
### DBO
Defined Benefit Obligation.

### PUCM
Projected Unit Credit Method.

### Interest Cost
Costo financiero actuarial.

### Service Cost
Costo del servicio devengado.

### Valor Presente
Valor descontado de los beneficios futuros.

### Beneficio Futuro
Monto esperado al cumplir el hito.

### Sensibilidad
Impacto del cambio de tasa de descuento.

### Hito
Años de servicio que generan beneficio.
        """)

    # =================================================
    # EXPORTACIONES
    # =================================================

    with tab6:

        excel_file = generar_excel(
            df_base,
            df_flujos,
            dbo_trabajador
        )

        st.download_button(
            "📥 Descargar Excel",
            excel_file,
            "NIC19_RESULTADOS.xlsx"
        )

        pdf_file = generar_pdf(
            total_dbo,
            gasto_nic19,
            total_beneficio
        )

        st.download_button(
            "📄 Descargar PDF",
            pdf_file,
            "NIC19_REPORTE.pdf"
        )
