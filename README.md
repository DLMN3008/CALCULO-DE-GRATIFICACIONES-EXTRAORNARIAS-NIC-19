# CALCULO-DE-GRATIFICACIONES-EXTRAORNARIAS-NIC-19
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# --------------------------------------------------
# CONFIGURACION
# --------------------------------------------------

st.set_page_config(
    page_title="NIC 19 - Gratificación por Tiempo de Servicio",
    page_icon="📊",
    layout="wide"
)

FECHA_VALORACION = datetime(2025, 12, 31)
TASA_DESCUENTO = 0.07
INCREMENTO_SALARIAL = 0.03
EDAD_JUBILACION = 70

# --------------------------------------------------
# FUNCIONES
# --------------------------------------------------

def antiguedad(fecha_ingreso):
    return (FECHA_VALORACION - fecha_ingreso).days / 365.25

def edad(fecha_nacimiento):
    return (FECHA_VALORACION - fecha_nacimiento).days / 365.25

def sueldo_proyectado(sueldo, n):
    return sueldo * ((1 + INCREMENTO_SALARIAL) ** n)

def valor_presente(valor_futuro, n):
    return valor_futuro / ((1 + TASA_DESCUENTO) ** n)

def cargar_parametros(df_param):

    sindicatos = {
        "SITECORPAC": {},
        "SITPRUCOR": {},
        "SINEACORP": {},
        "SIPEACOR": {}
    }

    hitos = [10,15,20,25,30,35,40,45,50]

    factores_site = ["-",1,1.5,2,2.5,3,4,4,"-"]
    factores_sucta = ["-",1,1.5,2,2.5,3,4,5,"-"]
    factores_sinea = [1,1.1,1.65,2.2,2.75,3.3,4.4,5.5,6]
    factores_sipea = ["-",1,1.5,2,2.5,3,4,5,"-"]

    for h,f in zip(hitos,factores_site):
        sindicatos["SITECORPAC"][h]=f

    for h,f in zip(hitos,factores_sucta):
        sindicatos["SITPRUCOR"][h]=f

    for h,f in zip(hitos,factores_sinea):
        sindicatos["SINEACORP"][h]=f

    for h,f in zip(hitos,factores_sipea):
        sindicatos["SIPEACOR"][h]=f

    return sindicatos

def calcular_trabajador(row,parametros):

    sindicato=row["SINDICATO"]

    if sindicato not in parametros:
        return 0,0

    sueldo=row["SUELDO BASICO"]

    ant=row["ANTIGUEDAD"]

    dbo_total=0
    vf_total=0

    for hito,factor in parametros[sindicato].items():

        if factor=="-":
            continue

        if ant >= hito:
            continue

        n=hito-ant

        sueldo_fut=sueldo_proyectado(sueldo,n)

        beneficio=sueldo_fut*float(factor)

        vp=valor_presente(beneficio,n)

        proporcion=ant/hito

        dbo=vp*proporcion

        dbo_total += dbo
        vf_total += beneficio

    return dbo_total,vf_total

# --------------------------------------------------
# TITULO
# --------------------------------------------------

st.title("📊 NIC 19 - Gratificación por Tiempo de Servicio")
st.markdown("### Valor Presente Actuarial y Devengo Anual")

archivo=st.file_uploader(
    "Cargar archivo Excel",
    type=["xlsx"]
)

if archivo:

    base=pd.read_excel(
        archivo,
        sheet_name="BASE DE DATOS"
    )

    parametros_excel=pd.read_excel(
        archivo,
        sheet_name="PARAMETROS"
    )

    parametros=cargar_parametros(parametros_excel)

    # -----------------------------
    # PREPARACION
    # -----------------------------

    base["FECHA DE INGRESO"]=pd.to_datetime(
        base["FECHA DE INGRESO"]
    )

    base["FECHA DE NACIMIENTO"]=pd.to_datetime(
        base["FECHA DE NACIMIENTO"]
    )

    base["ANTIGUEDAD"]=base[
        "FECHA DE INGRESO"
    ].apply(antiguedad)

    base["EDAD"]=base[
        "FECHA DE NACIMIENTO"
    ].apply(edad)

    resultados=[]

    for _,row in base.iterrows():

        dbo,vf=calcular_trabajador(
            row,
            parametros
        )

        resultados.append(
            [dbo,vf]
        )

    resultados=pd.DataFrame(
        resultados,
        columns=[
            "DBO",
            "VALOR_FUTURO"
        ]
    )

    base=pd.concat(
        [base,resultados],
        axis=1
    )

    base["INTEREST_COST"]=base["DBO"]*0.07

    base["SERVICE_COST"]=(
        base["DBO"]/np.maximum(
            1,
            70-base["EDAD"]
        )
    )

    base["GASTO_NIC19"]=(
        base["INTEREST_COST"]
        +base["SERVICE_COST"]
    )

    # -----------------------------
    # KPIs
    # -----------------------------

    total_dbo=base["DBO"].sum()
    total_gasto=base["GASTO_NIC19"].sum()
    total_vf=base["VALOR_FUTURO"].sum()

    c1,c2,c3,c4=st.columns(4)

    c1.metric(
        "Pasivo Actuarial",
        f"S/ {total_dbo:,.0f}"
    )

    c2.metric(
        "Gasto NIC 19",
        f"S/ {total_gasto:,.0f}"
    )

    c3.metric(
        "Valor Futuro",
        f"S/ {total_vf:,.0f}"
    )

    c4.metric(
        "Trabajadores",
        len(base)
    )

    # -----------------------------
    # GRAFICO 1
    # -----------------------------

    st.subheader("Pasivo por Sindicato")

    sindicato=base.groupby(
        "SINDICATO"
    )["DBO"].sum().reset_index()

    fig=px.bar(
        sindicato,
        x="SINDICATO",
        y="DBO"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # -----------------------------
    # GRAFICO 2
    # -----------------------------

    st.subheader("Top 20 Trabajadores")

    top20=base.nlargest(
        20,
        "DBO"
    )

    fig2=px.bar(
        top20,
        x="NOMBRES",
        y="DBO"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # -----------------------------
    # GRAFICO 3
    # -----------------------------

    st.subheader("Distribución Antigüedad")

    fig3=px.histogram(
        base,
        x="ANTIGUEDAD",
        nbins=20
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # -----------------------------
    # GRAFICO 4
    # -----------------------------

    st.subheader("Pasivo por Sede")

    sedes=base.groupby(
        "SEDES"
    )["DBO"].sum().reset_index()

    fig4=px.pie(
        sedes,
        names="SEDES",
        values="DBO"
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    # -----------------------------
    # DETALLE
    # -----------------------------

    st.subheader("Detalle NIC 19")

    st.dataframe(
        base,
        use_container_width=True
    )

    # -----------------------------
    # EXPORTAR
    # -----------------------------

    salida=BytesIO()

    with pd.ExcelWriter(
        salida,
        engine="xlsxwriter"
    ) as writer:

        base.to_excel(
            writer,
            index=False,
            sheet_name="NIC19"
        )

    st.download_button(
        "📥 Descargar Excel",
        data=salida.getvalue(),
        file_name="NIC19_RESULTADOS.xlsx",
        mime="application/vnd.ms-excel"
    )
