"""
Generador de Clientes Sintéticos para Sistema de Recomendación de ETFs
Autor: Proyecto TFM (modificado)
Versión: v2.3
Fecha: Octubre 2025

Objetivo:
Generar un CSV con clientes sintéticos con información relevante para personalización:
Edad, Sueldo_Anual, Patrimonio, Horizonte de inversión, Tolerancia al riesgo,
Sector favorito y Conocimiento inversor.

Notas:
- La Rentabilidad_Esperada ya NO se incluye: se calculará más adelante en función
  de los ETFs recomendados y la cartera final del cliente.
- Se usa logging profesional para control, auditoría y depuración.
- El sueldo y patrimonio se generan de forma realista considerando perfiles europeos.
"""

import pandas as pd
import numpy as np
import logging

# ------------------------------------------------------
# Configuración general y parámetros globales
# ------------------------------------------------------

# Configurar logger (nivel INFO por defecto)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Parámetros generales ajustables
CONOCIMIENTO_PROBS = {"Medio": 0.7, "Alto": 0.3}  # Probabilidades base aleatorias


# ------------------------------------------------------
# Funciones auxiliares
# ------------------------------------------------------

def generar_sueldos_europeos(edades):
    """
    Genera sueldos brutos mensuales realistas en euros según la edad.
    Basado en medias europeas (Eurostat 2024) divididas por 12.
    """
    sueldos = []
    for edad in edades:
        if edad < 25:
            # Media anual 25000, Desv. 4000
            base = np.random.normal(25000 / 12, 4000 / 12)
        elif edad < 35:
            # Media anual 35000, Desv. 6000
            base = np.random.normal(35000 / 12, 6000 / 12)
        elif edad < 45:
            # Media anual 45000, Desv. 8000
            base = np.random.normal(45000 / 12, 8000 / 12)
        elif edad < 55:
            # Media anual 50000, Desv. 9000
            base = np.random.normal(50000 / 12, 9000 / 12)
        elif edad < 65:
            # Media anual 45000, Desv. 8000
            base = np.random.normal(45000 / 12, 8000 / 12)
        else:
            # Media anual 30000, Desv. 6000
            base = np.random.normal(30000 / 12, 6000 / 12)
        
        # Aplicar mínimo mensual (15000 / 12 = 1250)
        sueldos.append(max(1250, base)) 
        
    return np.round(sueldos, 0).astype(int)


def estimar_patrimonio(sueldo, edad):
    """
    Estima patrimonio aproximado como múltiplo del salario anual,
    aumentando con la edad (simulando ahorro acumulado).
    """
    factor_edad = np.interp(edad, [20, 70], [1, 100])  # de 1x a 100x el salario
    ruido = np.random.normal(1.0, 0.3)
    patrimonio = sueldo * factor_edad * ruido
    return np.clip(patrimonio, 5000, 2_000_000).astype(int)


# ------------------------------------------------------
# Función principal
# ------------------------------------------------------

def generar_clientes_sinteticos(
        n_clientes=500,
        semilla=42,
        output_path='./clientes_base.csv',
        conocimiento_probs=CONOCIMIENTO_PROBS
    ):
    """
    Genera un dataset sintético de clientes y lo guarda en CSV.

    Args:
        n_clientes (int): Número de clientes a generar
        semilla (int): Semilla para reproducibilidad
        output_path (str): Ruta donde se guardará el CSV generado
        conocimiento_probs (dict): Probabilidades para asignar conocimiento inversor aleatorio

    Returns:
        pd.DataFrame: DataFrame con clientes sintéticos
    """

    np.random.seed(semilla)  # Reproducibilidad garantizada

    logging.info(f"🎯 Generando {n_clientes} clientes sintéticos europeos...")

    # ----------------------------
    # Variables básicas del cliente
    # ----------------------------
    edades = np.random.randint(20, 70, size=n_clientes)
    sueldos = generar_sueldos_europeos(edades)
    patrimonios = [estimar_patrimonio(s, e) for s, e in zip(sueldos, edades)]

    clientes = pd.DataFrame({
        "ClienteID": range(1, n_clientes + 1),
        "Edad": edades,
        "Sueldo_Anual": np.round(sueldos, 2),
        "Patrimonio": np.round(patrimonios, 2),
        "Horizonte": np.random.choice(["Corto", "Medio", "Largo"], size=n_clientes),
        "Tolerancia_Riesgo": np.random.choice(["Baja", "Media", "Alta"], size=n_clientes),
        # "Sector_Favorito": np.random.choice(["Tecnología", "Salud", "Finanzas", "Energía"], size=n_clientes)
    })

    # ----------------------------
    # Conocimiento inversor
    # ----------------------------
    conocimiento = []
    for _, row in clientes.iterrows():
        if row["Tolerancia_Riesgo"] == "Alta" and row["Edad"] < 35:
            conocimiento.append("Alto")
        elif row["Tolerancia_Riesgo"] == "Baja" and row["Edad"] > 55:
            conocimiento.append("Bajo")
        else:
            conocimiento.append(
                np.random.choice(
                    ["Medio", "Alto"],
                    p=[conocimiento_probs["Medio"], conocimiento_probs["Alto"]]
                )
            )
    clientes["Conocimiento_Inversor"] = conocimiento

    # ----------------------------
    # Control de calidad
    # ----------------------------
    try:
        if clientes.isnull().any().any():
            logging.warning("⚠️ Se detectaron valores nulos en el dataset de clientes.")
        else:
            logging.info("✅ No se detectaron valores nulos en el dataset de clientes.")
    except Exception as e:
        logging.warning(f"⚠️ Error durante validación de datos: {e}")

    # ----------------------------
    # Guardar CSV final
    # ----------------------------
    try:
        clientes.to_csv(output_path, index=False)
        logging.info(f"✅ CSV de clientes base generado correctamente en: {output_path}")
    except Exception as e:
        logging.error(f"❌ Error al guardar el CSV: {e}")

    return clientes


# ------------------------------------------------------
# Ejecución directa
# ------------------------------------------------------
if __name__ == "__main__":
    generar_clientes_sinteticos(n_clientes=500)
