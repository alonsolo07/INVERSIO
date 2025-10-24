"""
==========================================================
ETF DATA CLEANING PIPELINE
==========================================================
Limpia, combina y clasifica los datasets de ETFs.
Autor: Sistema de Recomendación ETFs
Fecha: Octubre 2025
"""

# ============================================================================ #
# IMPORTS
# ============================================================================ #
import pandas as pd
import numpy as np
import requests
import re
import logging
from typing import Dict, Any

# ============================================================================ #
# VARIABLES GLOBALES / RUTAS
# ============================================================================ #
PATH_GENERAL = './originales/etf_general.csv'
PATH_RENTABILIDAD = './originales/etf_rentabilidad.csv'
PATH_RIESGO = './originales/etf_riesgo.csv'
PATH_OUTPUT = 'etfs.csv'
PATH_CATEGORIAS = 'categorias_distintas.csv'

# ============================================================================ #
# CONFIGURACIÓN DE LOGGING
# ============================================================================ #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================================ #
# FUNCIONES AUXILIARES
# ============================================================================ #

def estandarizar_nulos(valor: Any) -> Any:
    """
    Convierte representaciones de nulos a np.nan
    """
    if pd.isna(valor):
        return np.nan
    valor_str = str(valor).strip()
    nulos = ['—', '−', '', 'nan', 'NaN', 'null', 'NULL', 'None']
    if valor_str in nulos:
        return np.nan
    return valor

def limpiar_porcentaje(valor: Any) -> float:
    """
    Convierte string de porcentaje a float (ej: '2,08 %' → 2.08)
    """
    valor = estandarizar_nulos(valor)
    if pd.isna(valor):
        return np.nan
    valor_str = str(valor).replace('−', '-').replace('%', '').replace(' ', '').replace(',', '.')
    try:
        return round(float(valor_str), 2)
    except (ValueError, TypeError):
        return np.nan

def limpiar_numero_europeo(valor: Any) -> float:
    """
    Convierte formato numérico europeo a float (ej: '1.234,56' → 1234.56)
    """
    valor = estandarizar_nulos(valor)
    if pd.isna(valor):
        return np.nan
    valor_str = str(valor).replace('−', '-')
    if '.' in valor_str and ',' in valor_str:
        valor_str = valor_str.replace('.', '').replace(',', '.')
    elif ',' in valor_str:
        valor_str = valor_str.replace(',', '.')
    try:
        return float(valor_str)
    except (ValueError, TypeError):
        return np.nan

def parsear_fecha_espanol(fecha_str: Any) -> pd.Timestamp:
    """
    Convierte fechas en español a formato pd.Timestamp
    """
    fecha_str = estandarizar_nulos(fecha_str)
    if pd.isna(fecha_str):
        return pd.NaT
    meses = {
        'ene':'Jan','feb':'Feb','mar':'Mar','abr':'Apr','may':'May','jun':'Jun',
        'jul':'Jul','ago':'Aug','sep':'Sep','sept':'Sep','oct':'Oct','nov':'Nov','dic':'Dec'
    }
    try:
        partes = str(fecha_str).strip().split()
        if len(partes) == 3:
            dia, mes_esp, anio = partes
            mes_ing = meses.get(mes_esp.lower(), mes_esp)
            fecha_ing = f"{dia} {mes_ing} {anio}"
            return pd.to_datetime(fecha_ing, format='%d %b %Y')
    except Exception:
        logger.debug(f"No se pudo parsear fecha: {fecha_str}")
    return pd.NaT

def normalizar_isin(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza ISINs: mayúsculas, sin espacios, validación y eliminación de duplicados
    """
    if 'ISIN' not in df.columns:
        raise ValueError("❌ Columna ISIN no encontrada en el dataset")
    registros_originales = len(df)
    df['ISIN'] = df['ISIN'].astype(str).str.strip().str.upper()
    patron_isin = r'^[A-Z]{2}[A-Z0-9]{10}$'
    invalidos = ~df['ISIN'].str.match(patron_isin, na=False)
    if invalidos.any():
        logger.warning(f"{invalidos.sum()} ISINs inválidos detectados")
        logger.debug(df[invalidos][['Nombre','ISIN']].head(5))
    duplicados = df.duplicated(subset='ISIN', keep='first')
    if duplicados.any():
        logger.warning(f"{duplicados.sum()} ISINs duplicados eliminados")
        df = df[~duplicados].copy()
    logger.info(f"ISINs procesados: {registros_originales} → {len(df)}")
    return df

def obtener_tipos_cambio() -> Dict[str, float]:
    """
    Obtiene tipos de cambio EUR → otras divisas con respaldo
    """
    try:
        url = "https://api.exchangerate-api.com/v4/latest/EUR"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        rates = resp.json()['rates']
        tipos = {'EUR':1.0,'USD':1/rates['USD'],'GBP':1/rates['GBP'],'CHF':1/rates['CHF'],'JPY':1/rates['JPY']}
        logger.info(f"✅ Tipos de cambio obtenidos (1 EUR ≈ {1/tipos['USD']:.4f} USD)")
        return tipos
    except Exception as e:
        logger.warning(f"⚠️ Error al obtener tipos de cambio: {e}, usando respaldo")
        return {'EUR':1.0,'USD':0.92,'GBP':1.17,'CHF':1.05,'JPY':0.0062}

def normalizar_precio(valor: Any, tipos_cambio: Dict[str,float]) -> float:
    """
    Normaliza precios a EUR desde cualquier divisa (ej: '37,33 US$' → 34.34)
    """
    valor = estandarizar_nulos(valor)
    if pd.isna(valor): return np.nan
    valor_str = str(valor).strip()
    patrones = [
        (r'([\d.,]+)\s*US\$','USD'), (r'([\d.,]+)\s*\$','USD'), (r'([\d.,]+)\s*USD','USD'),
        (r'([\d.,]+)\s*GBP','GBP'), (r'([\d.,]+)\s*GBX','GBX'), (r'([\d.,]+)\s*CHF','CHF'),
        (r'([\d.,]+)\s*JPY','JPY'), (r'([\d.,]+)\s*€','EUR'), (r'([\d.,]+)\s*EUR','EUR')
    ]
    for patron, divisa in patrones:
        match = re.match(patron, valor_str)
        if match:
            numero = limpiar_numero_europeo(match.group(1))
            if pd.isna(numero): return np.nan
            if divisa=='GBX': numero/=100; divisa='GBP'
            return round(numero*tipos_cambio.get(divisa,1.0),2)
    return limpiar_numero_europeo(valor_str)

def normalizar_patrimonio(valor: Any, tipos_cambio: Dict[str,float]) -> float:
    """
    Normaliza patrimonio a EUR (millones o miles de millones)
    """
    valor = estandarizar_nulos(valor)
    if pd.isna(valor): return np.nan
    valor_str = str(valor).strip()
    # Mil millones
    match = re.match(r'([\d.,]+)\s*mil\s*M([A-Z€$]+)', valor_str, re.I)
    if match:
        numero = limpiar_numero_europeo(match.group(1))*1_000_000_000
        divisa = match.group(2).replace('$','USD').replace('€','EUR')
        return round(numero*tipos_cambio.get(divisa,1.0),0)
    # Millones
    match = re.match(r'([\d.,]+)\s*M([A-Z€$]+)', valor_str, re.I)
    if match:
        numero = limpiar_numero_europeo(match.group(1))*1_000_000
        divisa = match.group(2).replace('$','USD').replace('€','EUR')
        return round(numero*tipos_cambio.get(divisa,1.0),0)
    return limpiar_numero_europeo(valor_str)

# ============================================================================ #
# FUNCIONES DE LIMPIEZA DATASETS
# ============================================================================ #

def limpiar_general(filepath:str, tipos_cambio:Dict[str,float]) -> pd.DataFrame:
    """
    Limpia dataset general.csv
    """
    logger.info(f"📄 Cargando {filepath}")
    df = pd.read_csv(filepath)
    cols_eliminar = ["Rendimiento 12 Meses","Medalist Rating","Rating Morningstar para Fondos",
                     "Rating ESG Morningstar Para Fondos","Fecha de creación"]
    df.drop(columns=[c for c in cols_eliminar if c in df.columns], inplace=True)
    df.rename(columns={'Último Precio':'Precio','Categoría Morningstar':'Categoría',
                       'Patrimonio (moneda base)':'Patrimonio','Fecha Patrimonio Fondo':'Fecha',
                       'Costes PRIIPs KID':'Costes'}, inplace=True)
    df = normalizar_isin(df)
    df['Precio'] = df['Precio'].apply(lambda x: normalizar_precio(x,tipos_cambio))
    df['Patrimonio'] = df['Patrimonio'].apply(lambda x: normalizar_patrimonio(x,tipos_cambio))
    df['Costes'] = df['Costes'].apply(limpiar_porcentaje)
    df['Fecha'] = df['Fecha'].apply(parsear_fecha_espanol)
    for col in df.columns:
        if col not in ['ISIN','Nombre','Categoría']:
            df[col] = df[col].apply(estandarizar_nulos)
    logger.info(f"✅ general.csv limpiado: {len(df)} ETFs")
    return df

def limpiar_rentabilidad(filepath:str) -> pd.DataFrame:
    """
    Limpia dataset rentabilidad.csv
    """
    logger.info(f"📄 Cargando {filepath}")
    df = pd.read_csv(filepath)
    df = normalizar_isin(df)
    df.rename(columns={
        'Rent Total 1 Día':'Rent_1Dia%','Rent Total 1 Semana':'Rent_1Semana%',
        'Rent Total 1 Mes':'Rent_1Mes%','Rent Total 3 Meses':'Rent_3Meses%',
        'Rent Total 6 Meses':'Rent_6Meses%','Rent Total Año':'Rent_Año%',
        'Rent Total 1 Año':'Rent_1Año%','Rent Total 3 Años':'Rent_3Años%',
        'Rent Total 5 Años':'Rent_5Años%','Rent Total 10 Años':'Rent_10Años%'
    }, inplace=True)
    for col in [c for c in df.columns if 'Rent' in c]:
        df[col] = df[col].apply(limpiar_porcentaje)
    logger.info(f"✅ rentabilidad.csv limpiado: {len(df)} ETFs")
    return df

def limpiar_riesgo(filepath:str) -> pd.DataFrame:
    """
    Limpia dataset riesgo.csv
    """
    logger.info(f"📄 Cargando {filepath}")
    df = pd.read_csv(filepath)
    df = normalizar_isin(df)
    df.rename(columns={
        'KID SRI':'KID_SRI','Alfa 3 Años, Mensual':'Alfa_3Años_Mensual',
        'Beta 3 Años, Mensual':'Beta_3Años_Mensual','R-cuadrado 3 Años, Mensual':'R2_3Años_Mensual',
        'Volatilidad 3 Años, Mensual':'Volatilidad_3Años_Mensual',
        'Ratio de Sharpe 3 Años, Mensual':'Sharpe_3Años_Mensual'
    }, inplace=True)
    df['KID_SRI'] = pd.to_numeric(df['KID_SRI'].apply(estandarizar_nulos),errors='coerce').astype('Int64')
    for col in ['Alfa_3Años_Mensual','Beta_3Años_Mensual','R2_3Años_Mensual','Volatilidad_3Años_Mensual','Sharpe_3Años_Mensual']:
        df[col] = df[col].apply(limpiar_numero_europeo)
    logger.info(f"✅ riesgo.csv limpiado: {len(df)} ETFs")
    return df

# ============================================================================ #
# MERGE Y CLASIFICACIÓN
# ============================================================================ #

def merge_datasets(df_gen:pd.DataFrame, df_rent:pd.DataFrame, df_ries:pd.DataFrame) -> pd.DataFrame:
    """
    Combina los 3 datasets por ISIN
    """
    df_temp = df_gen.merge(df_rent.drop(columns=['Nombre'],errors='ignore'), on='ISIN',how='inner',validate='one_to_one')
    df_final = df_temp.merge(df_ries.drop(columns=['Nombre'],errors='ignore'), on='ISIN',how='inner',validate='one_to_one')
    logger.info(f"✅ Merge completado: {len(df_final)} ETFs finales")
    return df_final

def exportar_categorias(df:pd.DataFrame)->None:
    """
    Exporta categorías únicas a CSV
    """
    pd.Series(df['Categoría'].unique(), name='Categoría').to_csv(PATH_CATEGORIAS, index=False, encoding='utf-8')
    logger.info(f"✅ Archivo '{PATH_CATEGORIAS}' generado con categorías únicas")

def reclasificar_categorias(df:pd.DataFrame)->pd.DataFrame:
    """
    Reclasifica categorías para el modelo
    """
    categoria_modelo = {
        # Renta Variable
        'Eurozone Large-Cap Equity': 'RV - General',
        'Europe Large-Cap Blend Equity': 'RV - General',
        'US Large-Cap Blend Equity': 'RV - General',
        'Global Large-Cap Blend Equity': 'RV - General',
        'Europe Large-Cap Growth Equity': 'RV - General',
        'Europe Large-Cap Value Equity': 'RV - General',
        'US Large-Cap Growth Equity': 'RV - General',
        'US Large-Cap Value Equity': 'RV - General',
        'Eurozone Flex-Cap Equity': 'RV - General',
        'Europe Flex-Cap Equity': 'RV - General',
        'US Flex-Cap Equity': 'RV - General',
        'Global Flex-Cap Equity': 'RV - General',

        # Emergente
        'Global Emerging Markets Equity': 'RV - Emergente',
        'Global Emerging Markets Small/Mid-Cap Equity': 'RV - Emergente',
        'Asia ex-Japan Equity': 'RV - Emergente',
        'Latin America Equity': 'RV - Emergente',
        'China Equity': 'RV - Emergente',
        'India Equity': 'RV - Emergente',
        'Japan Small/Mid-Cap Equity': 'RV - Emergente',
        'Asia ex-Japan Small/Mid-Cap Equity': 'RV - Emergente',
        'Global Emerging Markets Corporate Bond': 'RV - Emergente',

        # Temáticas / Smart Beta
        'Sector Equity Technology': 'RV - Temáticas',
        'Sector Equity Healthcare': 'RV - Temáticas',
        'Sector Equity Energy': 'RV - Temáticas',
        'Sector Equity Financial Services': 'RV - Temáticas',
        'Sector Equity Consumer Goods & Services': 'RV - Temáticas',
        'Sector Equity Precious Metals': 'RV - Temáticas',
        'Sector Equity Water': 'RV - Temáticas',
        'Sector Equity Biotechnology': 'RV - Temáticas',
        'Sector Equity Agriculture': 'RV - Temáticas',
        'Sector Equity Communications': 'RV - Temáticas',
        'Sector Equity Industrial Materials': 'RV - Temáticas',
        'Sector Equity Utilities': 'RV - Temáticas',
        'Renta Variable Flexible / Smart Beta': 'RV - Temáticas',
        
        # Renta Fija
        'EUR Government Bond - Short Term': 'RF - Bonos Gubernamentales',
        'EUR Government Bond': 'RF - Bonos Gubernamentales',
        'USD Government Bond - Short Term': 'RF - Bonos Gubernamentales',
        'USD Government Bond': 'RF - Bonos Gubernamentales',
        
        'EUR Corporate Bond': 'RF - Bonos Corporativos',
        'EUR High Yield Bond': 'RF - Bonos Corporativos',
        'Global Corporate Bond': 'RF - Bonos Corporativos',
        'Global High Yield Bond': 'RF - Bonos Corporativos',
        
        'EUR Diversified Bond': 'RF - Bonos Mixtos',
        'USD Diversified Bond': 'RF - Bonos Mixtos',
        'Global Diversified Bond': 'RF - Bonos Mixtos',
        'Target Date 2026 - 2030': 'RF - Bonos Mixtos',
        'Target Date 2031 - 2035': 'RF - Bonos Mixtos',
        'Target Date 2036 - 2040': 'RF - Bonos Mixtos',
        
        # Materias Primas
        'Commodities - Industrial & Broad Metals': 'Materias Primas',
        'Commodities - Broad Basket': 'Materias Primas',
        'Commodities - Precious Metals': 'Materias Primas',
        
        # Real Estate
        'Property - Indirect Global': 'Real Estate',
        'Property - Indirect Europe': 'Real Estate',
        'Property - Indirect North America': 'Real Estate',
        'Property - Indirect Asia': 'Real Estate',
        'Property - Indirect Switzerland': 'Real Estate',
        
        # Especiales
        'Options Trading': 'Especiales',
        'Systematic Trend USD': 'Especiales',
        'Convertible Bond - Global': 'Especiales',
        'Currency': 'Especiales',
        # Cualquier otra categoría no listada se clasificará como Especiales
    }
    df['Categoría'] = df['Categoría'].map(categoria_modelo).fillna('Especiales')

    # Asignar grupo numérico (1 = Renta Fija, 2 = Renta Variable, 3 = Alternativos)
    grupo_map = {
        # Renta Variable → grupo 2
        'RV - General': 2,
        'RV - Emergente': 2,
        'RV - Temáticas': 2,
        
        # Renta Fija → grupo 1
        'RF - Bonos Gubernamentales': 1,
        'RF - Bonos Corporativos': 1,
        'RF - Bonos Mixtos': 1,
        
        # Alternativos → grupo 3
        'Materias Primas': 3,
        'Real Estate': 3,
        'Especiales': 3
    }

    df['Grupo'] = df['Categoría'].map(grupo_map).fillna(3).astype(int)

    # Reordenar columnas: colocar 'Grupo' justo después de 'Categoría'
    cols = list(df.columns)
    if 'Categoría' in cols and 'Grupo' in cols:
        idx = cols.index('Categoría') + 1
        cols.insert(idx, cols.pop(cols.index('Grupo')))
        df = df[cols]
    return df

def eliminar_cripto_y_extremos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Elimina ETFs que contengan referencias a cripto, blockchain o similares,
    así como ETFs con rentabilidad a 3 años extremadamente alta (>200%).

    Args:
        df (pd.DataFrame): DataFrame de ETFs original.

    Returns:
        pd.DataFrame: DataFrame filtrado sin ETFs cripto/extremos.
    """
    # Condiciones de exclusión
    condicion_extremos = (
        df['Categoría'].str.contains(
            'Crypto|Cripto|Leverage|Apalanc|Digital Assets|Blockchain|BTC|Solana', case=False, na=False
        ) |
        df['Nombre'].str.contains('Crypto|Cripto|Leverage|Apalanc|Digital Assets|Blockchain|BTC|Solana', case=False, na=False) |
        (df['Rent_3Años%'] > 200)
    )

    # Contar eliminados
    n_eliminados = condicion_extremos.sum()
    total = len(df)
    print(f"✅ Fondos cripto/extremos eliminados: {n_eliminados} de {total} ({n_eliminados/total*100:.2f}%)")

    # Filtrar
    df = df.loc[~condicion_extremos].copy()
    return df

# ============================================================================ #
# PIPELINE PRINCIPAL
# ============================================================================ #

def main():
    tipos_cambio = obtener_tipos_cambio()
    df_general = limpiar_general(PATH_GENERAL, tipos_cambio)
    df_rent = limpiar_rentabilidad(PATH_RENTABILIDAD)
    df_riesgo = limpiar_riesgo(PATH_RIESGO)
    df_final = merge_datasets(df_general, df_rent, df_riesgo)
    df_final = eliminar_cripto_y_extremos(df_final)
    df_final = reclasificar_categorias(df_final)
    exportar_categorias(df_final)
    df_final.to_csv(PATH_OUTPUT, index=False, encoding='utf-8')
    logger.info(f"✅ Pipeline completado. Archivo final '{PATH_OUTPUT}' generado.")

if __name__ == "__main__":
    main()
