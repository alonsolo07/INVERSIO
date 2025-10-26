"""
Script principal para ejecutar todos los módulos del proyecto
en el orden correcto.
"""

import subprocess
import sys
import logging
from pathlib import Path
from tqdm import tqdm

# Configuración logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Directorios principales
ROOT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT_DIR / "scripts"

# Subdirectorios de scripts
SCRAPERS_DIR = SCRIPTS_DIR / "scrapers"
ETF_SCRIPTS_DIR = SCRIPTS_DIR / "etf"
SCORING_SCRIPTS_DIR = SCRIPTS_DIR / "scoring"
CLIENTES_SCRIPTS_DIR = SCRIPTS_DIR / "clientes"
RECOMENDADOR_SCRIPTS_DIR = SCRIPTS_DIR / "recomendador"

# Rutas específicas de los scripts
SCRAPER_GENERAL_PATH = SCRAPERS_DIR / "scraper_general.py"
SCRAPER_RENTABILIDAD_PATH = SCRAPERS_DIR / "scraper_rentabilidad.py"
SCRAPER_RIESGO_PATH = SCRAPERS_DIR / "scraper_riesgo.py"
CLEANER_PATH = ETF_SCRIPTS_DIR / "cleaner.py"
SCORING_PATH = SCORING_SCRIPTS_DIR / "scoring_etfs.py"
GENERAR_CLIENTES_PATH = CLIENTES_SCRIPTS_DIR / "generar_clientes.py"
ASIGNAR_PESOS_PATH = CLIENTES_SCRIPTS_DIR / "asignar_pesos.py"
RECOMENDADOR_PATH = RECOMENDADOR_SCRIPTS_DIR / "recomendador.py"

# Lista de scripts a ejecutar en orden
SCRIPTS = [
    SCRAPER_GENERAL_PATH,
    SCRAPER_RENTABILIDAD_PATH,
    SCRAPER_RIESGO_PATH,
    CLEANER_PATH,
    SCORING_PATH,
    GENERAR_CLIENTES_PATH,
    ASIGNAR_PESOS_PATH,
    RECOMENDADOR_PATH
]

def run_script(script_path: Path):
    """Ejecuta un script de Python y muestra su salida en consola"""
    if not script_path.exists():
        logger.error(f"❌ Script no encontrado: {script_path}")
        return False

    logger.info(f"▶ Ejecutando {script_path.name}...")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False,   # Muestra la salida en tiempo real
        text=True
    )
    if result.returncode == 0:
        logger.info(f"✅ {script_path.name} ejecutado correctamente")
        return True
    else:
        logger.error(f"❌ Error ejecutando {script_path.name}")
        return False

if __name__ == "__main__":
    print("\nEjecutando pipeline completo del proyecto INVERSIO\n")
    for script in tqdm(SCRIPTS, desc="Progreso total", unit="script"):
        success = run_script(script)
        if not success:
            logger.error("Pipeline detenido por error")
            break
    else:
        print("\nPipeline completado exitosamente!")
