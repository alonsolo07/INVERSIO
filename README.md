# 💼 INVERSIO : Sistema de Recomendación de ETFs

## 🧩 Descripción General

**Inversio** es una herramienta interactiva que recomienda carteras personalizadas de **ETFs** (Exchange-Traded Funds) adaptadas al perfil de riesgo, horizonte temporal y tolerancia del inversor.  
El sistema combina la extracción automatizada de datos financieros desde *Morningstar* con un proceso de análisis, scoring y recomendación, integrando todos los resultados en una interfaz visual desarrollada con **Streamlit**.  

El objetivo es **democratizar la inversión**, facilitando al usuario decisiones informadas y ajustadas a su perfil, mostrando además proyecciones dinámicas de rentabilidad esperada y evolución temporal de su cartera.

---

## 🎯 Objetivos del Proyecto

- Analizar el comportamiento histórico y las características de diferentes ETFs.  
- Calcular métricas de rendimiento y riesgo para clasificarlos en grupos homogéneos.  
- Desarrollar un motor de recomendación que optimice la relación **rentabilidad-riesgo**.  
- Crear una aplicación visual e interactiva que permita al usuario:
  - Simular aportaciones periódicas.
  - Evaluar la rentabilidad proyectada.
  - Visualizar la composición óptima de su cartera.


---

## 📂 Estructura del Proyecto

```
inversio/         
│
├── assets/
│   └── inversio_logo.png            
│
├── data/
│   ├── clientes/
│   │   ├── clientes_base.csv        
│   │   └── clientes_con_pesos.csv   
│   │
│   ├── etf/
│   │   ├── limpios/
│   │   │   └── etfs.csv             
│   │   └── originales/
│   │       ├── etf_general.csv      
│   │       ├── etf_rentabilidad.csv 
│   │       └── etf_riesgo.csv       
│   │
│   ├── recomendador/
│   │   └── recomendaciones_clientes.csv  
│   │
│   └── score/
│       ├── etfs_scored.csv               
│       └── topN_grupo.csv           
│
├── scripts/
│   │
│   ├── clientes/
│   │   ├── generar_clientes.py      
│   │   └── asignar_pesos.py
│   │
│   ├── etf/
│   │   └── cleaner.py              
│   │
│   ├── recomendador/
│   │   └── recomendador.py
│   │
│   ├── scoring/
│   │   └── scoring_etfs.py
│   │
│   └── scrapers/
│       ├── scraper_general.py       
│       ├── scraper_renta.py         
│       └── scraper_riesgo.py        
│
├── .gitignore
├── inversio_test.py
├── inversio.py
├── README.md
├── requirements.txt
├── run_all.py
└── inversio.py
```

---

## 📊 Datos y Fuentes

- **ETFs:** obtenidos automáticamente mediante *web scrapers* desde [Morningstar](https://www.morningstar.es/), con información de rentabilidad, riesgo y métricas generales.  
- **Clientes:** generados sintéticamente para la demostración del sistema. Incluyen variables como edad, sueldo anual, patrimonio, horizonte temporal y tolerancia al riesgo.

---

## 🏗️ Arquitectura del Sistema

```mermaid
flowchart TB
    %% ============================
    %% Estilos mejorados con bordes redondeados
    %% ============================
    classDef proceso fill:#E8D5F2,stroke:#7B2CBF,stroke-width:2.5px,color:#000,font-weight:bold
    classDef limpieza fill:#C7E9FB,stroke:#0077B6,stroke-width:2.5px,color:#000,font-weight:bold
    classDef scoring fill:#FFD6A5,stroke:#FF6B35,stroke-width:2.5px,color:#000,font-weight:bold
    classDef salida fill:#B7E4C7,stroke:#2D6A4F,stroke-width:2.5px,color:#000,font-weight:bold
    classDef cliente fill:#FFB3BA,stroke:#C1121F,stroke-width:2.5px,color:#000,font-weight:bold
    classDef recomendacion fill:#FFE66D,stroke:#F77F00,stroke-width:2.5px,color:#000,font-weight:bold

    %% ============================
    %% Pipeline ETFs
    %% ============================
    subgraph ETF["🏦 ETFs"]
        direction TB
        A([📂 Datos Originales<br/> ETFs Morningstar]):::proceso
        B([🧹 Limpieza y<br/>Normalización]):::limpieza
        C([🔗 Merge Datasets<br/>General + Rentabilidad <br/>+ Riesgo]):::limpieza
        D([⭐ Scoring y Ranking<br/>Dinámico por Grupo]):::scoring
        
        A --> B --> C --> D
    end

    %% ============================
    %% Pipeline Clientes
    %% ============================
    subgraph CLI["👥 CLIENTES"]
        direction TB
        CA([📋 Datos de<br/>Clientes/Perfiles]):::cliente
        CB([🔧 Limpieza y<br/>Preparación]):::cliente
        CC([⚖️ Asignación de Pesos<br/>y Criterios]):::cliente
        
        CA --> CB --> CC
    end

    %% ============================
    %% Sistema de Recomendación
    %% ============================
    F([🎯 Motor de<br/>Recomendación<br/>Personalizada]):::recomendacion
    R([✅ RESULTADO<br/>Recomendaciones<br/>adaptadas al perfil del Cliente]):::salida

    %% ============================
    %% Flujo principal
    %% ============================
    D -.-> F
    CC -.-> F
    F -.-> R

    %% ============================
    %% Notas adicionales
    %% ============================
    style ETF fill:#F8F9FA1A,stroke:#6C757D,stroke-width:2px,stroke-dasharray: 5 5, rx:30,ry:30
    style CLI fill:#F8F9FA1A,stroke:#6C757D,stroke-width:2px,stroke-dasharray: 5 5, rx:30,ry:30

    %% Quitar fondo de etiquetas (contando desde 0)
    %% Links internos: A-->B(0), B-->C(1), C-->D(2), CA-->CB(3), CB-->CC(4)
    %% Links principales: D-.->F(5), CC-.->F(6), F-.->R(7)
    linkStyle 5 fill:none,stroke:#6C757D
    linkStyle 6 fill:none,stroke:#6C757D
```
---

## ⚙️ Flujo de Trabajo

1. **Extracción de datos:**  
   Los scripts de `scrapers/` recogen información actualizada sobre los ETFs desde *Morningstar* (general, rentabilidad, riesgo).

2. **Limpieza y consolidación (`cleaner.py`):**  
   Combina los distintos CSVs y genera un dataset limpio único.

3. **Cálculo de puntuaciones (`scoring_etfs.py`):**  
   Evalúa cada ETF en función de su rentabilidad, volatilidad y métricas adicionales, clasificándolos en tres grupos: **bajo, medio y alto riesgo**.

4. **Generación de clientes (`generar_clientes.py`):**  
   Crea una base sintética de inversores para las pruebas.

5. **Asignación de pesos (`asignar_pesos.py`):**  
   Calcula, para cada cliente, la proporción recomendada de inversión en cada grupo de riesgo.

6. **Recomendación final (`recomendador.py`):**  
   Une las puntuaciones de ETFs con los perfiles de clientes y genera las carteras recomendadas personalizadas.

7. **Visualización interactiva (`inversio.py`):**  
   La aplicación en **Streamlit** permite al usuario:
   - Ajustar el monto invertido y el tiempo de inversión.  
   - Observar la rentabilidad proyectada.  
   - Visualizar la distribución de ETFs y el peso de cada activo en la cartera.

---

## 💻 Instalación y Uso

### 1️⃣ Clonar el repositorio

Ve a la ruta en la que quieras guardar el proyecto

```bash
git clone https://github.com/alonsolara/INVERSIO
cd inversio
```

### 2️⃣ Crear entorno virtual (recomendado)

```bash
python -m venv .venv
source .venv/bin/activate  # En Linux/Mac
.venv\Scripts\activate     # En Windows
```

### 3️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4️⃣ Ejecutar todos los scripts automáticamente

```bash
python run_all.py
```

### 5️⃣ Lanzar la aplicación

Existen dos versiones:

   - Versión de prueba (inversio_test)  
   Permite probar la aplicación mediante un formulario interactivo, con toda la funcionalidad completa.

```bash
streamlit run app/streamlit/inversio_test.py
```

   - Versión completa (inversio)  
   Muestra todos los datos del proyecto, incluyendo gráficos, carteras y simulaciones, y permite seleccionar clientes específicos.

```bash
streamlit run app/streamlit/inversio.py
```

## 🧠 Tecnologías Principales

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| ![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white) | 3.10+ | Lenguaje base del proyecto |
| ![Selenium](https://img.shields.io/badge/Selenium-4.0+-43B02A?style=flat&logo=selenium&logoColor=white) | 4.0+ | Web scraping automatizado |
| ![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat&logo=pandas&logoColor=white) | 2.0+ | Manipulación y análisis de datos |
| ![NumPy](https://img.shields.io/badge/NumPy-1.24+-013243?style=flat&logo=numpy&logoColor=white) | 1.24+ | Cálculos numéricos |
| ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?style=flat&logo=streamlit&logoColor=white) | 1.28+ | Interfaz web interactiva |
| ![Plotly](https://img.shields.io/badge/Plotly-5.0+-3F4F75?style=flat&logo=plotly&logoColor=white) | 5.0+ | Visualizaciones dinámicas |


## 📚 Créditos y Autoría

- **Autor:** Alonso Lara Ordóñez  
- **Contacto:** [linkedin.com/in/alonsolara/](https://www.linkedin.com/in/alonsolara/)