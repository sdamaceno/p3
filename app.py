import streamlit as st
import pandas as pd
import requests
import concurrent.futures
import time
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import base64

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Consulta de Preços - Análise de Mercado",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuração do Fuso Horário (Brasília/Goiânia: UTC-3)
fuso_br = timezone(timedelta(hours=-3))

# Funções de Formatação de Moeda Brasileira
def formatar_moeda_simples(valor):
    try:
        formatted = f"{float(valor):,.2f}"
        return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def formatar_moeda_ordenavel(valor):
    try:
        val_f = float(valor)
        s = f"{val_f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s.rjust(15, ' ')}"
    except:
        return "R$ " + "0,00".rjust(15, ' ')

# --- 2. CSS & DESIGN (COMPACTO E MONOCROMÁTICO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Inter:wght@400;500&display=swap');

    :root {
        --tj-blue: #0F2C4C;      
        --tj-gold: #B08D55;      
        --text-main: #1E293B;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: var(--text-main);
        background-color: #F8FAFC;
    }
    
    h1, h2, h3, h4, h5 { font-family: 'Plus Jakarta Sans', sans-serif; }

    footer {visibility: hidden;}
    .block-container { padding-top: 1.5rem !important; padding-bottom: 100px !important; }

    /* CABEÇALHO NATIVO E BOTÃO SANDUÍCHE */
    header[data-testid="stHeader"] { background-color: transparent !important; box-shadow: none !important; }
    header[data-testid="stHeader"] > div:not(:first-child) { display: none !important; }

    [data-testid="collapsedControl"] {
        position: fixed !important; top: 25px !important; left: 20px !important;
        background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important; width: 45px !important; height: 45px !important;
        z-index: 999999 !important; box-shadow: 0 2px 5px rgba(0,0,0,0.08) !important;
        transition: all 0.2s ease; display: flex !important; align-items: center !important; justify-content: center !important;
    }
    [data-testid="collapsedControl"]:hover { background-color: #F1F5F9 !important; border-color: var(--tj-blue) !important; }
    [data-testid="collapsedControl"] svg { display: none !important; }
    [data-testid="collapsedControl"]::after {
        content: ''; display: block; width: 24px; height: 24px; background-color: var(--tj-blue);
        -webkit-mask: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>') no-repeat center;
        mask: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>') no-repeat center;
    }

    [data-testid="stSidebar"] { background-color: #F8FAFC; border-right: 1px solid #E2E8F0; }

    .stApp { margin-top: 0px; }

    .tj-header {
        background: #FFFFFF; padding: 20px 5rem 20px 85px; margin-top: -1.5rem; 
        margin-left: -5rem; margin-right: -5rem; border-bottom: 1px solid #E2E8F0;
        display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .tj-logo-text { font-family: 'Plus Jakarta Sans'; font-weight: 700; font-size: 18px; color: var(--tj-blue); line-height: 1.2; }
    .tj-sub { font-weight: 400; font-size: 13px; color: #64748B; border-left: 1px solid #CBD5E1; padding-left: 10px; margin-left: 10px; }

    .hero-container {
        background: linear-gradient(180deg, #E6F2FF 0%, #FFFFFF 100%); padding: 40px 5rem;
        margin-left: -5rem; margin-right: -5rem; text-align: center; border-bottom: 1px solid #F1F5F9; margin-bottom: 30px;
    }
    .hero-title { color: var(--tj-blue); font-size: 32px; font-weight: 800; margin-bottom: 5px; }

    .metric-card {
        background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 15px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); text-align: center; transition: transform 0.2s;
        border-top: 4px solid var(--tj-gold); height: 100%; display: flex; flex-direction: column; justify-content: center;
    }
    .metric-card-secondary { border-top: 4px solid #64748B; background-color: #F8FAFC; }
    .metric-val { font-size: 20px; font-weight: 700; color: var(--tj-blue); }
    .metric-lbl { font-size: 11px; color: #64748B; text-transform: uppercase; margin-bottom: 4px; font-weight: 600; }

    .stButton > button { background-color: var(--tj-blue); color: white; border: none; border-radius: 6px; font-weight: 600; width: 100%; }
    .stButton > button:hover { background-color: #0B223D; color: white; }

    .tj-footer {
        position: fixed; bottom: 0; left: 0; width: 100%; background-color: var(--tj-blue);
        color: white; text-align: center; padding: 20px 0; font-size: 12px; z-index: 1000; box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.1);
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 600; }
    
    /* Tabelas e Totais Compactos */
    .compact-table-container { margin-bottom: 0px; }
    .subtotal-lote { text-align: right; font-weight: 600; color: #64748B; margin-bottom: 15px; margin-top: 5px; font-size: 14px; }
    .lote-header { margin-top: 5px !important; margin-bottom: 5px !important; color: #0F2C4C;}
    
    /* Bloco de Valor Total em uma linha */
    .total-global-compact {
        background-color: #E6F2FF; padding: 15px 25px; border-radius: 6px; 
        border-left: 5px solid #0F2C4C; display: flex; justify-content: space-between; 
        align-items: center; margin-bottom: 15px; margin-top: 10px;
    }
    .total-global-title { margin: 0; color: #0F2C4C; font-size: 16px; font-weight: 700; text-transform: uppercase; }
    .total-global-value { margin: 0; color: #0F2C4C; font-size: 26px; font-weight: 800; }

    @media (max-width: 768px) {
        .tj-header, .hero-container { margin-left: -1rem; margin-right: -1rem; padding-left: 80px; padding-right: 1rem; }
        .total-global-compact { flex-direction: column; align-items: flex-end; }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. MEMÓRIA DE SESSÃO E MENU LATERAL ---
if 'dados_brutos' not in st.session_state:
    st.session_state['dados_brutos'] = pd.DataFrame()
if 'termo_pesquisado' not in st.session_state:
    st.session_state['termo_pesquisado'] = ""
if 'df_edicao' not in st.session_state:
    st.session_state['df_edicao'] = pd.DataFrame()
if 'filter_hash' not in st.session_state:
    st.session_state['filter_hash'] = ""
if 'step2_ready' not in st.session_state:
    st.session_state['step2_ready'] = False
if 'todos_marcados' not in st.session_state:
    st.session_state['todos_marcados'] = True
if 'lotes_contratacao' not in st.session_state:
    st.session_state['lotes_contratacao'] = {}

def toggle_todos():
    val = st.session_state['chk_todos_ui']
    st.session_state['todos_marcados'] = val
    if not st.session_state['df_edicao'].empty:
        st.session_state['df_edicao']['Válido?'] = val

with st.sidebar:
    st.markdown("### Filtros de Pesquisa")
    
    st.text_input("Considerar Preços:", value="Apenas Homologados", disabled=True)
    tipos_permitidos = ["Homologado"] 
    
    regra_calculo = st.selectbox(
        "Parâmetro de Cálculo",
        ["Preços válidos - Mediana ±25% e Média"]
    )
    
    st.markdown("---")
    
    meses_corte = st.slider("Período de Pesquisa", min_value=12, max_value=60, value=24, step=6, format="%d meses")
    paginas = st.number_input("Volume de Busca (Páginas)", min_value=1, max_value=5, value=3)

# --- 4. ENGINE DE PESQUISA ---
class PNCPEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        })

    def buscar_editais(self, termo, paginas):
        base_url = "https://pncp.gov.br/api/search/"
        editais = []
        busca_api = termo.replace('"', '').replace("'", "")
        for p in range(1, paginas + 1):
            params = {"q": busca_api, "tipos_documento": "edital", "ordenacao": "-dataPublicacaoPncp", "pagina": str(p), "tam_pagina": "50"}
            try:
                resp = self.session.get(base_url, params=params, timeout=10)
                if resp.status_code == 200:
                    items = resp.json().get('items', [])
                    if not items: break
                    editais.extend(items)
                else: break
            except: break
        return editais

    def _obter_valor_homologado_robusto(self, cnpj, ano, seq, item):
        val_homologado = item.get("valorUnitarioHomologado")
        if val_homologado and float(val_homologado) > 0: return float(val_homologado)
        num_item = item.get("numeroItem")
        url_resultado = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{num_item}/resultados"
        try:
            res_resultado = self.session.get(url_resultado, timeout=3)
            if res_resultado.status_code == 200:
                for r in res_resultado.json():
                    val = r.get("valorUnitarioHomologado")
                    if val and float(val) > 0: return float(val)
        except: pass
        situacao = str(item.get("situacaoCompraItem", ""))
        if situacao in ['4', '6']:
            val_fallback = item.get("valorUnitario")
            if val_fallback and float(val_fallback) > 0: return float(val_fallback)
        return 0.0

    def minerar_itens(self, edital, termo_busca):
        try:
            orgao = edital.get("orgao", {})
            cnpj = edital.get("orgao_cnpj") or edital.get("cnpj")
            razao = edital.get("orgao_nome") or edital.get("razaoSocial") or "N/D"
            ano = edital.get("ano")
            seq = edital.get("numero_sequencial")
            data_pub = edital.get("data_publicacao_pncp")[:10]
            if not (cnpj and ano and seq): return []
            link_audit = f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"
            url_itens = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens"
            resp = self.session.get(url_itens, timeout=10)
            itens = []
            if resp.status_code == 200:
                termos_chave = termo_busca.lower().split()
                for item in resp.json():
                    desc = str(item.get("descricao", "")).lower()
                    if all(t in desc for t in termos_chave):
                        val_h = self._obter_valor_homologado_robusto(cnpj, ano, seq, item)
                        if val_h > 0:
                            itens.append({
                                "Data": datetime.strptime(data_pub, "%Y-%m-%d").strftime("%d/%m/%Y"),
                                "Órgão": razao.upper(),
                                "Item": item.get("descricao"),
                                "Qtd": item.get("quantidade"),
                                "Preço": float(val_h), 
                                "Valor Unitário": formatar_moeda_ordenavel(val_h), 
                                "Link PNCP": link_audit 
                            })
            return itens
        except: return []

# --- 5. ESTATÍSTICA ---
def processar_precos_regra(df, regra):
    if df.empty: return df, pd.DataFrame(), 0, 0, 0
    if regra == "Preços válidos - Mediana ±25% e Média":
        mediana_geral = df['Preço'].median()
        limite_inferior = mediana_geral * 0.75
        limite_superior = mediana_geral * 1.25
        df_validos = df[(df['Preço'] >= limite_inferior) & (df['Preço'] <= limite_superior)].copy()
        df_outliers = df[(df['Preço'] < limite_inferior) | (df['Preço'] > limite_superior)].copy()
        return df_validos, df_outliers, mediana_geral, limite_inferior, limite_superior

def ordenar_validos(df):
    if df.empty: return df
    return df.sort_values(by=['Preço'])

def ordenar_outliers(df):
    if df.empty: return df
    idx_max = df['Preço'].idxmax()
    idx_min = df['Preço'].idxmin()
    row_max = df.loc[[idx_max]]
    if idx_max == idx_min: return row_max
    row_min = df.loc[[idx_min]]
    restante = df.drop([idx_max, idx_min], errors='ignore')
    return pd.concat([row_max, row_min, restante])

# --- LÓGICA DE EXCLUSIVIDADE "SEM LOTE" ---
tem_sem_lote = "Sem Lote" in st.session_state['lotes_contratacao']
tem_com_lote = any(k != "Sem Lote" for k in st.session_state['lotes_contratacao'].keys())

if tem_sem_lote:
    opcoes_agrupamento = ["Sem Lote"]
    idx_padrao = 0
    desabilitar_agrup = True
elif tem_com_lote:
    opcoes_agrupamento = ["Agrupar em Lotes"]
    idx_padrao = 0
    desabilitar_agrup = True
else:
    opcoes_agrupamento = ["Agrupar em Lotes", "Sem Lote"]
    idx_padrao = 0
    desabilitar_agrup = False

# --- 6. RENDERIZAÇÃO DA INTERFACE ---

st.markdown("""
<div class="tj-header">
    <div style="display:flex; align-items:center;">
        <div>
            <div class="tj-logo-text">PODER JUDICIÁRIO</div>
            <div class="tj-logo-text" style="font-weight:400; font-size:14px;">Tribunal de Justiça do Estado de Goiás</div>
        </div>
    </div>
    <div class="tj-sub">
        <strong>Sistema de Apoio à Licitação</strong><br>
        Base PNCP (Filtro Inteligente)
    </div>
</div>
<div class="hero-container">
    <div class="hero-title">Consulta de Preços - Análise de Mercado</div>
    <div class="hero-subtitle">Mineração com validação em cascata, curadoria técnica e composição de lotes</div>
</div>
""", unsafe_allow_html=True)

total_itens_carrinho = sum(len(lista) for lista in st.session_state['lotes_contratacao'].values())
tab_pesquisa, tab_lote = st.tabs([
    "Pesquisa Individual de Itens", 
    f"Resumo da Contratação ({total_itens_carrinho} itens)"
])

with tab_pesquisa:
    with st.form(key='search_form'):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            termo = st.text_input("Qual item você deseja pesquisar?", placeholder="Ex: Monitor 24 polegadas, Papel Sulfite A4...", label_visibility="collapsed")
        with col_btn:
            btn_buscar = st.form_submit_button("Pesquisar")

    if btn_buscar and termo:
        engine = PNCPEngine()
        with st.status("Localizando editais na base nacional...", expanded=True) as status:
            editais = engine.buscar_editais(termo, paginas)
            
            if not editais:
                status.update(label="Nenhum edital encontrado.", state="error")
                st.session_state['dados_brutos'] = pd.DataFrame() 
            else:
                st.write("Editais encontrados. Executando extração de preços (Apenas Homologados)...")
                all_items = []
                bar = st.progress(0)
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    futures = {executor.submit(engine.minerar_itens, ed, termo): ed for ed in editais}
                    done = 0
                    for f in concurrent.futures.as_completed(futures):
                        res = f.result()
                        if res: all_items.extend(res)
                        done += 1
                        bar.progress(done / len(editais))
                bar.empty()
                
                if not all_items:
                    status.update(label="Itens não encontrados com o status exigido.", state="error")
                    st.session_state['dados_brutos'] = pd.DataFrame()
                else:
                    status.update(label="Mineração concluída!", state="complete")
                    df_raw = pd.DataFrame(all_items)
                    
                    try:
                        df_raw['dt'] = pd.to_datetime(df_raw['Data'], format="%d/%m/%Y", errors='coerce')
                        limite_data = datetime.now(fuso_br) - relativedelta(months=meses_corte)
                        df_raw['dt'] = df_raw['dt'].dt.tz_localize(fuso_br)
                        df_pre_filtro = df_raw[(df_raw['dt'] >= limite_data)].copy()
                        df_pre_filtro = df_pre_filtro.drop(columns=['dt'])
                    except:
                        df_pre_filtro = df_raw.copy()
                    
                    if not df_pre_filtro.empty:
                        _, _, _, lim_inf_pre, lim_sup_pre = processar_precos_regra(df_pre_filtro, regra_calculo)
                        if lim_inf_pre > 0 or lim_sup_pre > 0:
                            df_pre_filtro.insert(0, "Válido?", (df_pre_filtro['Preço'] >= lim_inf_pre) & (df_pre_filtro['Preço'] <= lim_sup_pre))
                        else:
                            df_pre_filtro.insert(0, "Válido?", True)
                    else:
                        df_pre_filtro.insert(0, "Válido?", True)

                    st.session_state['dados_brutos'] = df_raw
                    st.session_state['termo_pesquisado'] = termo
                    st.session_state['df_edicao'] = df_pre_filtro
                    st.session_state['filter_hash'] = f"{meses_corte}_{regra_calculo}"
                    st.session_state['step2_ready'] = False
                    st.session_state['todos_marcados'] = True
                    st.rerun()

    if not st.session_state['dados_brutos'].empty:
        
        df_edicao = st.session_state['df_edicao']
        termo_atual = st.session_state['termo_pesquisado']
        
        current_hash = f"{meses_corte}_{regra_calculo}"
        if st.session_state['filter_hash'] != current_hash:
            st.session_state['filter_hash'] = current_hash
            st.session_state['step2_ready'] = False
            
            df_raw = st.session_state['dados_brutos'].copy()
            try:
                df_raw['dt'] = pd.to_datetime(df_raw['Data'], format="%d/%m/%Y", errors='coerce')
                limite_data = datetime.now(fuso_br) - relativedelta(months=meses_corte)
                df_raw['dt'] = df_raw['dt'].dt.tz_localize(fuso_br)
                df_new = df_raw[(df_raw['dt'] >= limite_data)].copy()
                df_new = df_new.drop(columns=['dt'])
            except:
                df_new = df_raw.copy()
                
            if not df_new.empty:
                _, _, _, lim_inf_pre, lim_sup_pre = processar_precos_regra(df_new, regra_calculo)
                if lim_inf_pre > 0 or lim_sup_pre > 0:
                    df_new.insert(0, "Válido?", (df_new['Preço'] >= lim_inf_pre) & (df_new['Preço'] <= lim_sup_pre))
                else:
                    df_new.insert(0, "Válido?", True)
            st.session_state['df_edicao'] = df_new
            st.rerun()

        if st.session_state['df_edicao'].empty:
            st.warning("Nenhum item restou após a aplicação do filtro de período.")
        else:
            st.markdown("---")
            st.markdown("### Passo 1: Validação do objeto")
            st.write("Abaixo estão os registros localizados. Os preços discrepantes estatisticamente já foram desmarcados. Revise a lista desmarcando os itens que **não correspondem** tecnicamente à sua pesquisa.")
            
            st.checkbox("Selecionar todos / nenhum", value=st.session_state['todos_marcados'], key='chk_todos_ui', on_change=toggle_todos)
            
            with st.form("form_triagem"):
                df_show = st.session_state['df_edicao'].copy()
                df_show = df_show.drop(columns=['Preço'])
                
                df_editado = st.data_editor(
                    df_show,
                    column_config={
                        "Válido?": st.column_config.CheckboxColumn("Válido?", default=True),
                        "Valor Unitário": st.column_config.TextColumn("Valor Unitário"),
                        "Link PNCP": st.column_config.LinkColumn("Link PNCP", display_text="Acessar PNCP")
                    },
                    disabled=["Data", "Órgão", "Item", "Qtd", "Valor Unitário", "Link PNCP"],
                    hide_index=True,
                    use_container_width=True
                )
                btn_validar = st.form_submit_button("Validar preço")
            
            if btn_validar:
                st.session_state['df_edicao']['Válido?'] = df_editado['Válido?']
                st.session_state['step2_ready'] = True
                st.rerun()

            if st.session_state['step2_ready']:
                df_final = st.session_state['df_edicao']
                df_selecionado = df_final[df_final['Válido?'] == True].copy()
                
                if df_selecionado.empty:
                    st.error("Todos os itens foram desmarcados. Selecione ao menos um item.")
                else:
                    st.markdown("---")
                    st.markdown("### Passo 2: Validação do preço")
                    
                    df_validos, df_outliers, mediana_geral, lim_inf, lim_sup = processar_precos_regra(df_selecionado, regra_calculo)
                    df_validos = ordenar_validos(df_validos)
                    df_outliers_sorted = ordenar_outliers(df_outliers)

                    media_saneada = df_validos['Preço'].mean() if not df_validos.empty else 0
                    mediana_saneada = df_validos['Preço'].median() if not df_validos.empty else 0
                    menor_valido = df_validos['Preço'].min() if not df_validos.empty else 0
                    maior_valido = df_validos['Preço'].max() if not df_validos.empty else 0
                    
                    menor_encontrado = df_selecionado['Preço'].min() if not df_selecionado.empty else 0
                    maior_encontrado = df_selecionado['Preço'].max() if not df_selecionado.empty else 0
                    total_registros = len(df_selecionado)
                    total_uteis = len(df_validos)

                    st.markdown("<br>", unsafe_allow_html=True)
                    l1_c1, l1_c2, l1_c3, l1_c4 = st.columns(4)
                    l1_c1.markdown(f"<div class='metric-card'><div class='metric-lbl'>Média Saneada</div><div class='metric-val'>{formatar_moeda_simples(media_saneada)}</div></div>", unsafe_allow_html=True)
                    l1_c2.markdown(f"<div class='metric-card'><div class='metric-lbl'>Mediana</div><div class='metric-val'>{formatar_moeda_simples(mediana_saneada)}</div></div>", unsafe_allow_html=True)
                    l1_c3.markdown(f"<div class='metric-card'><div class='metric-lbl'>Menor Válido</div><div class='metric-val'>{formatar_moeda_simples(menor_valido)}</div></div>", unsafe_allow_html=True)
                    l1_c4.markdown(f"<div class='metric-card'><div class='metric-lbl'>Maior Válido</div><div class='metric-val'>{formatar_moeda_simples(maior_valido)}</div></div>", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    l2_c1, l2_c2, l2_c3, l2_c4 = st.columns(4)
                    l2_c1.markdown(f"<div class='metric-card metric-card-secondary'><div class='metric-lbl'>Menor Preço Encontrado</div><div class='metric-val'>{formatar_moeda_simples(menor_encontrado)}</div></div>", unsafe_allow_html=True)
                    l2_c2.markdown(f"<div class='metric-card metric-card-secondary'><div class='metric-lbl'>Maior Preço Encontrado</div><div class='metric-val'>{formatar_moeda_simples(maior_encontrado)}</div></div>", unsafe_allow_html=True)
                    l2_c3.markdown(f"<div class='metric-card metric-card-secondary'><div class='metric-lbl'>Registros Selecionados</div><div class='metric-val'>{total_registros}</div></div>", unsafe_allow_html=True)
                    l2_c4.markdown(f"<div class='metric-card metric-card-secondary'><div class='metric-lbl'>Amostras Úteis</div><div class='metric-val'>{total_uteis}</div></div>", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("#### Tabela 1: Preços válidos")
                    df_view_validos = df_validos[['Data', 'Órgão', 'Item', 'Qtd', 'Valor Unitário', 'Link PNCP']]
                    st.dataframe(df_view_validos, column_config={"Link PNCP": st.column_config.LinkColumn("Link PNCP", display_text=None)}, use_container_width=True, hide_index=True)

                    if not df_outliers_sorted.empty:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("#### Tabela 2: Preços descartados")
                        df_view_outliers = df_outliers_sorted[['Data', 'Órgão', 'Item', 'Qtd', 'Valor Unitário', 'Link PNCP']]
                        st.dataframe(df_view_outliers, column_config={"Link PNCP": st.column_config.LinkColumn("Link PNCP", display_text=None)}, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.markdown("### Ações")
                    
                    data_emissao = datetime.now(fuso_br).strftime('%d/%m/%Y às %H:%M:%S')
                    html_individual = f"""
                    <html lang="pt-BR"><head><meta charset="UTF-8"><style>
                        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
                        body {{ font-family: 'Inter', sans-serif; color: #1E293B; padding: 20px; font-size:11px; }}
                        h1 {{ color: #0F2C4C; border-bottom: 2px solid #B08D55; padding-bottom: 10px; }}
                        .stats {{ background: #F1F5F9; padding: 15px; margin-bottom: 20px; font-size:13px; border-radius:6px; line-height: 1.6; border-left: 4px solid #B08D55;}}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }}
                        th {{ background: #0F2C4C; color: white; padding: 8px; text-align: left; }}
                        td {{ border: 1px solid #E2E8F0; padding: 6px; word-wrap: break-word; }}
                        a {{ color: #003B71; text-decoration: none; font-weight: bold; }}
                    </style></head><body>
                        <h1>Relatório de Pesquisa de Mercado (Item Individual)</h1>
                        <p style="text-align: right; color: #64748B;">Emitido em: {data_emissao}</p>
                        <div class="stats">
                            <b>Objeto:</b> {termo_atual}<br>
                            <b>Metodologia:</b> {regra_calculo}<br>
                            <b>Média Saneada (Ref.):</b> {formatar_moeda_simples(media_saneada)} | <b>Mediana:</b> {formatar_moeda_simples(mediana_geral)} <br>
                            <b>Amostras Úteis:</b> {total_uteis} itens de {total_registros} selecionados.
                        </div>
                        <h3>Tabela 1: Preços válidos</h3>
                        <table><thead><tr><th width="8%">Data</th><th width="15%">Órgão</th><th width="25%">Item</th><th width="12%">Preço</th><th width="30%">Link PNCP</th></tr></thead><tbody>
                    """
                    for _, r in df_validos.iterrows():
                        html_individual += f"<tr><td>{r['Data']}</td><td>{r['Órgão']}</td><td>{r['Item']}</td><td>{r['Valor Unitário'].strip()}</td><td><a href='{r['Link PNCP']}'>{r['Link PNCP']}</a></td></tr>"
                    html_individual += "</tbody></table>"

                    if not df_outliers_sorted.empty:
                        html_individual += "<h3 style='margin-top: 30px;'>Tabela 2: Preços descartados</h3><table><thead><tr><th width='8%'>Data</th><th width='15%'>Órgão</th><th width='25%'>Item</th><th width='12%'>Preço</th><th width='30%'>Link PNCP</th></tr></thead><tbody>"
                        for _, r in df_outliers_sorted.iterrows():
                            html_individual += f"<tr><td>{r['Data']}</td><td>{r['Órgão']}</td><td>{r['Item']}</td><td>{r['Valor Unitário'].strip()}</td><td><a href='{r['Link PNCP']}'>{r['Link PNCP']}</a></td></tr>"
                        html_individual += "</tbody></table>"

                    html_individual += "<script>window.print()</script></body></html>"

                    col_acao1, col_acao2 = st.columns([1, 1])
                    
                    with col_acao1:
                        with st.form("form_add_lote"):
                            col_lote1, col_lote2, col_lote3 = st.columns([2, 2, 2])
                            with col_lote1:
                                qtd_item = st.number_input(f"Qtd. p/ '{termo_atual}':", min_value=1, value=1)
                            with col_lote2:
                                tipo_agrupamento = st.radio("Formato da Contratação:", opcoes_agrupamento, index=idx_padrao, disabled=desabilitar_agrup)
                            with col_lote3:
                                if tipo_agrupamento == "Agrupar em Lotes":
                                    num_lote = st.number_input("Nº do Lote:", min_value=1, value=1)
                                else:
                                    st.write("") # Spacer
                            
                            add_lote = st.form_submit_button("➕ Salvar Item na Contratação")
                            
                            if add_lote:
                                if media_saneada > 0:
                                    nome_lote = f"Lote {num_lote}" if tipo_agrupamento == "Agrupar em Lotes" else "Sem Lote"
                                    
                                    if nome_lote not in st.session_state['lotes_contratacao']:
                                        st.session_state['lotes_contratacao'][nome_lote] = []
                                        
                                    item_lote = {
                                        "Objeto": termo_atual,
                                        "Quantidade": qtd_item,
                                        "Média Saneada": media_saneada,
                                        "Valor Total": media_saneada * qtd_item,
                                        "df_validos": df_validos,
                                        "df_outliers": df_outliers_sorted,
                                        "Amostras": total_uteis,
                                        "dados_brutos_salvo": st.session_state['dados_brutos'].copy(),
                                        "df_edicao_salvo": st.session_state['df_edicao'].copy(),
                                        "html_individual": html_individual
                                    }
                                    st.session_state['lotes_contratacao'][nome_lote].append(item_lote)
                                    
                                    # Limpeza (Reset)
                                    st.session_state['dados_brutos'] = pd.DataFrame()
                                    st.session_state['termo_pesquisado'] = ""
                                    st.session_state['df_edicao'] = pd.DataFrame()
                                    st.session_state['step2_ready'] = False
                                    
                                    st.success(f"Item salvo em '{nome_lote}'. Área limpa para nova pesquisa.")
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error("Não é possível salvar um item sem Média Saneada válida.")
                    
                    with col_acao2:
                        st.download_button("📄 Imprimir Relatório Individual", html_individual.encode('utf-8'), f"relatorio_{termo_atual}.html", use_container_width=True)

# --- ABA 2: RESUMO DA CONTRATAÇÃO (LOTES) ---
with tab_lote:
    if not st.session_state['lotes_contratacao']:
        st.info("Nenhum item adicionado à contratação ainda. Realize a pesquisa individual e adicione os itens ao lote.")
    else:
        valor_total_contratacao = 0.0
        
        # Ordenação inteligente (Se "Sem Lote", fica sendo único. Se numérico, ordena por número)
        chaves_lotes = list(st.session_state['lotes_contratacao'].keys())
        if "Sem Lote" in chaves_lotes:
            lotes_ordenados = [("Sem Lote", st.session_state['lotes_contratacao']["Sem Lote"])]
        else:
            lotes_ordenados = sorted(st.session_state['lotes_contratacao'].items(), key=lambda x: int(x[0].split()[1]))
        
        # CABEÇALHO COMPACTO DO VALOR TOTAL NO TOPO
        for nome_lote, itens_do_lote in lotes_ordenados:
            for item in itens_do_lote:
                valor_total_contratacao += item["Valor Total"]
                
        st.markdown(f"""
        <div class='total-global-compact'>
            <div class='total-global-title'>VALOR TOTAL ESTIMADO DA CONTRATAÇÃO</div>
            <div class='total-global-value'>{formatar_moeda_simples(valor_total_contratacao)}</div>
        </div>
        """, unsafe_allow_html=True)
        
        for nome_lote, itens_do_lote in lotes_ordenados:
            if nome_lote != "Sem Lote":
                st.markdown(f"<h4 class='lote-header'>{nome_lote}</h4>", unsafe_allow_html=True)
            
            tabela_lote = []
            subtotal_lote = 0.0
            
            for idx, item in enumerate(itens_do_lote):
                tabela_lote.append({
                    "Item": idx + 1,
                    "Descrição": item["Objeto"],
                    "Qtd": item["Quantidade"],
                    "Valor Ref. Unit.": formatar_moeda_ordenavel(item["Média Saneada"]),
                    "Valor Total Estimado": formatar_moeda_ordenavel(item["Valor Total"]),
                    "Amostras": item["Amostras"]
                })
                subtotal_lote += item["Valor Total"]
                
            df_lote = pd.DataFrame(tabela_lote)
            st.markdown("<div class='compact-table-container'>", unsafe_allow_html=True)
            st.dataframe(
                df_lote,
                column_config={
                    "Valor Ref. Unit.": st.column_config.TextColumn("Valor Ref. Unitário"),
                    "Valor Total Estimado": st.column_config.TextColumn("Subtotal Estimado")
                },
                hide_index=True,
                use_container_width=True
            )
            
            if nome_lote != "Sem Lote":
                st.markdown(f"<div class='subtotal-lote'>Subtotal do {nome_lote}: {formatar_moeda_simples(subtotal_lote)}</div></div>", unsafe_allow_html=True)
            else:
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Painel de Gerenciamento do Lote (Com Reordenação e Alinhamento)
            texto_expander = f"Gerenciar Itens ({nome_lote})" if nome_lote != "Sem Lote" else "Gerenciar Itens da Contratação"
            with st.expander(texto_expander):
                for idx, item in enumerate(itens_do_lote):
                    # Colunas alinhadas para os botões monocromáticos
                    c_nome, c_up, c_down, c_ed, c_pdf, c_rm = st.columns([5, 0.5, 0.5, 1.5, 1.5, 1.5])
                    c_nome.markdown(f"**Item {idx+1}:** {item['Objeto']} (Qtd: {item['Quantidade']})")
                    
                    # Setas de Reordenação
                    if c_up.button("▲", key=f"up_{nome_lote}_{idx}", disabled=(idx == 0), use_container_width=True):
                        itens_do_lote[idx], itens_do_lote[idx-1] = itens_do_lote[idx-1], itens_do_lote[idx]
                        st.rerun()
                    if c_down.button("▼", key=f"dw_{nome_lote}_{idx}", disabled=(idx == len(itens_do_lote)-1), use_container_width=True):
                        itens_do_lote[idx], itens_do_lote[idx+1] = itens_do_lote[idx+1], itens_do_lote[idx]
                        st.rerun()
                    
                    # Botões de Ação
                    if c_ed.button("✎ Editar", key=f"ed_{nome_lote}_{idx}", use_container_width=True):
                        st.session_state['dados_brutos'] = item['dados_brutos_salvo'].copy()
                        st.session_state['df_edicao'] = item['df_edicao_salvo'].copy()
                        st.session_state['termo_pesquisado'] = item['Objeto']
                        st.session_state['step2_ready'] = True
                        
                        st.session_state['lotes_contratacao'][nome_lote].pop(idx)
                        if not st.session_state['lotes_contratacao'][nome_lote]:
                            del st.session_state['lotes_contratacao'][nome_lote]
                        st.rerun()
                        
                    with c_pdf:
                        st.download_button("📄 PDF", item['html_individual'].encode('utf-8'), f"relatorio_{item['Objeto']}.html", key=f"dl_{nome_lote}_{idx}", use_container_width=True)
                        
                    if c_rm.button("✖ Remover", key=f"rm_{nome_lote}_{idx}", use_container_width=True):
                        st.session_state['lotes_contratacao'][nome_lote].pop(idx)
                        if not st.session_state['lotes_contratacao'][nome_lote]:
                            del st.session_state['lotes_contratacao'][nome_lote]
                        st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
        
        # --- PDF DA CONTRATAÇÃO COMPLETA ---
        data_emissao_lote = datetime.now(fuso_br).strftime('%d/%m/%Y às %H:%M:%S')
        html_lote = f"""
        <html lang="pt-BR"><head><meta charset="UTF-8"><style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
            body {{ font-family: 'Inter', sans-serif; color: #1E293B; padding: 20px; font-size:11px; }}
            h1 {{ color: #0F2C4C; border-bottom: 2px solid #B08D55; padding-bottom: 10px; }}
            h2 {{ color: #0F2C4C; border-bottom: 1px solid #E2E8F0; padding-bottom: 5px; margin-top: 30px; }}
            h3 {{ color: #64748B; margin-top: 20px; }}
            .stats {{ background: #F1F5F9; padding: 15px; margin-bottom: 20px; font-size:13px; border-radius:6px; line-height: 1.6; border-left: 4px solid #B08D55;}}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; table-layout: fixed; }}
            th {{ background: #0F2C4C; color: white; padding: 8px; text-align: left; }}
            td {{ border: 1px solid #E2E8F0; padding: 6px; word-wrap: break-word; }}
            .total-lote {{ font-size: 14px; font-weight: bold; color: #0F2C4C; text-align: right; padding: 5px; }}
            .total-global {{ font-size: 20px; font-weight: 900; color: #0F2C4C; text-align: right; padding: 15px; background: #E6F2FF; margin-top: 30px; border-radius: 4px; border-left: 5px solid #0F2C4C;}}
            a {{ color: #003B71; text-decoration: none; font-weight: bold; }}
            .page-break {{ page-break-before: always; }}
            .item-header {{ border-bottom: 2px solid #E2E8F0; padding-bottom: 5px; color: #B08D55; margin-top: 30px; }}
        </style></head><body>
            <h1>Relatório de Pesquisa de Mercado - Resumo da Contratação</h1>
            <p style="text-align: right; color: #64748B;">Emitido em: {data_emissao_lote}</p>
            <div class="stats">
                <b>Metodologia Estatística Base:</b> {regra_calculo}<br>
                <b>Total de Itens na Contratação:</b> {total_itens_carrinho}
            </div>
            <div class='total-global'>VALOR TOTAL ESTIMADO: {formatar_moeda_simples(valor_total_contratacao)}</div>
        """
        
        for nome_lote, itens_do_lote in lotes_ordenados:
            if nome_lote != "Sem Lote":
                html_lote += f"<h2>Resumo: {nome_lote}</h2>"
            else:
                html_lote += f"<h2>Resumo da Contratação</h2>"
                
            html_lote += "<table><thead><tr><th width='5%'>Item</th><th width='40%'>Descrição</th><th width='10%'>Qtd</th><th width='20%'>Valor Ref. Unit.</th><th width='25%'>Subtotal</th></tr></thead><tbody>"
            subt = 0.0
            for idx, item in enumerate(itens_do_lote):
                html_lote += f"<tr><td>{idx+1}</td><td>{item['Objeto']}</td><td>{item['Quantidade']}</td><td>{formatar_moeda_simples(item['Média Saneada'])}</td><td>{formatar_moeda_simples(item['Valor Total'])}</td></tr>"
                subt += item['Valor Total']
            
            if nome_lote != "Sem Lote":
                html_lote += f"</tbody></table><div class='total-lote'>Subtotal do {nome_lote}: {formatar_moeda_simples(subt)}</div>"
            else:
                html_lote += "</tbody></table>"
        
        html_lote += "<div class='page-break'></div><h1>Anexo I - Detalhamento Estatístico por Item</h1>"
        
        for nome_lote, itens_do_lote in lotes_ordenados:
            if nome_lote != "Sem Lote":
                html_lote += f"<h2 style='color: #B08D55;'>{nome_lote}</h2>"
            for idx, item in enumerate(itens_do_lote):
                html_lote += f"<h3 class='item-header'>Item {idx+1}: {item['Objeto']} (Qtd: {item['Quantidade']})</h3>"
                html_lote += f"<p style='font-size:12px;'><b>Média Saneada Adotada:</b> {formatar_moeda_simples(item['Média Saneada'])} | <b>Amostras Válidas:</b> {item['Amostras']}</p>"
                
                html_lote += "<h4>Tabela 1: Preços válidos</h4>"
                html_lote += "<table><thead><tr><th width='8%'>Data</th><th width='15%'>Órgão</th><th width='25%'>Item</th><th width='12%'>Preço</th><th width='30%'>Link PNCP</th></tr></thead><tbody>"
                for _, r in item['df_validos'].iterrows():
                    html_lote += f"<tr><td>{r['Data']}</td><td>{r['Órgão']}</td><td>{r['Item']}</td><td>{formatar_moeda_simples(r['Preço'])}</td><td><a href='{r['Link PNCP']}'>{r['Link PNCP']}</a></td></tr>"
                html_lote += "</tbody></table>"
                
                if not item['df_outliers'].empty:
                    html_lote += "<h4>Tabela 2: Preços descartados</h4>"
                    html_lote += "<table><thead><tr><th width='8%'>Data</th><th width='15%'>Órgão</th><th width='25%'>Item</th><th width='12%'>Preço</th><th width='30%'>Link PNCP</th></tr></thead><tbody>"
                    for _, r in item['df_outliers'].iterrows():
                        html_lote += f"<tr><td>{r['Data']}</td><td>{r['Órgão']}</td><td>{r['Item']}</td><td>{formatar_moeda_simples(r['Preço'])}</td><td><a href='{r['Link PNCP']}'>{r['Link PNCP']}</a></td></tr>"
                    html_lote += "</tbody></table>"
                html_lote += "<hr style='border: 1px dashed #ccc; margin: 30px 0;'>"

        html_lote += "<script>window.print()</script></body></html>"

        col_acao1, col_acao2 = st.columns([1, 1])
        with col_acao1:
            st.download_button("📄 Imprimir Relatório Completo", html_lote.encode('utf-8'), "relatorio_contratacao.html", type="primary", use_container_width=True)
        with col_acao2:
            if st.button("✖ Limpar Todos os Lotes", use_container_width=True):
                st.session_state['lotes_contratacao'] = {}
                st.rerun()

# --- FOOTER ---
st.markdown("""
<div class="tj-footer">
    © 2026 Poder Judiciário do Estado de Goiás<br>
    Sistema de Apoio à Instrução Processual - Dados Públicos
</div>
""", unsafe_allow_html=True)