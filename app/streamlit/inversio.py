import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import textwrap
import streamlit.components.v1 as components
from PIL import Image
import os

# Configuración de la página
st.set_page_config(page_title="Recomendador de ETFs", layout="wide")

# Cargar datos
@st.cache_data
def load_data():
    return pd.read_csv("../recomendador/recomendaciones_clientes.csv")

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
        margin: 10px;                 /* quitar margen para ajustar grid */
        height: 20vh;               /* ocupar todo el alto de la celda */
        width: 100%;               /* ocupar todo el ancho de la celda */
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin: 6px;       /* pequeño margen interno */
        box-sizing: border-box;
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
    # Ruta relativa al archivo; adapta si pones la imagen en otra carpeta
    logo_path = "../../inversio_logo.png"
    if os.path.exists(logo_path):
        logo_img = Image.open(logo_path)
        st.image(logo_img, width=200)  # ajusta ancho según necesites
    else:
        st.markdown("### INVERSIO")  # fallback si falta la imagen

with col_selector:
    clientes_disponibles = sorted(df['ClienteID'].unique())
    cliente_seleccionado = st.selectbox("Seleccionar Cliente:", clientes_disponibles, key="cliente")

# Filtrar datos por cliente
df_cliente = df[df['ClienteID'] == cliente_seleccionado].copy()


####################################################
# COLUMNA IZQUIERDA: Inputs (30%)
####################################################

col_inputs, col_metricas = st.columns([30, 70])

with col_inputs:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Input 1: Tiempo invertido
    st.markdown("""
    <div class='input-label'>⏱️ Tiempo invertido (años)</div>
    """, unsafe_allow_html=True)
    tiempo_anos = st.slider("", 1, 60, 25, key="tiempo", label_visibility="collapsed")
    
    # Input 2: Aportación inicial
    st.markdown("""
    <div class='input-label'>💰 Aportación inicial (€)</div>
    """, unsafe_allow_html=True)
    aportacion_inicial = st.slider("", 100, 100000, 5000, step=100, key="aportacion", label_visibility="collapsed")
    
    # Input 3: Aportación mensual
    st.markdown("""
    <div class='input-label'>📅 Aportación mensual (€)</div>
    """, unsafe_allow_html=True)
    aportacion_mensual = st.slider("", 0, 10000, 100, step=10, key="mensual", label_visibility="collapsed")

####################################################
# COLUMNA DERECHA: Métricas (70%)
####################################################

with col_metricas:
    # Obtener rentabilidad esperada del cliente
    rentabilidad_anual = (df_cliente['Rentabilidad_Esperada_Cliente_%'] * df_cliente['Peso_Asignado']).sum() / 100
    
    # Calcular capital total aportado
    meses = tiempo_anos * 12
    capital_aportado = aportacion_inicial + (aportacion_mensual * meses)
    
    # Calcular capital final con interés compuesto
    # Fórmula: VF = VA(1+r)^n + PMT * [((1+r)^n - 1) / r]
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

    # ajustar proporción interna si quieres una celda más grande: [1.2, 1] por ejemplo
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
# GRÁFICOS (Distribución y Proyección)
####################################################

st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)

col_dist, col_proy = st.columns([1, 2])

with col_dist:
    st.markdown("### 📊 Distribución de inversión")
    
    # Agrupar por grupo y sumar pesos
    grupos_map = {'RF': 'Riesgo bajo', 'RV': 'Riesgo medio', 'Alt': 'Riesgo alto'}
    colores_map = {'Riesgo bajo': '#87CEEB', 'Riesgo medio': '#90EE90', 'Riesgo alto': '#FFB6C1'}
    
    # Orden específico de las categorías
    orden_categorias = ['Riesgo bajo', 'Riesgo medio', 'Riesgo alto']
    
    distribucion = df_cliente.groupby('Grupo')['Peso_Asignado'].sum().reset_index()
    distribucion['Grupo_Nombre'] = distribucion['Grupo'].map(grupos_map)
    distribucion['Porcentaje'] = (distribucion['Peso_Asignado'] * 100).round(0).astype(int)
    
    # Crear figura de barras
    fig_dist = go.Figure()
    
    for idx, row in distribucion.iterrows():
        grupo_nombre = row['Grupo_Nombre']
        color = colores_map[grupo_nombre]
        porcentaje = row['Porcentaje']
        
        # Obtener ETFs de este grupo
        etfs_grupo = df_cliente[df_cliente['Grupo'] == row['Grupo']].copy()
        num_etfs = len(etfs_grupo)
        
        if num_etfs > 0:
            # Crear segmentos para cada ETF con su peso individual
            for etf_idx, (i, etf_row) in enumerate(etfs_grupo.iterrows()):
                peso_etf = etf_row['Peso_Asignado'] * 100
                # Usar nombre real del ETF (acortado para mejor visualización)
                etf_nombre_corto = etf_row['ETF_Nombre'][:30] + '...' if len(etf_row['ETF_Nombre']) > 30 else etf_row['ETF_Nombre']
                
                fig_dist.add_trace(go.Bar(
                    name=etf_nombre_corto,
                    x=[grupo_nombre],
                    y=[peso_etf],
                    marker=dict(
                        color=color,
                        line=dict(color='#000000', width=2),
                        cornerradius=20  # Bordes redondeados
                    ),
                    text=f"<b>{peso_etf:.1f}%</b>",  # Negrita
                    textposition='inside',
                    textfont=dict(size=15, family='Inter',weight='bold'),
                    insidetextanchor='middle',  # Centrado vertical y horizontal
                    hovertemplate=f"<b>{etf_row['ETF_Nombre']}</b><br>ISIN: {etf_row['ETF_ISIN']}<br>Peso: {peso_etf:.1f}%<extra></extra>",
                    showlegend=False
                ))
    
    fig_dist.update_layout(
        barmode='stack',
        height=600,
        margin=dict(l=20, r=20, t=20, b=80),
        xaxis=dict(
            title="",
            categoryorder='array',
            categoryarray=orden_categorias,  # Orden personalizado
            showticklabels=False  # Ocultar etiquetas del eje X
        ),
        yaxis=dict(showticklabels=False, showgrid=False),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Inter'),
        bargap=0.3  # Espacio entre barras
    )
    
    # Añadir etiquetas debajo (solo una vez por categoría)
    etiquetas_agregadas = set()
    for idx, row in distribucion.iterrows():
        if row['Grupo_Nombre'] not in etiquetas_agregadas:
            fig_dist.add_annotation(
                x=row['Grupo_Nombre'],
                y=-7,  # Posición debajo de la barra
                text=f"<b>{row['Porcentaje']}%<br>{row['Grupo_Nombre']}</b>",
                showarrow=False,
                font=dict(size=20, family='Inter', weight='bold', color='black'),
                xref="x",
                yref="y"
            )
            etiquetas_agregadas.add(row['Grupo_Nombre'])
    
    st.plotly_chart(fig_dist, use_container_width=True)

with col_proy:
    st.markdown("### 📈 Proyección de Rentabilidad Esperada")
    
    # Calcular proyección año a año
    proyeccion_anos = []
    proyeccion_valores = []
    
    for ano in range(tiempo_anos + 1):
        meses_transcurridos = ano * 12
        if tasa_mensual > 0:
            vf_inicial = aportacion_inicial * ((1 + tasa_mensual) ** meses_transcurridos)
            if meses_transcurridos > 0:
                vf_mensual = aportacion_mensual * (((1 + tasa_mensual) ** meses_transcurridos - 1) / tasa_mensual)
            else:
                vf_mensual = 0
            valor = vf_inicial + vf_mensual
        else:
            valor = aportacion_inicial + (aportacion_mensual * meses_transcurridos)
        
        proyeccion_anos.append(ano)
        proyeccion_valores.append(valor)
    
    # Crear gráfico de línea
    fig_proy = go.Figure()
    
    fig_proy.add_trace(go.Scatter(
        x=proyeccion_anos,
        y=proyeccion_valores,
        mode='lines+markers',
        line=dict(color='#666', width=2),
        marker=dict(size=8, color='#333'),
        hovertemplate='Año %{x}<br>€%{y:,.0f}<extra></extra>'
    ))
    
    fig_proy.update_layout(
        height=600,  # Altura aumentada
        margin=dict(l=20, r=20, t=20, b=40),
        xaxis_title="AÑOS",
        yaxis_title="€",
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#eee'),
        yaxis=dict(showgrid=True, gridcolor='#eee')
    )
    
    st.plotly_chart(fig_proy, use_container_width=True)