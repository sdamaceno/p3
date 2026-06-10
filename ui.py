import streamlit as st # type: ignore[import]
from texts import get_text

TJ_BLUE = "#0F2C4C"
TJ_GOLD = "#B08D55"
TEXT_MAIN = "#1E293B"
BG_MAIN = "#F8FAFC"

def carregar_estilos():
    st.markdown(f"""
    <style>
        :root {{ --tj-blue: {TJ_BLUE}; --tj-gold: {TJ_GOLD}; --text-main: {TEXT_MAIN}; }}
        
        html, body, [class*="css"], input, textarea, button {{ 
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", Arial, sans-serif !important; 
            color: var(--text-main); 
            background-color: {BG_MAIN}; 
        }}
        
        h1, h2, h3, h4, h5 {{ font-weight: 700; letter-spacing: -0.5px; margin-bottom: 4px; }}
        footer {{visibility: hidden; display: none;}}
        
        /* Layout de Tela Cheia Controlada */
        .block-container {{ padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 1600px !important; margin: 0 auto; }}
        header[data-testid="stHeader"] {{ display: none !important; }}
        [data-testid="stSidebar"] {{ display: none !important; }}
        .stApp {{ margin-top: 0px; }}
        
        ::-webkit-scrollbar {{ width: 6px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: #CBD5E1; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #94A3B8; }}
        
        [data-testid="stDataFrame"] {{ overflow-x: auto !important; width: 100% !important; }}
        
        /* Customização Estrita do File Uploader para Casar com o Botão Primário */
        [data-testid="stFileUploader"] > section {{
            background-color: var(--tj-blue) !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 0px !important;
            min-height: 38px !important;
            height: 38px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            transition: background-color 0.2s ease !important;
            box-shadow: none !important;
        }}
        [data-testid="stFileUploader"] > section:hover {{
            background-color: #0B223D !important;
        }}
        
        [data-testid="stFileUploader"] > section > div,
        [data-testid="stFileUploader"] > section button,
        [data-testid="stFileUploader"] > section small,
        [data-testid="stFileUploader"] > section span,
        [data-testid="stFileUploader"] > section svg {{ display: none !important; }}
        
        [data-testid="stFileUploader"] > section::after {{
            content: 'Enviar' !important;
            color: white !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }}
        
        /* Cabeçalho Limpo SAM */
        .sam-header {{ background: #FFFFFF; padding: 20px 2rem; margin-top: -1rem; margin-left: -2rem; margin-right: -2rem; border-bottom: 1px solid #E2E8F0; box-shadow: 0 2px 4px -1px rgba(0,0,0,0.05); margin-bottom: 25px; text-align: center; }}
        .sam-title {{ font-weight: 800; font-size: 24px; color: var(--tj-blue); letter-spacing: -0.5px; }}
        
        /* Redução de espaçamentos para compactação máxima */
        .stButton > button {{ background-color: var(--tj-blue); color: white; border: none; border-radius: 4px; font-weight: 600; width: 100%; padding: 4px 10px; min-height: 35px; transition: background-color 0.2s ease; }}
        .stButton > button:hover {{ background-color: #0B223D; color: white; }}
        
        div[data-testid="column"] {{ padding-bottom: 0px !important; }}
        
        .tit-contratacao h3 {{ color: var(--tj-blue); font-weight: 800; font-size: 20px; margin-bottom: 5px; }}
        .tit-grupo h4 {{ color: var(--tj-blue) !important; font-weight: 700 !important; font-size: 15px !important; margin: 0px !important; padding: 0px !important; }}
        
        .section-title {{ font-size: 13px; font-weight: 700; color: #64748B; margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .lbl-upload {{ font-size: 14px; color: #1E293B; margin-bottom: 8px; font-weight: 600; }}
        
        .metric-card {{ background: white; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; text-align: center; border-top: 4px solid var(--tj-gold); display: flex; flex-direction: column; justify-content: center; }}
        .metric-val {{ font-size: 18px; font-weight: 800; color: var(--tj-blue); letter-spacing: -0.5px; }}
        .metric-lbl {{ font-size: 10px; color: #64748B; text-transform: uppercase; margin-bottom: 2px; font-weight: 700; }}
        
        .total-global-compact {{ background-color: #E6F2FF; padding: 10px 20px; border-radius: 4px; border-left: 4px solid {TJ_BLUE}; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; margin-top: 5px; }}
        .total-global-title {{ margin: 0; color: {TJ_BLUE}; font-size: 14px; font-weight: 800; text-transform: uppercase; }}
        .total-global-value {{ margin: 0; color: {TJ_BLUE}; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }}
        
        .item-row {{ border-bottom: 1px solid #E2E8F0; padding: 4px 0; margin-bottom: 2px; display: flex; align-items: center; font-size: 13px; }}
        
        @media (max-width: 768px) {{
            .total-global-compact {{ flex-direction: column; align-items: flex-start; gap: 5px; }}
        }}
    </style>
    """, unsafe_allow_html=True)

def renderizar_cabecalho():
    st.markdown(f"""
    <div class="sam-header">
        <div class="sam-title">{get_text("NOME_SISTEMA")}</div>
    </div>
    """, unsafe_allow_html=True)

def renderizar_metricas_estatisticas(media_formatada, amostras, maior_valor_formatado):
    l1_c1, l1_c2, l1_c3 = st.columns(3)
    l1_c1.markdown(f"<div class='metric-card'><div class='metric-lbl'>{get_text('LBL_PRECO_FINAL')}</div><div class='metric-val'>{media_formatada}</div></div>", unsafe_allow_html=True)
    l1_c2.markdown(f"<div class='metric-card'><div class='metric-lbl'>{get_text('LBL_AMOSTRAS')}</div><div class='metric-val'>{amostras}</div></div>", unsafe_allow_html=True)
    l1_c3.markdown(f"<div class='metric-card'><div class='metric-lbl'>{get_text('LBL_MAIOR_VALOR')}</div><div class='metric-val'>{maior_valor_formatado}</div></div>", unsafe_allow_html=True)

def renderizar_total_global(valor_formatado):
    st.markdown(f"""
    <div class='total-global-compact'>
        <div class='total-global-title'>{get_text('VALOR_TOTAL_GLOBAL')}</div>
        <div class='total-global-value'>{valor_formatado}</div>
    </div>
    """, unsafe_allow_html=True)

def renderizar_cabecalho_lista_itens():
    st.markdown("<div style='background-color:#0F2C4C; color:white; padding:6px 8px; border-radius:4px; font-weight:bold; display:flex; font-size: 13px; margin-bottom: 8px;'>", unsafe_allow_html=True)
    c_h1, c_h2, c_h3, c_h4 = st.columns([1, 4, 1.5, 3], gap="small")
    c_h1.write(get_text("COL_LOTE"))
    c_h2.write(get_text("COL_DESC"))
    c_h3.write(get_text("COL_STATUS"))
    c_h4.write(get_text("COL_ACOES"))
    st.markdown("</div>", unsafe_allow_html=True)

def gerar_html_linha_item():
    return f"<div class='item-row'>"

def render_status_badge(pronto, valor_formatado=""):
    if pronto:
        return f"<span style='color:green; font-weight:bold;'>✔ {valor_formatado}</span>"
    return f"<span style='color:#64748B;'>{get_text('BADGE_PENDENTE')}</span>"