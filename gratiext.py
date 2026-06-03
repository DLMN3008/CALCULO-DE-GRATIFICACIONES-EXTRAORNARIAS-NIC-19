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
