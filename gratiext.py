# CALCULO-DE-GRATIFICACIONES-EXTRAORNARIAS-NIC-19
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO

# ======================================================
# PARAMETROS ACTUARIALES
# ======================================================

FECHA_VALORACION = datetime(2025, 12, 31)
TASA_DESCUENTO = 0.07
INCREMENTO_SALARIAL = 0.03
EDAD_JUBILACION = 70

# ======================================================
# FUNCIONES ACTUARIALES
# ======================================================

def calcular_edad(fecha_nacimiento):
    return (
        FECHA_VALORACION - fecha_nacimiento
    ).days / 365.25


def calcular_antiguedad(fecha_ingreso):
    return (
        FECHA_VALORACION - fecha_ingreso
    ).days / 365.25


def sueldo_proyectado(
    sueldo,
    anios,
    incremento=INCREMENTO_SALARIAL
):
    return sueldo * ((1 + incremento) ** anios)


def valor_presente(
    flujo,
    anios,
    tasa=TASA_DESCUENTO
):
    return flujo / ((1 + tasa) ** anios)


def validar_base_datos(df):

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

        if col not in df.columns:
            errores.append(
                f"Falta columna: {col}"
            )

    return errores


def cargar_parametros(df_param):

    parametros = {}

    sindicatos = df_param.iloc[0, 2:].tolist()

    for i, sindicato in enumerate(sindicatos):

        parametros[sindicato] = {}

        for fila in range(1, len(df_param)):

            anio_txt = str(
                df_param.iloc[fila, 1]
            )

            if "AÑOS" not in anio_txt:
                continue

            anio = int(
                anio_txt.replace(
                    "AÑOS",
                    ""
                ).strip()
            )

            factor = df_param.iloc[
                fila,
                i + 2
            ]

            parametros[sindicato][anio] = factor

    return parametros


def calcular_flujos_trabajador(
    trabajador,
    parametros
):

    sindicato = trabajador["SINDICATO"]

    if sindicato not in parametros:
        return pd.DataFrame()

    sueldo = trabajador["SUELDO BASICO"]

    antiguedad = trabajador["ANTIGUEDAD"]

    flujos = []

    for hito, factor in parametros[sindicato].items():

        if pd.isna(factor):
            continue

        if str(factor) == "-":
            continue

        if antiguedad >= hito:
            continue

        faltante = hito - antiguedad

        sueldo_futuro = sueldo_proyectado(
            sueldo,
            faltante
        )

        beneficio = (
            sueldo_futuro *
            float(factor)
        )

        vp = valor_presente(
            beneficio,
            faltante
        )

        proporcion = (
            antiguedad / hito
        )

        dbo = vp * proporcion

        flujos.append({
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

    return pd.DataFrame(flujos)
