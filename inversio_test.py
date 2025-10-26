import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import os
from decimal import Decimal, ROUND_HALF_UP

from settings import LOGO_PATH, TOPN_GRUPO_PATH

# Configuración de la página
st.set_page_config(page_title="Recomendador de ETFs", layout="wide")

# ===================================
# FUNCIONES DE LÓGICA DE NEGOCIO 
# ===================================

def redondear_decimal(valor: float) -> float:
    """Redondea un valor a 2 decimales usando lógica decimal."""
    return float(Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def normalizar_pesos(pesos: np.ndarray) -> np.ndarray:
    """Normaliza array de pesos para que sume exactamente 1.00"""
    n = len(pesos)
    pesos_normalizados = np.zeros_like(pesos)
    
    for i in range(n):
        pesos_redondeados = np.array([redondear_decimal(p) for p in pesos[i]])
        suma_actual = sum(pesos_redondeados)
        diferencia = redondear_decimal(1.00 - suma_actual)
        
        if diferencia != 0:
            idx_max = np.argmax(pesos_redondeados)
            pesos_redondeados[idx_max] = redondear_decimal(pesos_redondeados[idx_max] + diferencia)
        
        pesos_normalizados[i] = pesos_redondeados
    
    return pesos_normalizados


def asignar_pesos_vectorizado(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna pesos de inversión RF, RV, Alt según perfil del cliente."""
    MIN_RF = 0.20
    MIN_RV = 0.20
    MIN_ALT = 0.10
    
    n = len(df)
    pesos = np.zeros((n, 3), dtype=float)
    
    # Pesos base según Tolerancia al Riesgo
    mask_baja = df["Tolerancia_Riesgo"] == "Baja"
    mask_media = df["Tolerancia_Riesgo"] == "Media"
    mask_alta = df["Tolerancia_Riesgo"] == "Alta"
    
    pesos[mask_baja] = [0.60, 0.30, 0.10]
    pesos[mask_media] = [0.40, 0.50, 0.10]
    pesos[mask_alta] = [0.20, 0.55, 0.25]
    
    # Ajuste por Horizonte temporal
    mask_corto = df["Horizonte"] == "Corto"
    mask_largo = df["Horizonte"] == "Largo"
    
    pesos[mask_corto, 0] += 0.10
    pesos[mask_corto, 1] -= 0.05
    pesos[mask_corto, 2] -= 0.05
    
    pesos[mask_largo, 0] -= 0.10
    pesos[mask_largo, 1] += 0.05
    pesos[mask_largo, 2] += 0.05
    
    # Garantizar límites mínimos
    pesos[:, 0] = np.maximum(pesos[:, 0], MIN_RF)
    pesos[:, 1] = np.maximum(pesos[:, 1], MIN_RV)
    pesos[:, 2] = np.maximum(pesos[:, 2], MIN_ALT)
    
    # Normalizar
    pesos_finales = normalizar_pesos(pesos)
    
    df = df.copy()
    df["Peso_Riesgo Bajo"] = pesos_finales[:, 0]
    df["Peso_Riesgo Medio"] = pesos_finales[:, 1]
    df["Peso_Riesgo Alto"] = pesos_finales[:, 2]

    
    return df

# ======================================================
# FUNCIONES DE RECOMENDACIÓN (de recomendador.py)
# ======================================================

def recomendar_etfs_dinamico(clientes: pd.DataFrame, etfs: pd.DataFrame) -> pd.DataFrame:
    """Genera recomendaciones personalizadas de ETFs para el cliente."""
    recomendaciones = []
    
    # Agrupar ETFs por grupo
    etfs_por_grupo = {
        grupo: df_grp.sort_values("Rank_Grupo", ascending=False)
        for grupo, df_grp in etfs.groupby("Grupo_Corto")
    }
    
    for _, cliente in clientes.iterrows():
        cliente_id = cliente["ClienteID"]
        
        for grupo in ["Riesgo Bajo", "Riesgo Medio", "Riesgo Alto"]:
            if grupo not in etfs_por_grupo:
                continue
            
            top_etfs_df = etfs_por_grupo[grupo]
            peso_grupo = cliente[f"Peso_{grupo}"]
            
            # Determinar cuántos ETFs asignar
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
            
            peso_por_etf = round(peso_grupo / n_etfs, 4)
            
            for _, etf in top_etfs.iterrows():
                recomendaciones.append({
                    "ClienteID": cliente_id,
                    "ETF_Nombre": etf["Nombre"],
                    "ETF_ISIN": etf["ISIN"],
                    "Grupo": grupo,
                    "Rank_Grupo": etf["Rank_Grupo"],
                    "Peso_Asignado": peso_por_etf
                })
    
    return pd.DataFrame(recomendaciones)


def agregar_rentabilidad_clientes(df_recomendaciones: pd.DataFrame, df_etfs: pd.DataFrame) -> pd.DataFrame:
    """Añade rentabilidad esperada de cada ETF y del portfolio total."""
    df_out = df_recomendaciones.merge(
        df_etfs[['ISIN', 'Rentabilidad_Anual_Predicha']],
        left_on='ETF_ISIN',
        right_on='ISIN',
        how='left'
    )
    
    df_out['Contribucion_%'] = df_out['Peso_Asignado'] * df_out['Rentabilidad_Anual_Predicha']
    
    rentabilidad_cliente = (
        df_out.groupby('ClienteID')['Contribucion_%']
        .sum()
        .reset_index()
        .rename(columns={'Contribucion_%': 'Rentabilidad_Esperada_Cliente_%'})
    )
    
    df_out = df_out.merge(rentabilidad_cliente, on='ClienteID', how='left')
    df_out.drop(columns=['ISIN'], inplace=True)
    df_out['Rentabilidad_Esperada_Cliente_%'] = df_out['Rentabilidad_Esperada_Cliente_%'].round(2)
    
    return df_out

# ======================================================
# CARGAR DATOS BASE
# ======================================================

@st.cache_data
def load_etfs():
    """Carga el catálogo de ETFs disponibles."""
    df = pd.read_csv(TOPN_GRUPO_PATH)
    grupo_map = {1: "Riesgo Bajo", 2: "Riesgo Medio", 3: "Riesgo Alto"}
    df["Grupo_Corto"] = df["Grupo"].map(grupo_map)
    return df

df_etfs = load_etfs()

# ======================================================
# CSS PERSONALIZADO
# ======================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
    }
    
    .stApp, .stMarkdown, .stSelectbox, .stSlider, h1, h2, h3, h4, h5, h6, p, div, span, label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif !important;
    }

    .stSlider > div {
        padding: 0 30px !important;
    }
    
    .stSlider > div > div > div > div > div {
        font-size: 1em;
        font-weight: bold;
    }
    
    .stSlider > div > div > div > input {
        color: white;
    }    

    .input-label {
        font-size: 1.2em;
        font-weight: bold;
        color: #333;
        margin: 10px;
        text-align: center;
    }
            
    .metric-box {
        background-color: #f5f5f5;
        border: 5px solid #333;
        border-radius: 20px;
        padding: 10px;
        text-align: center;
        margin: 10px;
        height: 20vh;
        width: 100%;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin: 6px;
    }
            
    .metric-value {
        font-size: 1.8em;
        font-weight: bold;
        color: #333;
    }
    .metric-label {
        font-size: 1.5em;
        color: #666;
    }

    .form-title {
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
        color: #333;
        margin-bottom: 30px;
    }
    
    .form-subtitle {
        text-align: center;
        font-size: 1.2em;
        color: #666;
        margin-bottom: 40px;
    }
    
    .profile-box {
        background-color: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .profile-item {
        font-size: 1.1em;
        margin: 8px 0;
        color: #333;
    }
    
    .profile-label {
        font-weight: bold;
        color: #666;
    }
    
    /* Estilos para radio buttons tipo botón */
    div[data-testid="stHorizontalBlock"] {
        justify-content: center !important;
    }
    
    div[data-testid="stHorizontalBlock"] > div {
        justify-content: center !important;
    }
    
    div[data-testid="stHorizontalBlock"] div[role="radiogroup"] {
        gap: 10px;
        justify-content: center !important;
        display: flex !important;
        width: 100%;
        align-items: center;
    }
    
    div[data-testid="stHorizontalBlock"] div[role="radiogroup"] label {
        background-color: white;
        border: 2px solid #333;
        border-radius: 10px;
        padding: 12px 30px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-weight: 500;
        text-align: center;
        min-width: 120px;
        margin: 0 auto;
    }
    
    div[data-testid="stHorizontalBlock"] div[role="radiogroup"] label:hover {
        background-color: #f0f0f0;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Estilo cuando está seleccionado - fondo gris como hover */
    div[data-testid="stHorizontalBlock"] div[role="radiogroup"] label:has(input:checked) {
        background-color: #f0f0f0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        border-color: #000;
        font-weight: 600;
    }
    
    /* Ocultar el círculo de radio por defecto */
    div[data-testid="stHorizontalBlock"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
        font-size: 1.1em;
    }
            
    .radio-centro {
    display: flex;
    justify-content: center;   /* centra el grupo horizontalmente */
    align-items: center;
    width: 100%;
    margin: 0 auto 10px auto;
    }
</style>
""", unsafe_allow_html=True)

# ======================================================
# INICIALIZAR SESSION STATE
# ======================================================

if 'pagina_actual' not in st.session_state:
    st.session_state.pagina_actual = 'formulario'

# ======================================================
# FUNCIÓN PARA MOSTRAR LOGO
# ======================================================

def mostrar_logo():
    col_logo, col_space = st.columns([1, 4])
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(str(LOGO_PATH), width=200)
        else:
            st.markdown("### INVERSIO")

# ======================================================
# PÁGINA 1: FORMULARIO DE PERFIL DEL CLIENTE
# ======================================================

def pagina_formulario():
    mostrar_logo()
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col_spacer1, col_form, col_spacer2 = st.columns([1, 2, 1])
    
    with col_form:
        st.markdown("<div class='form-title'>🎯 Perfil del Inversor</div>", unsafe_allow_html=True)
        st.markdown("<div class='form-subtitle'>Complete sus datos para obtener recomendaciones personalizadas</div>", unsafe_allow_html=True)
        
        with st.form(key="formulario_perfil", enter_to_submit=False):
            
            # Edad
            st.markdown("<div class='input-label'>👤 Edad</div>", unsafe_allow_html=True)
            edad = st.number_input(
                "Edad:",
                min_value=18,
                max_value=100,
                value=35,
                step=1,
                label_visibility="collapsed"
            )
            
            st.markdown("<b>", unsafe_allow_html=True)
            
            # Sueldo Mensual
            st.markdown("<div class='input-label'>💰 Sueldo Mensual (€)</div>", unsafe_allow_html=True)
            sueldo_mensual_input = st.text_input(
                "Sueldo:",
                value="2500",
                label_visibility="collapsed",
                placeholder="Ej: 2500"
            )
            
            st.markdown("<b>", unsafe_allow_html=True)
            
            # Horizonte de inversión
            st.markdown("<div class='input-label'>⏱️ Horizonte de Inversión</div>", unsafe_allow_html=True)
            
            horizonte = st.selectbox(
                "Selecciona horizonte:",
                options=["Corto", "Medio", "Largo"],
                index=1,
                label_visibility="collapsed"
            )

            st.markdown("<b>", unsafe_allow_html=True)
            
            # Tolerancia al Riesgo
            st.markdown("<div class='input-label'>📊 Tolerancia al Riesgo</div>", unsafe_allow_html=True)

            tolerancia = st.selectbox(
                "Selecciona tolerancia:",
                options=["Baja", "Media", "Alta"],
                index=1,
                label_visibility="collapsed"
            )

            st.markdown("<br>", unsafe_allow_html=True)
            
            submit_button = st.form_submit_button(
                label="🚀 Generar Recomendación",
                use_container_width=True,
                type="primary"
            )
            
            if submit_button:
                # Validar y convertir inputs
                try:
                    sueldo_mensual = int(sueldo_mensual_input.replace(r'\D', ''))
                    
                    if sueldo_mensual < 0:
                        st.error("⚠️ Los valores no pueden ser negativos")
                        return
                    
                except ValueError:
                    st.error("⚠️ Por favor, introduzca valores numéricos válidos")
                    return
                
                # Crear DataFrame temporal con los datos del cliente
                df_cliente_input = pd.DataFrame({
                    'ClienteID': ['DEMO_001'],
                    'Edad': [int(edad)],
                    'Sueldo_Mensual': [sueldo_mensual],
                    'Horizonte': [horizonte],
                    'Tolerancia_Riesgo': [tolerancia]
                })
                
                # Pipeline de procesamiento
                # 1. Asignar pesos
                df_cliente_con_pesos = asignar_pesos_vectorizado(df_cliente_input)
                
                # 2. Generar recomendaciones de ETFs
                df_recomendaciones = recomendar_etfs_dinamico(df_cliente_con_pesos, df_etfs)
                
                # 3. Agregar rentabilidad esperada
                df_final = agregar_rentabilidad_clientes(df_recomendaciones, df_etfs)
                
                # Guardar en session_state
                st.session_state.perfil_cliente = df_cliente_con_pesos.iloc[0].to_dict()
                st.session_state.df_recomendaciones = df_final
                st.session_state.pagina_actual = 'resultados'
                st.rerun()

# ======================================================
# PÁGINA 2: RESULTADOS CON SLIDERS DINÁMICOS
# ======================================================

def pagina_resultados():
    # Recuperar datos del cliente
    perfil = st.session_state.perfil_cliente
    df_cliente = st.session_state.df_recomendaciones
    
    # Header con logo y botón
    col_logo, col_space, col_button = st.columns([1, 7, 1])
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(str(LOGO_PATH), width=200)
        else:
            st.markdown("### INVERSIO")
    
    with col_button:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Nueva Simulación", use_container_width=True, type="secondary"):
            st.session_state.pagina_actual = 'formulario'
            st.rerun()
    
    # ======================================================
    # LAYOUT: COLUMNA IZQUIERDA (PERFIL + SLIDERS)
    # ======================================================
    
    col_inputs, col_metricas = st.columns([30, 70])
    
    with col_inputs:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Mostrar perfil del cliente
        st.markdown("### 👤Perfil del Cliente")
        st.markdown(f"""
        <div class='profile-box'>
            <div class='profile-item'><span class='profile-label'>Edad:</span> {perfil['Edad']} años</div>
            <div class='profile-item'><span class='profile-label'>Sueldo mensual:</span> {perfil['Sueldo_Mensual']/12:,.0f} €</div>
            <div class='profile-item'><span class='profile-label'>Horizonte de inversión:</span> {perfil['Horizonte']}</div>
            <div class='profile-item'><span class='profile-label'>Tolerancia a riesgo:</span> {perfil['Tolerancia_Riesgo']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Sliders dinámicos
        st.markdown("""
        <div class='input-label'>⏱️ Tiempo invertido (años)</div>
        """, unsafe_allow_html=True)
        tiempo_anos = st.slider("", 1, 60, 5, key="tiempo", label_visibility="collapsed")
        
        st.markdown("""
        <div class='input-label'>💰 Aportación inicial (€)</div>
        """, unsafe_allow_html=True)
        aportacion_inicial = st.slider("", 100, 100000, 0, step=100, key="aportacion", label_visibility="collapsed")
        
        st.markdown("""
        <div class='input-label'>📅 Aportación mensual (€)</div>
        """, unsafe_allow_html=True)
        aportacion_mensual = st.slider("", 0, 10000, 100, step=10, key="mensual", label_visibility="collapsed")
    
    # ======================================================
    # COLUMNA DERECHA: MÉTRICAS
    # ======================================================
    
    with col_metricas:
        # Calcular rentabilidad esperada del cliente
        rentabilidad_anual = df_cliente['Rentabilidad_Esperada_Cliente_%'].iloc[0] / 100
        
        # Cálculos financieros
        meses = tiempo_anos * 12
        capital_aportado = aportacion_inicial + (aportacion_mensual * meses)
        
        tasa_mensual = rentabilidad_anual / 12
        if tasa_mensual > 0:
            valor_futuro_inicial = aportacion_inicial * ((1 + tasa_mensual) ** meses)
            valor_futuro_mensual = aportacion_mensual * (((1 + tasa_mensual) ** meses - 1) / tasa_mensual)
            capital_final = valor_futuro_inicial + valor_futuro_mensual
        else:
            capital_final = capital_aportado
        
        ganancia_total = capital_final - capital_aportado
        
        # Grid de métricas 2x2
        st.markdown("<br>", unsafe_allow_html=True)
        
        row1_col1, row1_col2 = st.columns([1, 1])
        row2_col1, row2_col2 = st.columns([1, 1])
        
        row1_col1.markdown(f"""
        <div class='metric-box'>
            <div class='metric-label'>💰 Capital Final Estimado</div>
            <div class='metric-value'>{capital_final:,.0f} €</div>
        </div>
        """, unsafe_allow_html=True)
        
        row1_col2.markdown(f"""
        <div class='metric-box'>
            <div class='metric-label'>📊 Capital Total Aportado</div>
            <div class='metric-value'>{capital_aportado:,.0f} €</div>
        </div>
        """, unsafe_allow_html=True)
        
        row2_col1.markdown(f"""
        <div class='metric-box'>
            <div class='metric-label'>☑️ Rentabilidad Media Esperada</div>
            <div class='metric-value'>{rentabilidad_anual*100:.2f}% anual</div>
        </div>
        """, unsafe_allow_html=True)
        
        row2_col2.markdown(f"""
        <div class='metric-box'>
            <div class='metric-label'>📈 Ganancia Total Estimada</div>
            <div class='metric-value'>{ganancia_total:,.0f} €</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ======================================================
    # GRÁFICOS
    # ======================================================
    
    st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
    
    col_dist, col_data, col_proy = st.columns([1, 1, 2])
    
    with col_dist:
        st.markdown("### 📊 Distribución de inversión")
        
        grupos_map = {
            'Riesgo Bajo': 'Riesgo Bajo',
            'Riesgo Medio': 'Riesgo Medio',
            'Riesgo Alto': 'Riesgo Alto'
        }

        colores_map = {
            'Riesgo Bajo': '#87CEEB',
            'Riesgo Medio': '#90EE90',
            'Riesgo Alto': '#FFB6C1'
        }

        orden_categorias = ['Riesgo Bajo', 'Riesgo Medio', 'Riesgo Alto']

        
        distribucion = df_cliente.groupby('Grupo')['Peso_Asignado'].sum().reset_index()
        distribucion['Grupo_Nombre'] = distribucion['Grupo'].map(grupos_map)
        distribucion['Porcentaje'] = (distribucion['Peso_Asignado'] * 100).round(0).astype(int)
        
        fig_dist = go.Figure()
        
        for idx, row in distribucion.iterrows():
            grupo_nombre = row['Grupo_Nombre']
            color = colores_map[grupo_nombre]
            
            etfs_grupo = df_cliente[df_cliente['Grupo'] == row['Grupo']].copy()
            
            for etf_idx, (i, etf_row) in enumerate(etfs_grupo.iterrows()):
                peso_etf = etf_row['Peso_Asignado'] * 100
                etf_nombre_corto = etf_row['ETF_Nombre'][:30] + '...' if len(etf_row['ETF_Nombre']) > 30 else etf_row['ETF_Nombre']
                
                fig_dist.add_trace(go.Bar(
                    name=etf_nombre_corto,
                    x=[grupo_nombre],
                    y=[peso_etf],
                    marker=dict(
                        color=color,
                        line=dict(color='#000000', width=2),
                        cornerradius=15
                    ),
                    text=f"<b>{peso_etf:.1f}%</b>",
                    textposition='inside',
                    textfont=dict(size=13, family='Inter', weight='bold'),
                    insidetextanchor='middle',
                    hovertemplate=f"<b>{etf_row['ETF_Nombre']}</b><br>ISIN: {etf_row['ETF_ISIN']}<br>Peso: {peso_etf:.1f}%<extra></extra>",
                    showlegend=False
                ))
        
        fig_dist.update_layout(
            barmode='stack',
            height=700,
            margin=dict(l=20, r=20, t=20, b=80),
            xaxis=dict(
                title="",
                categoryorder='array',
                categoryarray=orden_categorias,
                showticklabels=False
            ),
            yaxis=dict(showticklabels=False, showgrid=False),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Inter'),
            bargap=0.4,
        )
        
        etiquetas_agregadas = set()
        for idx, row in distribucion.iterrows():
            if row['Grupo_Nombre'] not in etiquetas_agregadas:
                fig_dist.add_annotation(
                    x=row['Grupo_Nombre'],
                    y=-7,
                    text=f"<b>{row['Porcentaje']}%<br>{row['Grupo_Nombre']}</b>",
                    showarrow=False,
                    font=dict(size=15, family='Inter', weight='bold', color='black'),
                    xref="x",
                    yref="y"
                )
                etiquetas_agregadas.add(row['Grupo_Nombre'])
        
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col_data:
        
        # Definir orden de grupos
        orden_grupos = ["Riesgo Bajo", "Riesgo Medio", "Riesgo Alto"]
        df_cliente['Grupo'] = pd.Categorical(df_cliente['Grupo'], categories=orden_grupos, ordered=True)

        # Ordenar por grupo y luego por Peso_Asignado descendente
        df_etfs_ordenado = df_cliente.sort_values(['Grupo', 'Peso_Asignado'], ascending=[True, False])
        
        for idx, etf in df_etfs_ordenado.iterrows():
            peso_porcentaje = etf['Peso_Asignado'] * 100
            cantidad_invertir_inicial = aportacion_inicial * etf['Peso_Asignado']
            cantidad_invertir_mes = aportacion_mensual * etf['Peso_Asignado']
            grupo_nombre = grupos_map[etf['Grupo']]
            color_grupo = colores_map[grupo_nombre]
            
            st.markdown(f"""
            <div style='
                background-color: white;
                border-left: 5px solid {color_grupo};
                border-radius: 5px;
                padding: 12px;
                margin-bottom: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            '>
                <div style='font-weight: bold; font-size: 0.95em; color: #333; margin-bottom: 8px;'>
                    {etf['ETF_Nombre']}
                </div>
                <div style='font-size: 0.85em; color: #666; margin-bottom: 4px;'>
                    <strong>ISIN:</strong> {etf['ETF_ISIN']}
                </div>
                <div style='font-size: 0.85em; color: #666; margin-bottom: 4px;'>
                    <strong>Peso / Rentabilidad estimada:</strong> {peso_porcentaje:.1f}% / {etf['Rentabilidad_Anual_Predicha']:.2f}% anual
                </div>
                <div style='font-size: 0.85em; color: #666;'>
                    <strong>Inversión inicial / mensual:</strong> {cantidad_invertir_inicial:,.2f} € / {cantidad_invertir_mes:,.2f} €
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col_proy:
        st.markdown("### 📈 Proyección de Rentabilidad Esperada")
        
        # Convertir la rentabilidad anual a mensual
        r_month = (1 + rentabilidad_anual) ** (1/12) - 1
        
        # Asumimos volatilidad mensual proporcional (simplificación)
        # σ = 2*sqrt(12)*tasa_mensual como aproximación ±2σ
        sigma_month = 0.01  # Ajusta según tus datos si deseas
        
        proyeccion_anos = list(range(tiempo_anos + 1))
        proy_base = []
        proy_plus = []
        proy_minus = []

        for ano in proyeccion_anos:
            meses = ano * 12
            def valor_futuro(ap_ini, ap_mensual, tasa, meses):
                if meses == 0:
                    return ap_ini
                if abs(tasa) > 1e-12:
                    vf_inicial = ap_ini * ((1 + tasa) ** meses)
                    vf_mensual = ap_mensual * (((1 + tasa) ** meses - 1) / tasa)
                    return vf_inicial + vf_mensual
                else:
                    return ap_ini + ap_mensual * meses

            proy_base.append(valor_futuro(aportacion_inicial, aportacion_mensual, r_month, meses))
            proy_plus.append(valor_futuro(aportacion_inicial, aportacion_mensual, r_month + 2*sigma_month, meses))
            proy_minus.append(valor_futuro(aportacion_inicial, aportacion_mensual, max(r_month - 2*sigma_month, -0.9999), meses))

        # Crear figura con banda sombreada
        fig_proy = go.Figure()

        # Banda ±2σ
        fig_proy.add_trace(go.Scatter(
            x=proyeccion_anos + proyeccion_anos[::-1],
            y=proy_plus + proy_minus[::-1],
            fill='toself',
            fillcolor='rgba(100,100,100,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo='skip',
            showlegend=True,
            name='Intervalo ±2σ'
        ))

        # Línea central
        fig_proy.add_trace(go.Scatter(
            x=proyeccion_anos,
            y=proy_base,
            mode='lines+markers',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6),
            name='Proyección central',
            hovertemplate='Año %{x}<br>€%{y:,.2f}<extra></extra>'
        ))

        # Líneas superior e inferior
        fig_proy.add_trace(go.Scatter(
            x=proyeccion_anos,
            y=proy_plus,
            mode='lines',
            line=dict(color='rgba(31,119,180,0.4)', width=1, dash='dash'),
            name='+2σ'
        ))
        fig_proy.add_trace(go.Scatter(
            x=proyeccion_anos,
            y=proy_minus,
            mode='lines',
            line=dict(color='rgba(31,119,180,0.4)', width=1, dash='dash'),
            name='-2σ'
        ))

        fig_proy.update_layout(
            height=600,
            margin=dict(l=20, r=20, t=20, b=40),
            xaxis_title="AÑOS",
            yaxis_title="€",
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='#eee'),
            yaxis=dict(showgrid=True, gridcolor='#eee'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )

        st.plotly_chart(fig_proy, use_container_width=True)


# ======================================================
# NAVEGACIÓN PRINCIPAL
# ======================================================

if st.session_state.pagina_actual == 'formulario':
    pagina_formulario()
else:
    pagina_resultados()