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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MorningstarRiesgoScraper:
    def __init__(self, headless=True, delay=2.0, output_file="fondos_riesgo.csv", rows_per_page=75):
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
        
        self.existing_data = pd.read_csv(output_file) if os.path.exists(output_file) else pd.DataFrame()
        self.start_page = (len(self.existing_data) // rows_per_page) + 1 if not self.existing_data.empty else 1
        print(f"ETF´s existentes: {len(self.existing_data)}. Reanudando en página {self.start_page}.")

    def load_screener_page(self):
        url = "https://global.morningstar.com/es/herramientas/buscador/etfs"
        print(f"Cargando página del screener: {url}")
        self.driver.get(url)
        time.sleep(self.delay * 2)

    def close_cookies_banner(self):
        try:
            accept_button = self.driver.find_element(By.CSS_SELECTOR, "button#onetrust-accept-btn-handler")
            accept_button.click()
            time.sleep(1)
            print("Banner de cookies cerrado")
        except Exception:
            pass

    def select_inversor_individual(self):
        try:
            button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='select-role-individual']"))
            )
            button.click()
            time.sleep(2)
            print("Overlay de tipo de inversor cerrado")
        except TimeoutException:
            pass

    def wait_for_overlays_to_disappear(self):
        try:
            WebDriverWait(self.driver, 10).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.mdc-role-selection__overlay__mdc"))
            )
            print("Overlays bloqueantes desaparecieron")
        except TimeoutException:
            pass

    def select_view(self, view_name="Riesgo"):
        try:
            dropdown_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.mdc-tools-view-selector__views-button__mdc"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", dropdown_button)
            dropdown_button.click()
            time.sleep(1)

            options = self.driver.find_elements(By.CSS_SELECTOR, "div.mdc-list-group-item__text__mdc")
            for option in options:
                if view_name in option.text:
                    option.click()
                    time.sleep(2)
                    print(f"Vista '{view_name}' seleccionada")
                    return
            print(f"No se encontró la opción '{view_name}'")
        except Exception as e:
            print(f"Error al seleccionar vista {view_name}: {e}")

    def wait_for_table_update(self):
        time.sleep(self.delay)
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.mdc-data-grid-table__mdc table"))
            )
        except TimeoutException:
            print("Timeout esperando actualización de tabla")

    def click_next_button(self):
        try:
            next_buttons = self.driver.find_elements(
                By.XPATH, "//button[contains(.//span[@class='mdc-button__content__mdc'], 'Siguiente')]"
            )
            if not next_buttons:
                print("No se encontró el botón Siguiente")
                return False

            next_button = next_buttons[0]
            if next_button.get_attribute("disabled"):
                print("\n-----------------------------------")
                print("Ultima página alcanzada")
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
                if len(cells) > 1: fund['Nombre'] = cells[1].text.strip()
                if len(cells) > 2: fund['ISIN'] = cells[2].text.strip()
                if len(cells) > 3: fund['KID SRI'] = cells[3].text.strip()
                if len(cells) > 4: fund['Alfa 3 Años, Mensual'] = cells[4].text.strip()
                if len(cells) > 5: fund['Beta 3 Años, Mensual'] = cells[5].text.strip()
                if len(cells) > 6: fund['R-cuadrado 3 Años, Mensual'] = cells[6].text.strip()
                if len(cells) > 7: fund['Volatilidad 3 Años, Mensual'] = cells[7].text.strip()
                if len(cells) > 8: fund['Ratio de Sharpe 3 Años, Mensual'] = cells[8].text.strip()
                if fund.get('Nombre') or fund.get('ISIN'):
                    data.append(fund)
            except:
                continue
        return data

    def append_to_csv(self, data):
        df = pd.DataFrame(data)
        if df.empty:
            return
        if not self.existing_data.empty:
            df = df[~df['ISIN'].isin(self.existing_data['ISIN'])]
        if df.empty:
            return

        header = not os.path.exists(self.output_file)
        df.to_csv(self.output_file, mode='a', index=False, encoding='utf-8-sig', header=header)
        self.existing_data = pd.concat([self.existing_data, df], ignore_index=True)
        print(f"{len(self.existing_data)} ETF´s guardados")

    def jump_to_start_page(self):
        if self.start_page <= 1:
            return
        print(f"Avanzando hasta la página {self.start_page}...")
        current_page = 1
        while current_page < self.start_page:
            if not self.click_next_button():
                break
            self.wait_for_table_update()
            current_page += 1
        print(f"Ahora en página {current_page}")

    def scrape_all_pages(self, max_pages=None):
        self.load_screener_page()
        self.close_cookies_banner()
        self.select_inversor_individual()
        self.wait_for_overlays_to_disappear()
        self.select_view("Riesgo")
        self.jump_to_start_page()
        page_count = self.start_page - 1

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

    def scrape_to_csv(self, max_pages=None):
        try:
            self.scrape_all_pages(max_pages=max_pages)
        finally:
            self.driver.quit()
            print("Cerrando scraper.")

if __name__ == "__main__":
    scraper = MorningstarRiesgoScraper(headless=True, delay=3, output_file="etf_riesgo.csv")
    scraper.scrape_to_csv()
