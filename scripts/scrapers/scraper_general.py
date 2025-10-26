import os
import pandas as pd
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException


import sys
import os
# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from settings import ETF_GENERAL_PATH


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MorningstarScreenerScraper:
    def __init__(self, headless=True, delay=2.0, output_file="fondos_screener_formato_original.csv", rows_per_page=75):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.delay = delay
        self.output_file = output_file
        self.rows_per_page = rows_per_page
        self.current_page = None
        
        # # Reiniciar CSV cada vez que se ejecute el script
        # if os.path.exists(output_file):
        #     os.remove(output_file)
        #     print(f"Archivo existente '{output_file}' eliminado para reiniciar el scrapeo.")
        
        self.existing_data = pd.DataFrame()
        self.start_page = 1
        print("Iniciando scrapeo desde la página 1.")


    def load_screener_page(self):
        url = "https://global.morningstar.com/es/herramientas/buscador/etfs"
        print(f"Cargando página del screener: {url}")
        self.driver.get(url)
        # Aumentamos tiempo de espera inicial para la carga completa
        time.sleep(self.delay * 5)


    def wait_for_table_update(self):
        """Espera a que la tabla de ETFs se actualice tras cambiar de página."""
        try:
            # Espera a que desaparezca la tabla anterior
            WebDriverWait(self.driver, 10).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.mdc-data-grid-table__mdc table"))
            )
        except TimeoutException:
            pass  # Puede que la tabla no desaparezca visualmente

        time.sleep(self.delay)  # Espera adicional para estabilidad

        try:
            # Espera a que reaparezca la tabla nueva
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.mdc-data-grid-table__mdc table"))
            )
            time.sleep(1)
        except TimeoutException:
            print("⚠ Timeout esperando actualización de tabla tras cambio de página")


    def click_next_button(self):
        try:
            next_buttons = self.driver.find_elements(
                By.XPATH, "//button[contains(., 'Siguiente')]"
            )
            if not next_buttons:
                print("No se encontró el botón Siguiente")
                return False

            next_button = next_buttons[0]
            if next_button.get_attribute("disabled"):
                print("\n-----------------------------------")
                print("Última página alcanzada")
                print("-----------------------------------\n")
                return False

            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            time.sleep(0.5)

            try:
                next_button.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", next_button)

            return True
        except Exception as e:
            print(f"Error al hacer clic en Siguiente: {e}")
            return False


    def scrape_current_page_rows(self):
        wait = WebDriverWait(self.driver, 20)
        try:
            table = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.mdc-data-grid-table__mdc table")
            ))
        except TimeoutException:
            print("Timeout: tabla de ETF´s no encontrada")
            return []

        rows = table.find_elements(By.CSS_SELECTOR, "tr.mdc-data-grid-row__mdc")
        data = []
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td, th")
            if not cells or len(cells) < 2:
                continue

            fund = {}
            try:
                fund['Nombre'] = cells[1].text.strip() if len(cells) > 1 else ""
                fund['ISIN'] = cells[2].text.strip() if len(cells) > 2 else ""
                fund['Último Precio'] = cells[3].text.strip() if len(cells) > 3 else ""
                fund['Rendimiento 12 Meses'] = cells[4].text.strip() if len(cells) > 4 else ""
                fund['Categoría Morningstar'] = cells[5].text.strip() if len(cells) > 5 else ""
                fund['Medalist Rating'] = cells[6].text.strip() if len(cells) > 6 else ""
                fund['Rating Morningstar para Fondos'] = cells[7].text.strip() if len(cells) > 7 else ""
                fund['Rating ESG Morningstar Para Fondos'] = cells[8].text.strip() if len(cells) > 8 else ""
                fund['Patrimonio (moneda base)'] = cells[9].text.strip() if len(cells) > 9 else ""
                fund['Fecha Patrimonio Fondo'] = cells[10].text.strip() if len(cells) > 10 else ""
                fund['Costes PRIIPs KID'] = cells[11].text.strip() if len(cells) > 11 else ""
                fund['Fecha de creación'] = cells[12].text.strip() if len(cells) > 12 else ""

                if fund.get('ISIN') or fund.get('Nombre'):
                    data.append(fund)
            except:
                continue
        return data


    def append_to_csv(self, data):
        df = pd.DataFrame(data)
        if df.empty:
            return

        # # Evita duplicar ISIN
        # if not self.existing_data.empty:
        #     df = df[~df['ISIN'].isin(self.existing_data['ISIN'])]
        # if df.empty:
        #     return

        # Orden correcto de columnas según el formato original
        columns_order = [
            "Nombre",
            "ISIN",
            "Último Precio",
            "Rendimiento 12 Meses",
            "Categoría Morningstar",
            "Medalist Rating",
            "Rating Morningstar para Fondos",
            "Rating ESG Morningstar Para Fondos",
            "Patrimonio (moneda base)",
            "Fecha Patrimonio Fondo",
            "Costes PRIIPs KID",
            "Fecha de creación"
        ]

        # Aseguramos columnas vacías si faltan
        for col in columns_order:
            if col not in df.columns:
                df[col] = ""

        df = df[columns_order]
        # df.rename(columns={"General_2": "General"}, inplace=True)
        if "General_2" in df.columns:
            df.rename(columns={"General_2": "General"}, inplace=True)


        # header = not os.path.exists(self.output_file)
        # df.to_csv(self.output_file, mode='a', index=False, encoding='utf-8-sig', header=header)

        # Acumulamos todo en existing_data
        self.existing_data = pd.concat([self.existing_data, df], ignore_index=True)
        print(f"{len(self.existing_data)} ETF´s")


    def scrape_all_pages(self, max_pages=None):
        self.load_screener_page()
        page_count = 0

        while True:
            page_count += 1
            self.current_page = page_count

            if max_pages and page_count > max_pages:
                break

            print(f"Página {self.current_page}", end=" — ")
            current_data = self.scrape_current_page_rows()
            self.append_to_csv(current_data)

            if not self.click_next_button():
                break
            self.wait_for_table_update()

        print("Proceso completado.")
        print(f"ETF's en CSV: {len(self.existing_data)}")

    def save_csv_final(self):
        if self.existing_data.empty:
            print("No hay datos para guardar.")
            return

        # Reordenar columnas y asegurar el formato
        columns_order = [
            "Nombre",
            "ISIN",
            "Último Precio",
            "Rendimiento 12 Meses",
            "Categoría Morningstar",
            "Medalist Rating",
            "Rating Morningstar para Fondos",
            "Rating ESG Morningstar Para Fondos",
            "Patrimonio (moneda base)",
            "Fecha Patrimonio Fondo",
            "Costes PRIIPs KID",
            "Fecha de creación"
        ]
        for col in columns_order:
            if col not in self.existing_data.columns:
                self.existing_data[col] = ""

        df_out = self.existing_data[columns_order]
        df_out.to_csv(self.output_file, index=False, encoding='utf-8-sig')
        print(f"✅ Archivo final guardado en '{self.output_file}' con {len(df_out)} ETFs.")


    def scrape_to_csv(self, max_pages=None):
        try:
            self.scrape_all_pages(max_pages=max_pages)
            # Guardado final al terminar
            self.save_csv_final()
        finally:
            self.driver.quit()
            # Pequeño delay para liberar recursos antes del siguiente scraper
            time.sleep(5)
            print("Cerrando scraper.")

if __name__ == "__main__":
    scraper = MorningstarScreenerScraper(headless=True, delay=3, output_file=ETF_GENERAL_PATH)
    scraper.scrape_to_csv()
