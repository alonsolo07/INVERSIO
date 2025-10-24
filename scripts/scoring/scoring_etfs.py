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

# ======================================================
# 🧭 CONFIGURACIÓN DE LOGGING PROFESIONAL
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
# ⚖️ CONFIGURACIÓN GLOBAL BASE DE MÉTRICAS
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
# 🎯 CONFIGURACIÓN DE PESOS DINÁMICOS POR GRUPO (NÚCLEO DEL CAMBIO)
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
    """Carga los datos, limpia NaNs básicos y convierte columnas a tipos numéricos."""
    logger.info("🔍 Preparando datos de entrada...")
    try:
        df = pd.read_csv(path_csv)
    except FileNotFoundError:
        logger.error(f"Error fatal: No se encontró el archivo en {path_csv}")
        return pd.DataFrame()
        
    base_cols = ["Categoría", "Grupo", "Precio", "Costes", "Patrimonio"]
    
    # Obtener todas las claves de METRICS_CONFIG_BASE y DYNAMIC_WEIGHTS para asegurar columnas
    required_metrics = set(METRICS_CONFIG_BASE.keys())
    for weights in DYNAMIC_WEIGHTS.values():
        required_metrics.update(weights.keys())
        
    required_cols = set(list(required_metrics) + base_cols + ["Rent_3Años%", "Rent_5Años%", "Rent_10Años%"])
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan
            
    df = df.dropna(subset=base_cols)
    
    numeric_cols = [col for col in df.columns if 'Rent_' in col or col in ['Precio', 'Patrimonio', 'Costes', 'KID_SRI', 'Sharpe_3Años_Mensual', 'Alfa_3Años_Mensual']]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    logger.info(f"✅ ETFs válidos tras limpieza inicial: {len(df)}")
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
    logger.info("💡 Calculando Rentabilidad Anual Predicha (Extrapolación Ponderada)...")
    
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

# ======================================================
# 🧮 CÁLCULO DE SCORE COMPUESTO Y RANKING (PESOS DINÁMICOS)
# ======================================================
def _calculate_score_by_group(df: pd.DataFrame, grouping_col: str, weights_by_group: dict) -> pd.DataFrame:
    """
    Calcula un score normalizado y ponderado (0-10) por grupo,
    utilizando pesos específicos definidos en weights_by_group.
    """
    score_col_name = f"Score_{grouping_col}"
    rank_col_name = f"Rank_{grouping_col}"
    df[score_col_name] = np.nan

    logger.info(f"⚖️ Calculando scores dinámicos para '{grouping_col}' con pesos específicos...")

    for group_id, group_df in df.groupby(grouping_col):
        # 1. Obtener la configuración de pesos específica para este grupo
        group_weights = weights_by_group.get(group_id, {})
        
        # Combinar con la configuración base para tener todas las métricas
        final_config = METRICS_CONFIG_BASE.copy()
        
        # Aplicar el peso dinámico sobre la base (o usar el peso base si no es dinámico)
        for metric, base_conf in METRICS_CONFIG_BASE.items():
            final_config[metric]['weight'] = group_weights.get(metric, base_conf.get('weight', 1.0)) # 1.0 por defecto
            
        group_indices = group_df.index
        total_weighted_score = pd.Series(0.0, index=group_indices)
        total_applicable_weight = pd.Series(0.0, index=group_indices)
        
        for metric, config in final_config.items():
            # Obtener el peso específico para el grupo
            weight = config['weight']
            direction = config['direction']
            
            group_metric_data = group_df[metric]
            
            if group_metric_data.isna().all():
                continue

            # 1. Normalización (Min-Max Scaling) dentro del grupo
            min_v, max_v = group_metric_data.min(), group_metric_data.max()
            
            if min_v == max_v:
                norm_score = pd.Series(0.5, index=group_indices)
            else:
                norm_score = (group_metric_data - min_v) / (max_v - min_v)
            
            # 2. Dirección
            if direction == 'lower':
                norm_score = 1 - norm_score
            
            # Ponderación y Acumulación Neutral (solo si el ETF tiene el dato)
            has_data_mask = norm_score.notna()
            
            total_weighted_score[has_data_mask] += norm_score[has_data_mask] * weight
            total_applicable_weight[has_data_mask] += weight
            
        # 4. CÁLCULO DEL SCORE FINAL POR ETF
        final_score = total_weighted_score.divide(total_applicable_weight).fillna(np.nan)

        df.loc[group_indices, score_col_name] = final_score

    # 5. Escalado final (0-10) sobre TODOS los scores calculados
    valid_scores = df[score_col_name].dropna()
    if not valid_scores.empty:
        min_score, max_score = valid_scores.min(), valid_scores.max()
        if min_score != max_score:
            df[score_col_name] = (df[score_col_name] - min_score) / (max_score - min_score) * 10
        else:
            df[score_col_name] = 5.0 
    
    df[score_col_name] = df[score_col_name].round(2)
    
    # 6. Ranking
    df[rank_col_name] = df.groupby(grouping_col)[score_col_name].rank(
        ascending=False, method="dense", na_option='bottom'
    ).fillna(0).astype(int)
    
    return df


def calcular_score(df: pd.DataFrame) -> pd.DataFrame:
    """Controlador principal para el cálculo de scores por Categoría y Grupo (con pesos dinámicos)."""
    df_scored = df.copy()
    
    if "Grupo" not in df_scored.columns:
        logger.warning("Columna 'Grupo' no encontrada. Se usará 'Categoría' como 'Grupo'.")
        df_scored["Grupo"] = df_scored["Categoría"]
        
    # Usamos la lógica de pesos dinámicos por Grupo para el ranking de Grupo
    df_scored = _calculate_score_by_group(df_scored, "Grupo", DYNAMIC_WEIGHTS)
    
    # Para el ranking de Categoría, si no tienes una lógica específica, podemos usar un peso promedio o el peso del Grupo 2 (RV Core)
    # Por simplicidad y robustez, usaremos la lógica del Grupo 2 como fallback para la Categoría.
    logger.warning("Usando pesos del GRUPO 2 para el ranking a nivel de 'Categoría'.")
    df_scored = _calculate_score_by_group(df_scored, "Categoría", {cat: DYNAMIC_WEIGHTS.get(2, {}) for cat in df_scored['Categoría'].unique()})
    
    logger.info("✅ Scores y rankings calculados con pesos dinámicos.")
    return df_scored

# ======================================================
# 💾 EXPORTACIÓN DE RESULTADOS (Mantenida de v1.6.5)
# ======================================================
def exportar_resultados(df: pd.DataFrame, n_top: int = 5):
    """
    Exporta el registro maestro completo y los rankings Top N.
    """
    logger.info(f"💾 Exportando resultados completos y Top {n_top}...")

    required_cols = ["Rank_Categoria", "Rank_Grupo", "Score_Categoria", "Score_Grupo", PREDICTED_COL]
    for col in required_cols:
        if col not in df.columns:
            logger.warning(f"La columna '{col}' no existe. Rellenando con 0.0 para exportación.")
            df[col] = 0.0
    
    cols_topn_grupo = ["Nombre", "ISIN", "Grupo", "Rank_Grupo", PREDICTED_COL]

    # 3. Guardar CSV completo (REGISTRO MAESTRO)
    output_file_all = "etfs_scored.csv"
    df_sorted = df.loc[:,~df.columns.duplicated()].copy() 
    df_sorted = df_sorted.sort_values(by=["Categoría", "Rank_Categoria"], ascending=True)
    df_sorted.to_csv(output_file_all, index=False, encoding='utf-8')
    logger.info(f"✅ Archivo completo exportado: {output_file_all}")
    
    # 4. Top N por categoría (Salida completa)
    top_categoria = df[df["Rank_Categoria"] <= n_top].sort_values(
        by=["Categoría", "Rank_Categoria"]
    )
    top_categoria.to_csv("topN_categoria.csv", index=False, encoding='utf-8')

    # 5. Top N por grupo (SALIDA MINIMALISTA SOLICITADA)
    top_grupo_full = df[df["Rank_Grupo"] <= n_top].sort_values(
        by=["Grupo", "Rank_Grupo"]
    )
    # Filtrar solo por las columnas solicitadas
    top_grupo_minimal = top_grupo_full[cols_topn_grupo] 
    
    top_grupo_minimal.to_csv("topN_grupo.csv", index=False, encoding='utf-8')

    logger.info(f"✅ Archivos Top {n_top} exportados (Top por Grupo en formato minimalista).")


# ======================================================
# 🚀 MAIN PIPELINE
# ======================================================
def main():
    """Ejecuta el pipeline completo: Carga -> Extrapolación -> Scoring -> Exportación."""
    logger.info("🚀 Iniciando pipeline de scoring y ranking ETFs")
    
    df = cargar_datos("../limpios/etfs.csv") 
    
    if df.empty:
        logger.error("No se cargaron datos. Abortando pipeline.")
        return
        
    df = extrapolar_rentabilidad_anual(df) 
    
    df = calcular_score(df)
    
    exportar_resultados(df)
    
    logger.info("🎉 Pipeline finalizado con éxito.")

if __name__ == "__main__":
    main()