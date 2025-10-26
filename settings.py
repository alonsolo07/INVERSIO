"""
Configuración centralizada de rutas del proyecto Inversio
"""
from pathlib import Path

# Raíz del proyecto (directorio donde está este archivo config/)
ROOT_DIR = Path(__file__).resolve().parent

# Directorios principales
DATA_DIR = ROOT_DIR / "data"
SCRIPTS_DIR = ROOT_DIR / "scripts"
APP_DIR = ROOT_DIR / "app"
ASSETS_DIR = ROOT_DIR / "assets"

# Subdirectorios de data
CLIENTES_DIR = DATA_DIR / "clientes"
ETF_DIR = DATA_DIR / "etf"
RECOMENDADOR_DIR = DATA_DIR / "recomendador"
SCORE_DIR = DATA_DIR / "score"

# Archivos específicos - ETF
ETF_ORIGINALES_DIR = ETF_DIR / "originales"
ETF_LIMPIOS_DIR = ETF_DIR / "limpios"

ETF_GENERAL_PATH = ETF_ORIGINALES_DIR / "etf_general.csv"
ETF_RENTABILIDAD_PATH = ETF_ORIGINALES_DIR / "etf_rentabilidad.csv"
ETF_RIESGO_PATH = ETF_ORIGINALES_DIR / "etf_riesgo.csv"
ETF_LIMPIO_PATH = ETF_LIMPIOS_DIR / "etfs.csv"

CATEGORIAS_PATH = ETF_DIR / 'categorias_distintas.csv'

# Archivos específicos - Clientes
CLIENTES_BASE_PATH = CLIENTES_DIR / "clientes_base.csv"
CLIENTES_PESOS_PATH = CLIENTES_DIR / "clientes_con_pesos.csv"

# Archivos específicos - Scoring
ETFS_SCORED_PATH = SCORE_DIR / "etfs_scored.csv"
TOPN_CATEGORIA_PATH = SCORE_DIR / "topN_categoria.csv"
TOPN_GRUPO_PATH = SCORE_DIR / "topN_grupo.csv"

# Archivos específicos - Recomendaciones
RECOMENDACIONES_PATH = RECOMENDADOR_DIR / "recomendaciones_clientes.csv"

# Assets
LOGO_PATH = ASSETS_DIR / "inversio_logo.png"

# Logging
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)  # Crear si no existe

# Configuración
DEBUG = True