"""
asignar_pesos.py
----------------------------------
Asignación vectorizada de pesos de inversión a clientes sintéticos
para los tres grupos de ETFs: Renta Fija (RF), Renta Variable (RV) y Alternativos (Alt).

Versión: 2.0 - Vectorizada con precisión decimal garantizada
Autor: Sistema de Recomendación ETFs (TFM Project)
Fecha: Octubre 2025

Características:
- Vectorización completa (sin .apply() ni bucles)
- Pesos redondeados a 2 decimales
- Suma garantizada = 1.00 (sin errores de float)
- Límites mínimos: RF ≥ 0.2, RV ≥ 0.2, Alt ≥ 0.1
"""

# ============================================================================ #
# IMPORTS
# ============================================================================ #
import pandas as pd
import numpy as np
import logging
from decimal import Decimal, ROUND_HALF_UP

import sys
import os
# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from settings import CLIENTES_BASE_PATH, CLIENTES_PESOS_PATH

# ============================================================================ #
# CONFIGURACIÓN DE LOGGING
# ============================================================================ #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ============================================================================ #
# CONSTANTES
# ============================================================================ #
PATH_INPUT = CLIENTES_BASE_PATH
PATH_OUTPUT = CLIENTES_PESOS_PATH

# Límites mínimos de asignación
MIN_RF = 0.20   # Renta Fija mínimo 20%
MIN_RV = 0.20   # Renta Variable mínimo 20%
MIN_ALT = 0.10  # Alternativos mínimo 10%

# ============================================================================ #
# FUNCIONES AUXILIARES
# ============================================================================ #

def redondear_decimal(valor: float) -> float:
    """
    Redondea un valor a 2 decimales usando lógica decimal (no float).
    Evita errores de precisión de punto flotante.
    
    Args:
        valor (float): Valor a redondear
    
    Returns:
        float: Valor redondeado a 2 decimales
    """
    return float(Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def normalizar_pesos(pesos: np.ndarray) -> np.ndarray:
    """
    Normaliza array de pesos para que sume exactamente 1.00
    Redondea a 2 decimales y ajusta el máximo para compensar.
    
    Args:
        pesos (np.ndarray): Array de shape (n, 3) con pesos [RF, RV, Alt]
    
    Returns:
        np.ndarray: Pesos normalizados y redondeados
    """
    n = len(pesos)
    pesos_normalizados = np.zeros_like(pesos)
    
    for i in range(n):
        # Redondear cada peso a 2 decimales
        pesos_redondeados = np.array([redondear_decimal(p) for p in pesos[i]])
        
        # Calcular diferencia con 1.00
        suma_actual = sum(pesos_redondeados)
        diferencia = redondear_decimal(1.00 - suma_actual)
        
        # Ajustar el peso máximo para compensar
        if diferencia != 0:
            idx_max = np.argmax(pesos_redondeados)
            pesos_redondeados[idx_max] = redondear_decimal(pesos_redondeados[idx_max] + diferencia)
        
        pesos_normalizados[i] = pesos_redondeados
    
    return pesos_normalizados


# ============================================================================ #
# FUNCIÓN PRINCIPAL DE ASIGNACIÓN
# ============================================================================ #

def asignar_pesos_vectorizado(df: pd.DataFrame) -> pd.DataFrame:
    """
    Asigna pesos de inversión a clientes de forma vectorizada.
    
    Lógica de asignación:
    1. Pesos base según Tolerancia_Riesgo
    2. Ajuste según Horizonte temporal
    3. Aplicación de límites mínimos
    4. Normalización para suma = 1.00
    
    Args:
        df (pd.DataFrame): DataFrame con clientes (requiere columnas Tolerancia_Riesgo y Horizonte)
    
    Returns:
        pd.DataFrame: DataFrame con columnas Peso_RF, Peso_RV, Peso_Alt
    """
    logger.info("🎯 Asignando pesos de inversión a clientes...")
    
    n = len(df)
    
    # Validar columnas requeridas
    if 'Tolerancia_Riesgo' not in df.columns or 'Horizonte' not in df.columns:
        raise ValueError("❌ Columnas requeridas: 'Tolerancia_Riesgo' y 'Horizonte'")
    
    # Inicializar matriz de pesos (n filas × 3 columnas: RF, RV, Alt)
    pesos = np.zeros((n, 3), dtype=float)
    
    # -----------------------------------------------------------------------
    # PASO 1: Asignar pesos base según Tolerancia al Riesgo
    # -----------------------------------------------------------------------
    mask_baja = df["Tolerancia_Riesgo"] == "Baja"
    mask_media = df["Tolerancia_Riesgo"] == "Media"
    mask_alta = df["Tolerancia_Riesgo"] == "Alta"
    
    pesos[mask_baja] = [0.60, 0.30, 0.10]   # Conservador: más RF
    pesos[mask_media] = [0.40, 0.50, 0.10]  # Balanceado: más RV
    pesos[mask_alta] = [0.20, 0.55, 0.25]   # Agresivo: RV + Alt
    
    logger.debug(f"   Pesos base asignados según tolerancia al riesgo")
    
    # -----------------------------------------------------------------------
    # PASO 2: Ajuste por Horizonte temporal
    # -----------------------------------------------------------------------
    mask_corto = df["Horizonte"] == "Corto"
    mask_largo = df["Horizonte"] == "Largo"
    
    # Horizonte Corto: +10% RF, -5% RV, -5% Alt
    pesos[mask_corto, 0] += 0.10  # RF
    pesos[mask_corto, 1] -= 0.05  # RV
    pesos[mask_corto, 2] -= 0.05  # Alt
    
    # Horizonte Largo: -10% RF, +5% RV, +5% Alt
    pesos[mask_largo, 0] -= 0.10  # RF
    pesos[mask_largo, 1] += 0.05  # RV
    pesos[mask_largo, 2] += 0.05  # Alt
    
    logger.debug(f"   Ajustes aplicados por horizonte temporal")
    
    # -----------------------------------------------------------------------
    # PASO 3: Garantizar límites mínimos
    # -----------------------------------------------------------------------
    pesos[:, 0] = np.maximum(pesos[:, 0], MIN_RF)   # RF ≥ 20%
    pesos[:, 1] = np.maximum(pesos[:, 1], MIN_RV)   # RV ≥ 20%
    pesos[:, 2] = np.maximum(pesos[:, 2], MIN_ALT)  # Alt ≥ 10%
    
    logger.debug(f"   Límites mínimos aplicados: RF≥{MIN_RF}, RV≥{MIN_RV}, Alt≥{MIN_ALT}")
    
    # -----------------------------------------------------------------------
    # PASO 4: Normalizar para que sumen exactamente 1.00
    # -----------------------------------------------------------------------
    pesos_finales = normalizar_pesos(pesos)
    
    # -----------------------------------------------------------------------
    # PASO 5: Asignar columnas al DataFrame
    # -----------------------------------------------------------------------
    df = df.copy()
    df["Peso_RF"] = pesos_finales[:, 0]   # Grupo 1 (RF)
    df["Peso_RV"] = pesos_finales[:, 1]  # Grupo 2 (RV)
    df["Peso_Alt"] = pesos_finales[:, 2]   # Grupo 3 (Alt)
    
    # -----------------------------------------------------------------------
    # VALIDACIÓN FINAL
    # -----------------------------------------------------------------------
    suma_pesos = df[["Peso_RF", "Peso_RV", "Peso_Alt"]].sum(axis=1)
    correctos = ((suma_pesos >= 0.99) & (suma_pesos <= 1.01)).sum()
    
    logger.info(f"✅ Pesos asignados correctamente a {len(df)} clientes")
    logger.info(f"   Validación: {correctos}/{n} clientes con suma entre 0.99 y 1.01")
    
    if correctos < n:
        logger.warning(f"   ⚠️ {n - correctos} clientes tienen suma de pesos fuera de rango")
        clientes_problema = df[~((suma_pesos >= 0.99) & (suma_pesos <= 1.01))]['ClienteID'].tolist()
        logger.warning(f"   Clientes con problemas: {clientes_problema[:5]}")
    
    return df


def generar_reporte_pesos(df: pd.DataFrame) -> None:
    """
    Genera reporte estadístico de la distribución de pesos.
    
    Args:
        df (pd.DataFrame): DataFrame con pesos asignados
    """
    logger.info("\n" + "="*70)
    logger.info("📊 REPORTE DE DISTRIBUCIÓN DE PESOS")
    logger.info("="*70)
    
    for col in ["Peso_RF", "Peso_RV", "Peso_Alt"]:
        logger.info(f"\n{col}:")
        logger.info(f"   Media:    {df[col].mean():.2%}")
        logger.info(f"   Mediana:  {df[col].median():.2%}")
        logger.info(f"   Mínimo:   {df[col].min():.2%}")
        logger.info(f"   Máximo:   {df[col].max():.2%}")
    
    logger.info("\n" + "="*70 + "\n")


# ============================================================================ #
# EJECUCIÓN DIRECTA PARA PRUEBA
# ============================================================================ #

def main():
    """
    Ejecuta el pipeline completo de asignación de pesos.
    """
    logger.info("🚀 Iniciando asignación de pesos de inversión...")
    logger.info("="*70)
    
    try:
        # Cargar clientes base
        df_clientes = pd.read_csv(PATH_INPUT)
        logger.info(f"📂 Archivo cargado: {PATH_INPUT} ({len(df_clientes)} clientes)")
        
        # Asignar pesos
        df_clientes = asignar_pesos_vectorizado(df_clientes)
        
        # Generar reporte
        generar_reporte_pesos(df_clientes)
        
        # Exportar resultado
        df_clientes.to_csv(PATH_OUTPUT, index=False, encoding='utf-8')
        logger.info(f"💾 Archivo exportado: {PATH_OUTPUT}")
        logger.info("✅ Pipeline completado exitosamente\n")
        
    except FileNotFoundError:
        logger.error(f"❌ Archivo no encontrado: {PATH_INPUT}")
        logger.error("   Por favor, genera los clientes primero con generar_clientes.py")
    except Exception as e:
        logger.error(f"❌ Error durante la ejecución: {e}")
        raise


if __name__ == "__main__":
    main()