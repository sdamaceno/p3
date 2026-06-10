import streamlit as st

def load():
    st.markdown("""
    <style>
        ::-webkit-scrollbar { width: 6px; height: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
        
        [data-testid="stDataFrame"] { overflow-x: auto !important; width: 100% !important; }
        
        /* Botões Padronizados - Texto Forçado Branco e 300 weight */
        .stButton > button { 
            background-color: #0F2C4C !important; 
            border: none !important; 
            border-radius: 4px !important; 
            width: 100% !important; 
            padding: 4px 10px !important; 
            min-height: 38px !important; 
            transition: background-color 0.2s ease !important;
        }
        .stButton > button p, .stButton > button span {
            color: #FFFFFF !important;
            font-weight: 300 !important;
            font-size: 12pt !important;
        }
        .stButton > button:hover { background-color: #0B223D !important; }
        
        /* Uploader */
        [data-testid="stFileUploader"] > section { 
            background-color: #0F2C4C !important; border: none !important; border-radius: 4px !important; padding: 0px !important; min-height: 38px !important; height: 38px !important; display: flex !important; align-items: center !important; justify-content: center !important; cursor: pointer !important; transition: background-color 0.2s ease !important; box-shadow: none !important; 
        }
        [data-testid="stFileUploader"] > section:hover { background-color: #0B223D !important; }
        [data-testid="stFileUploader"] > section > div, [data-testid="stFileUploader"] > section button, [data-testid="stFileUploader"] > section small, [data-testid="stFileUploader"] > section span, [data-testid="stFileUploader"] > section svg { display: none !important; }
        [data-testid="stFileUploader"] > section::after { content: 'Enviar arquivo' !important; color: white !important; font-weight: 300 !important; font-size: 12pt !important; }
        
        /* TRANSFORMAÇÃO DO TOGGLE EM EXPANDER VISUAL */
        [data-testid="stToggle"] {
            background-color: transparent;
            margin-bottom: 5px;
        }
        [data-testid="stToggle"] label {
            width: 100%; cursor: pointer; display: flex; align-items: center;
        }
        [data-testid="stToggle"] [data-baseweb="checkbox"] > div:first-child { 
            display: none !important; /* Esconde a "chavinha" nativa */
        }
        [data-testid="stToggle"] [data-baseweb="checkbox"] p {
            font-weight: 300 !important; color: #0F2C4C !important; font-size: 14pt !important; display: flex; align-items: center;
        }
        /* Injeção do Chevron via CSS com fonte estrutural para não quebrar no Linux/Web */
        [data-testid="stToggle"] [data-baseweb="checkbox"] p::before {
            content: '▶';
            font-family: "Segoe UI Symbol", "DejaVu Sans", sans-serif !important;
            font-size: 10pt !important; margin-right: 10px; color: #0F2C4C; transition: transform 0.2s;
        }
        [data-testid="stToggle"] [data-baseweb="checkbox"] input:checked ~ div p::before {
            content: '▼';
        }
        
        /* Métricas e Tabelas Alinhadas a 300 Weight */
        .metric-card { background: white; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; text-align: center; border-top: 4px solid #B08D55; display: flex; flex-direction: column; justify-content: center; }
        .metric-val { font-size: 18pt; font-weight: 300; color: #0F2C4C; letter-spacing: -0.5px; }
        .metric-lbl { font-size: 10pt; color: #64748B; text-transform: uppercase; margin-bottom: 2px; font-weight: 300; }
        .total-global-compact { background-color: #E6F2FF; padding: 10px 20px; border-radius: 4px; border-left: 4px solid #0F2C4C; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; margin-top: 5px; }
        .total-global-title { margin: 0; color: #0F2C4C; font-size: 12pt; font-weight: 300; text-transform: uppercase; }
        .total-global-value { margin: 0; color: #0F2C4C; font-size: 18pt; font-weight: 300; letter-spacing: -0.5px; }
        .item-row { border-bottom: 1px solid #E2E8F0; padding: 4px 0; margin-bottom: 2px; display: flex; align-items: center; font-size: 12pt; }
    </style>
    """, unsafe_allow_html=True)

def button_primary(label, key=None, use_container_width=True, **kwargs): return st.button(label, key=key, type="primary", use_container_width=use_container_width, **kwargs)
def button_secondary(label, key=None, use_container_width=True, **kwargs): return st.button(label, key=key, use_container_width=use_container_width, **kwargs)
def form_submit_button(label, key=None, type="secondary", use_container_width=False, **kwargs): return st.form_submit_button(label, key=key, type=type, use_container_width=use_container_width, **kwargs)
def file_uploader(key, **kwargs): return st.file_uploader("Upload", type=["xlsx", "xls", "ods", "csv", "pdf", "docx", "doc", "odt", "md", "txt"], key=key, label_visibility="collapsed", **kwargs)
def text_area(value, placeholder, key, height=250, **kwargs): return st.text_area(f"ta_{key}", value=value, height=height, label_visibility="collapsed", placeholder=placeholder, key=key, **kwargs)
def text_input(label, value, key, placeholder="", disabled=False, **kwargs): return st.text_input(label, value=value, key=key, placeholder=placeholder, disabled=disabled, **kwargs)
def number_input(label, value=0.0, key=None, min_value=None, max_value=None, **kwargs): return st.number_input(label, value=value, key=key, min_value=min_value, max_value=max_value, **kwargs)
def selectbox(label, options, key=None, index=0, format_func=str, **kwargs): return st.selectbox(label, options=options, key=key, index=index, format_func=format_func, **kwargs)
def slider(label, min_value, max_value, value, step, format_str, key, **kwargs): return st.slider(label, min_value=min_value, max_value=max_value, value=value, step=step, format=format_str, key=key, **kwargs)
def toggle(label, value, key, **kwargs): return st.toggle(label, value=value, key=key, **kwargs)

# Correção da largura baseada na nova API do Streamlit
def data_editor(df, column_config, key=None, **kwargs): return st.data_editor(df, num_rows="dynamic", width="stretch", column_config=column_config, key=key, **kwargs)

def dataframe(df, column_config=None, **kwargs):
    if column_config: st.dataframe(df, hide_index=True, width="stretch", column_config=column_config, **kwargs)
    else: st.dataframe(df, hide_index=True, width="stretch", **kwargs)

def render_metric_card(label, value): return f"<div class='metric-card'><div class='metric-lbl'><strong>{label}</strong></div><div class='metric-val'>{value}</div></div>"
def render_total_global(label, value): st.markdown(f"<div class='total-global-compact'><div class='total-global-title'><strong>{label}</strong></div><div class='total-global-value'>{value}</div></div>", unsafe_allow_html=True)
def render_table_header(col_lote, col_desc, col_status, col_acoes): st.markdown(f"<div style='background-color:#0F2C4C; color:white; padding:6px 8px; border-radius:4px; font-weight:300; display:flex; margin-bottom: 8px;'><div style='flex:1; margin-right:8px;'>{col_lote}</div><div style='flex:4; margin-right:8px;'>{col_desc}</div><div style='flex:1.5; margin-right:8px;'>{col_status}</div><div style='flex:3;'>{col_acoes}</div></div>", unsafe_allow_html=True)
def render_item_row_start(): return "<div class='item-row'>"
def render_status_badge(pronto, valor_formatado, lbl_pendente): return f"<span style='font-weight:300; color:green;'><span class='glyph'>✔</span> {valor_formatado}</span>" if pronto else f"<span style='font-weight:300; color:#64748B;'>{lbl_pendente}</span>"