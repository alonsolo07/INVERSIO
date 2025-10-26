import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import textwrap
import streamlit.components.v1 as components
from PIL import Image
import os

from settings import LOGO_PATH, RECOMENDACIONES_PATH

# Configuración de la página
st.set_page_config(page_title="Recomendador de ETFs", layout="wide")

# Cargar datos
@st.cache_data
def load_data():
    return pd.read_csv(RECOMENDACIONES_PATH)

df = load_data()

# CSS personalizado
st.markdown("""
<style>
            
    /* Importar fuente profesional */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Aplicar fuente a toda la aplicación */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
    }
    
    /* Aplicar fuente a elementos específicos de Streamlit */
    .stApp, .stMarkdown, .stSelectbox, .stSlider, h1, h2, h3, h4, h5, h6, p, div, span, label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif !important;
    }

    /* Añadir margen a las barras del slider para hacerlas más cortas */
    .stSlider > div {
        padding: 0 30px !important;
    }
    
    /* Estilizar el thumb (botón deslizante) */
    .stSlider > div > div > div > div > div {
        font-size: 1em;
        font-weight: bold;
    }
    
    /* Estilizar el texto de valor del slider */
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

    .percentage-label {
        font-size: 1.8em;
        font-weight: bold;
        color: #d32f2f;
        text-align: center;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Header con logo y selector de cliente
col_logo, col_a, col_selector = st.columns([1, 2, 1])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(str(LOGO_PATH), width=200)
    else:
        st.markdown("### INVERSIO")

with col_selector:
    clientes_disponibles = sorted(df['ClienteID'].unique())
    cliente_seleccionado = st.selectbox("Seleccionar Cliente:", clientes_disponibles, key="cliente")

# Filtrar datos por cliente
df_cliente = df[df['ClienteID'] == cliente_seleccionado].copy()


####################################################
# COLUMNA IZQUIERDA: Inputs
####################################################

col_inputs, col_metricas = st.columns([30, 70])

with col_inputs:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Input 1: Tiempo invertido
    st.markdown("""
    <div class='input-label'>⏱️ Tiempo invertido (años)</div>
    """, unsafe_allow_html=True)
    tiempo_anos = st.slider("", 1, 60, 5, key="tiempo", label_visibility="collapsed")
    
    # Input 2: Aportación inicial
    st.markdown("""
    <div class='input-label'>💰 Aportación inicial (€)</div>
    """, unsafe_allow_html=True)
    aportacion_inicial = st.slider("", 100, 100000, 1000, step=100, key="aportacion", label_visibility="collapsed")
    
    # Input 3: Aportación mensual
    st.markdown("""
    <div class='input-label'>📅 Aportación mensual (€)</div>
    """, unsafe_allow_html=True)
    aportacion_mensual = st.slider("", 0, 10000, 100, step=10, key="mensual", label_visibility="collapsed")

####################################################
# COLUMNA DERECHA: Métricas
####################################################

with col_metricas:
    # Obtener rentabilidad esperada del cliente
    rentabilidad_anual = df_cliente['Rentabilidad_Esperada_Cliente_%'].iloc[0] / 100
    
    # Calcular capital total aportado
    meses = tiempo_anos * 12
    capital_aportado = aportacion_inicial + (aportacion_mensual * meses)
    
    # Calcular capital final con interés compuesto
    tasa_mensual = rentabilidad_anual / 12
    if tasa_mensual > 0:
        valor_futuro_inicial = aportacion_inicial * ((1 + tasa_mensual) ** meses)
        valor_futuro_mensual = aportacion_mensual * (((1 + tasa_mensual) ** meses - 1) / tasa_mensual)
        capital_final = valor_futuro_inicial + valor_futuro_mensual
    else:
        capital_final = capital_aportado
    
    ganancia_total = capital_final - capital_aportado

    # ======================================================
    # MÉTRICAS PRINCIPALES (2x2)
    # ======================================================

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


####################################################
# GRÁFICOS (Distribución, Datos y Proyección)
####################################################

st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)

col_dist, col_data, col_proy = st.columns([1, 1, 2])

with col_dist:
    st.markdown("### 📊 Distribución de inversión")
    
    grupos_map = {'RF': 'Riesgo Bajo', 'RV': 'Riesgo Medio', 'Alt': 'Riesgo Alto'}
    colores_map = {'Riesgo Bajo': '#87CEEB', 'Riesgo Medio': '#90EE90', 'Riesgo Alto': '#FFB6C1'}
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
    df_cliente['Grupo_Nombre'] = df_cliente['Grupo'].map(grupos_map)
    df_cliente['Grupo_Nombre'] = pd.Categorical(df_cliente['Grupo_Nombre'], categories=orden_grupos, ordered=True)

    # Ordenar por grupo y luego por Peso_Asignado descendente
    df_etfs_ordenado = df_cliente.sort_values(['Grupo_Nombre', 'Peso_Asignado'], ascending=[True, False])
    
    for idx, etf in df_etfs_ordenado.iterrows():
        peso_porcentaje = etf['Peso_Asignado'] * 100
        cantidad_invertir_inicial = aportacion_inicial * etf['Peso_Asignado']
        cantidad_invertir_mes = aportacion_mensual * etf['Peso_Asignado']
        grupo_nombre = etf['Grupo_Nombre']
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