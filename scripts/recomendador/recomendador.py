"""
=========================================================
RECOMENDADOR DE ETFs DINÁMICO + RENTABILIDAD ESPERADA
=========================================================

Descripción:
------------
Este módulo genera las recomendaciones de ETFs personalizadas
para cada cliente en función de sus pesos por grupo de riesgo (RF, RV, Alt),
e incorpora la rentabilidad esperada de cada ETF y del portfolio completo
de cada cliente.

Estructura:
-----------
1. Carga de datos (clientes + ETFs)
2. Generación dinámica de recomendaciones
3. Cálculo de rentabilidad esperada del cliente
4. Exportación final a un único CSV consolidado

Autor: Sistema de Recomendación ETFs (TFM)
Versión: 1.0
Fecha: Octubre 2025
"""

# ======================================================
# 🔧 Importación de librerías
# ======================================================
import pandas as pd
import logging

# ======================================================
# ⚙️ Configuración de logging
# ======================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ======================================================
# 📂 Carga de datos
# ======================================================
# Clientes: contienen los pesos por grupo (RF, RV, Alt)
# ETFs: contienen su score por grupo y rentabilidad esperada estimada
df_clientes = pd.read_csv("../clientes/clientes_con_pesos.csv")
df_etfs = pd.read_csv("../etf/scorev2/topN_por_grupo.csv")

# Mapeo corto para los grupos
grupo_map = {1: "RF", 2: "RV", 3: "Alt"}
df_etfs["Grupo_Corto"] = df_etfs["Grupo"].map(grupo_map)

# ======================================================
# 🧩 Función principal: recomendación dinámica de ETFs
# ======================================================
def recomendar_etfs_dinamico(clientes: pd.DataFrame, etfs: pd.DataFrame) -> pd.DataFrame:
    """
    Genera recomendaciones personalizadas de ETFs para cada cliente
    según los pesos de sus grupos de riesgo.

    Lógica de asignación:
    ---------------------
    - Si el peso de un grupo >= 3 → se asignan los 2 mejores ETFs.
    - Si el peso < 0.3 → se asigna solo el mejor ETF.
    - El peso del grupo se distribuye equitativamente entre los ETFs asignados.

    Args:
        clientes (pd.DataFrame): DataFrame con pesos de los grupos (Peso_RF, Peso_RV, Peso_Alt)
        etfs (pd.DataFrame): DataFrame con Rank_Grupo y Grupo_Corto

    Returns:
        pd.DataFrame: Recomendaciones con ClienteID, ETF, Grupo, Score y Peso_Asignado
    """
    recomendaciones = []

    # Agrupar los ETFs por grupo y ordenarlos por su score descendente
    etfs_por_grupo = {
        grupo: df_grp.sort_values("Rank_Grupo", ascending=False)
        for grupo, df_grp in etfs.groupby("Grupo_Corto")
    }

    # Iterar sobre cada cliente y generar las asignaciones
    for _, cliente in clientes.iterrows():
        cliente_id = cliente["ClienteID"]

        # Evaluar cada grupo (RF, RV, Alt)
        for grupo in ["RF", "RV", "Alt"]:
            if grupo not in etfs_por_grupo:
                continue

            # ETFs disponibles en el grupo
            top_etfs_df = etfs_por_grupo[grupo]
            peso_grupo = cliente[f"Peso_{grupo}"]

            # Determinar cuántos ETFs asignar según el peso del grupo
            # n_asignar = 2 if peso_grupo >= 0.3 else 1
            
            if peso_grupo > 0.5:
                n_asignar = 3
            elif peso_grupo >= 0.3:
                n_asignar = 2
            else:
                n_asignar = 1

            top_etfs = top_etfs_df.head(n_asignar)
            n_etfs = len(top_etfs)

            if n_etfs == 0:
                continue

            # Distribuir el peso del grupo entre los ETFs seleccionados
            peso_por_etf = round(peso_grupo / n_etfs, 4)

            # Guardar las recomendaciones
            for _, etf in top_etfs.iterrows():
                recomendaciones.append({
                    "ClienteID": cliente_id,
                    "ETF_Nombre": etf["Nombre"],
                    "ETF_ISIN": etf["ISIN"],
                    "Grupo": grupo,
                    "Rank_Grupo": etf["Rank_Grupo"],
                    "Peso_Asignado": peso_por_etf
                })

    # Convertir a DataFrame final
    df_recomendaciones = pd.DataFrame(recomendaciones)
    return df_recomendaciones


# ======================================================
# 📈 Nueva función: cálculo de rentabilidad esperada por cliente
# ======================================================
def agregar_rentabilidad_clientes(df_recomendaciones: pd.DataFrame, df_etfs: pd.DataFrame) -> pd.DataFrame:
    """
    Añade al dataframe de recomendaciones:
    - La rentabilidad esperada individual de cada ETF.
    - La rentabilidad esperada total del portfolio de cada cliente,
      calculada de forma ponderada según los pesos asignados.

    Args:
        df_recomendaciones (pd.DataFrame): Resultado del recomendador dinámico.
        df_etfs (pd.DataFrame): Dataset de ETFs con columna 'Rentabilidad_Anual_Predicha'.

    Returns:
        pd.DataFrame: Recomendaciones con rentabilidad de cada ETF y rentabilidad total del cliente.
    """

    # 🔹 Unir rentabilidad esperada de cada ETF
    df_out = df_recomendaciones.merge(
        df_etfs[['ISIN', 'Rentabilidad_Anual_Predicha']],
        left_on='ETF_ISIN',
        right_on='ISIN',
        how='left'
    )

    # 🔹 Calcular la contribución ponderada del ETF en el portfolio del cliente
    df_out['Contribucion_%'] = df_out['Peso_Asignado'] * df_out['Rentabilidad_Anual_Predicha']

    # 🔹 Calcular rentabilidad esperada total por cliente (suma ponderada)
    rentabilidad_cliente = (
        df_out.groupby('ClienteID')['Contribucion_%']
        .sum()
        .reset_index()
        .rename(columns={'Contribucion_%': 'Rentabilidad_Esperada_Cliente_%'})
    )

    # 🔹 Unir rentabilidad total al dataframe principal
    df_out = df_out.merge(rentabilidad_cliente, on='ClienteID', how='left')

    # 🔹 Limpieza de columnas auxiliares
    df_out.drop(columns=['ISIN'], inplace=True)
    df_out['Rentabilidad_Esperada_Cliente_%'] = df_out['Rentabilidad_Esperada_Cliente_%'].round(2)

    return df_out


# ======================================================
# 🚀 EJECUCIÓN PRINCIPAL (Pipeline completo)
# ======================================================
if __name__ == "__main__":
    logger.info("🚀 Generando recomendaciones dinámicas para clientes...")

    # 1️⃣ Generar recomendaciones base
    df_recomendaciones = recomendar_etfs_dinamico(df_clientes, df_etfs)

    # 2️⃣ Añadir cálculo de rentabilidad esperada (por ETF y cliente)
    df_final = agregar_rentabilidad_clientes(df_recomendaciones, df_etfs)

    # 3️⃣ Guardar el resultado final en un único archivo CSV consolidado
    df_final.to_csv("recomendaciones_clientes.csv", index=False, encoding="utf-8")

    logger.info(f"✅ Archivo final generado con {len(df_final)} filas.")
    logger.info("✅ Proceso completado exitosamente.")