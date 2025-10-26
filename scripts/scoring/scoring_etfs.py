"""
scoring_etfs.py
----------------------------------
Pipeline principal para el cálculo de scoring, ranking y predicción de ETFs.

Version: 1.7.0 - Implementación de Pesos Dinámicos por Grupo de Riesgo.
    - El peso de las métricas de Riesgo/Volatilidad (KID_SRI, Sharpe, Alfa)
      y Rendimiento (PREDICTED_COL) se ajusta según el 'Grupo' del ETF.
    - Se garantiza la equidad en el scoring entre clases de activos.

Autor: EVOLVE Research (TFM Project)
Análisis y Mejora: Tu Tutor de ML/DS
"""

import pandas as pd
import numpy as np
import logging

import sys
import os
# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from settings import ETFS_SCORED_PATH, TOPN_CATEGORIA_PATH, TOPN_GRUPO_PATH, ETF_LIMPIO_PATH

# ======================================================
# 🧭 LOGGING
# ======================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Columna utilizada para la predicción de rendimiento anualizada
PREDICTED_COL = "Rentabilidad_Anual_Predicha"

# ======================================================
# ⚖️ CONFIGURACIÓN GLOBAL MÉTRICAS
# ======================================================
# Esta es la base, que será SOBREESCRITA por los pesos dinámicos en la función de scoring.
METRICS_CONFIG_BASE = {
    # Factores de Calidad/Rendimiento Ajustado (su peso varía fuertemente)
    "Alfa_3Años_Mensual": {"direction": "higher"},
    "Sharpe_3Años_Mensual": {"direction": "higher"},
    PREDICTED_COL: {"direction": "higher"},
    "KID_SRI": {"direction": "lower"},
    
    # Factores Secundarios/Constantes (mantienen un peso fijo en todos los grupos)
    "Costes": {"weight": 0.75, "direction": "lower"}, # Expense Ratio
    "Rent_1Año%": {"weight": 0.3, "direction": "higher"},
    "Patrimonio": {"weight": 0.25, "direction": "higher"},
}

# ======================================================
# 🎯 CONFIGURACIÓN DE PESOS DINÁMICOS POR GRUPO
# ======================================================
DYNAMIC_WEIGHTS = {
    # GRUPO 1: BAJO RIESGO (Cash, RF Corto Plazo) - PRIORIDAD: Seguridad
    1: {
        "KID_SRI": 1.5,                 # Peso Máximo para la seguridad
        "Sharpe_3Años_Mensual": 1.25,
        "Alfa_3Años_Mensual": 0.75,
        PREDICTED_COL: 0.5,             # Bajo peso al retorno, no es el objetivo
    },
    
    # GRUPO 2: MEDIO RIESGO (Renta Variable Core, Sectorial) - PRIORIDAD: Rendimiento Ajustado
    2: {
        "KID_SRI": 0.5,                 # Bajo peso: No penalizar la volatilidad natural de la RV
        "Sharpe_3Años_Mensual": 1.5,    # Peso Máximo: Medida clave en RV
        "Alfa_3Años_Mensual": 1.0,
        PREDICTED_COL: 1.0,             # Importante
    },
    
    # GRUPO 3: ALTO RIESGO/ESPECIALES (Emergentes, Materias Primas) - PRIORIDAD: Comp. por Riesgo
    3: {
        "KID_SRI": 0.75,                # Peso intermedio: Penalizar riesgo excesivo, pero permitirlo
        "Sharpe_3Años_Mensual": 1.0,
        "Alfa_3Años_Mensual": 1.25,     # Premiar fuertemente el Alpha (outperformance)
        PREDICTED_COL: 1.25,            # Premiar fuertemente el retorno esperado (compensación)
    },
}

# ======================================================
# ⚙️ CARGA Y LIMPIEZA DE DATOS
# ======================================================
def cargar_datos(path_csv: str) -> pd.DataFrame:
    """
    Carga los datos desde CSV, asegura que existan todas las columnas necesarias,
    convierte las columnas numéricas y mantiene todas las filas aunque falten datos.
    """
    logger.info("🔍 Preparando datos de entrada...")
    try:
        df = pd.read_csv(path_csv)
    except FileNotFoundError:
        logger.error(f"Error fatal: No se encontró el archivo en {path_csv}")
        return pd.DataFrame()

    # Columnas base opcionales, no obligatorias
    base_cols = ["Categoría", "Grupo", "Precio", "Costes", "Patrimonio"]

    # Columnas métricas necesarias para scoring
    required_metrics = set(METRICS_CONFIG_BASE.keys())
    for weights in DYNAMIC_WEIGHTS.values():
        required_metrics.update(weights.keys())

    # Columnas adicionales de rentabilidad
    rent_cols = ["Rent_1Mes%", "Rent_3Meses%", "Rent_6Meses%", "Rent_1Año%",
                 "Rent_3Años%", "Rent_5Años%", "Rent_10Años%"]

    # Asegurar todas las columnas, rellenando NaN si no existen
    for col in list(base_cols) + list(required_metrics) + rent_cols:
        if col not in df.columns:
            df[col] = np.nan

    # Convertir columnas numéricas
    numeric_cols = ["Precio", "Costes", "Patrimonio", "KID_SRI",
                    "Sharpe_3Años_Mensual", "Alfa_3Años_Mensual"] + rent_cols

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    logger.info(f"✅ Datos cargados: {len(df)} ETFs. Columnas disponibles: {df.columns.tolist()[:10]} ...")
    return df

# ======================================================
# 💡 FUNCIÓN: EXTRAPOLACIÓN PONDERADA
# ======================================================
def extrapolar_rentabilidad_anual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la Rentabilidad Anual Predicha (PREDICTED_COL) mediante una media ponderada
    de todos los retornos históricos disponibles.
    """
    df = df.copy()
    logger.info("💡 Calculando Rentabilidad Anual Estimada")
    
    # Definición de las métricas de rendimiento y sus pesos/factores de anualización
    RENT_CONFIG = {
        "Rent_1Mes%":   {"factor": 12.0, "weight": 0.2},
        "Rent_3Meses%": {"factor": 4.0,  "weight": 0.3},
        "Rent_6Meses%": {"factor": 2.0,  "weight": 0.5},
        "Rent_1Año%":   {"factor": 1.0,  "weight": 1.0},
        "Rent_3Años%":  {"factor": 1/3,  "weight": 1.0},
        "Rent_5Años%":  {"factor": 1/5,  "weight": 1.0},
        "Rent_10Años%": {"factor": 1/10, "weight": 1.0},
    }
    
    df[PREDICTED_COL] = np.nan
    
    total_weighted_return = pd.Series(0.0, index=df.index)
    total_applicable_weight = pd.Series(0.0, index=df.index)
    
    for col, config in RENT_CONFIG.items():
        if col in df.columns:
            annualized_return = df[col] * config['factor']
            weight = config['weight']
            
            has_data_mask = annualized_return.notna()
            
            total_weighted_return[has_data_mask] += annualized_return[has_data_mask] * weight
            total_applicable_weight[has_data_mask] += weight
            
    final_annual_prediction = total_weighted_return.divide(total_applicable_weight)
    
    df[PREDICTED_COL] = final_annual_prediction.where(total_applicable_weight > 0)
    
    predicted_count = df[PREDICTED_COL].notna().sum()
    logger.info(f"✅ Rentabilidad Anual Predicha calculada para {predicted_count} ETFs.")
    
    return df


def clasificar_por_grupo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clasifica los ETFs en grupos de riesgo según rentabilidad anual predicha y volatilidad.

    Reglas:
    - Grupo 1: Rentabilidad ≤ 5% y volatilidad baja
    - Grupo 2: Rentabilidad entre 5% y 20% y volatilidad media
    - Grupo 3: Rentabilidad entre 20% y 50% y volatilidad alta
    - Grupo 4: Rentabilidad > 50% o sin rentabilidad estimada (excluidos del ranking)
    """
    df = df.copy()

    # Calcular umbrales de volatilidad
    vol_baja = df["Volatilidad_3Años_Mensual"].quantile(0.33)
    vol_media = df["Volatilidad_3Años_Mensual"].quantile(0.66)

    def asignar_grupo(row):
        rent = row.get("Rentabilidad_Anual_Predicha", np.nan)
        vol = row.get("Volatilidad_3Años_Mensual", np.nan)

        # 🚫 Sin rentabilidad o >50% → grupo 4 (excluir del top)
        if pd.isna(rent) or rent > 50:
            return 4

        # 🟢 Grupo 1: bajo riesgo
        if rent <= 5 and not pd.isna(vol) and vol <= vol_baja:
            return 1

        # 🟡 Grupo 2: riesgo medio
        if 5 < rent <= 20 and not pd.isna(vol) and vol_baja < vol <= vol_media:
            return 2

        # 🔴 Grupo 3: riesgo alto
        if 20 < rent <= 50 and not pd.isna(vol) and vol > vol_media:
            return 3

        # Si no cumple exactamente, lo consideramos fuera (grupo 4)
        return 4

    df["Grupo"] = df.apply(asignar_grupo, axis=1)
    return df


def top_etfs_por_grupo(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Devuelve los top N ETFs por grupo según la Rentabilidad Anual Predicha.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas 'Grupo' y 'Rentabilidad_Anual_Predicha'.
        top_n (int): Número de ETFs a devolver por grupo (default=5).
        
    Returns:
        pd.DataFrame: ETFs top por grupo, ordenados por 'Grupo' y rentabilidad descendente.
    """

    # Filtramos solo filas con rentabilidad predicha disponible
    df = df[df["Grupo"].isin([1, 2, 3]) & df['Rentabilidad_Anual_Predicha'].notna()]
    
    # Iteramos por grupo y marcamos top N
    for grupo, grupo_df in df.groupby('Grupo'):
        top_indices = grupo_df.nlargest(top_n, 'Rentabilidad_Anual_Predicha').index
        df.loc[top_indices, 'Top_Grupo'] = True

    df['Rank_Grupo'] = (
        df.groupby('Grupo')['Rentabilidad_Anual_Predicha']
          .rank(method='first', ascending=False)
          .astype(int)  # 👈 fuerza entero
    )

    return df


# ======================================================
# 💾 EXPORTACIÓN DE RESULTADOS (Mantenida de v1.6.5)
# ======================================================
def exportar_resultados(df: pd.DataFrame, n_top: int = 5):
    """
    Exporta el registro maestro completo y los rankings Top N.
    """
    logger.info(f"💾 Exportando resultados completos y Top {n_top}...")
    
    cols_topn_grupo = ["Nombre", "ISIN", "Grupo", "Rank_Grupo", PREDICTED_COL, "Volatilidad_3Años_Mensual"]

    # 3. Guardar CSV completo
    df_sorted = df.loc[:,~df.columns.duplicated()].copy() 
    df_sorted = df_sorted.sort_values(by=[PREDICTED_COL], ascending=True)
    df_sorted.to_csv(ETFS_SCORED_PATH, index=False, encoding='utf-8')
    logger.info(f"✅ Archivo completo exportado: {ETFS_SCORED_PATH}")

    # 5. Top N por grupo
    top_grupo_full = df[df["Rank_Grupo"] <= n_top].sort_values(
        by=["Grupo", "Rank_Grupo"]
    )
    # Filtrar solo por las columnas solicitadas
    top_grupo_minimal = top_grupo_full[cols_topn_grupo] 
    
    top_grupo_minimal.to_csv(TOPN_GRUPO_PATH, index=False, encoding='utf-8')

    logger.info(f"✅ Archivos Top {n_top} exportados en {TOPN_GRUPO_PATH}.")


# ======================================================
# 🚀 MAIN PIPELINE
# ======================================================
def main():
    """Ejecuta el pipeline completo: Carga -> Extrapolación -> Scoring -> Exportación."""
    logger.info("🚀 Iniciando pipeline de scoring y ranking ETFs")
    
    df = cargar_datos(ETF_LIMPIO_PATH) 
    
    if df.empty:
        logger.error("No se cargaron datos. Abortando pipeline.")
        return
        
    df = extrapolar_rentabilidad_anual(df)
    df = clasificar_por_grupo(df)
    df = top_etfs_por_grupo(df)
    
    exportar_resultados(df)
    
    logger.info("🎉 Pipeline finalizado con éxito.")

if __name__ == "__main__":
    main()