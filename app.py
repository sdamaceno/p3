import streamlit as st
import pandas as pd
import requests
import concurrent.futures
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import base64

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Consulta de Preços - Análise de Mercado",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        # O preenchimento alinha as strings, permitindo que a ordenação alfabética funcione como numérica
        return f"R$ {s.rjust(15, ' ')}"
    except:
        return "R$ " + "0,00".rjust(15, ' ')

# --- 2. CSS & DESIGN (BOTÃO HAMBURGER E MARGENS) ---
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
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
    .metric-val { font-size: 20px; font-weight: 700; color: var(--tj-blue); }
    .metric-lbl { font-size: 11px; color: #64748B; text-transform: uppercase; margin-bottom: 4px; font-weight: 600; }

    .stButton > button { background-color: var(--tj-blue); color: white; border: none; border-radius: 6px; height: 44px; font-weight: 600; width: 100%; margin-top: 13px; }
    .stButton > button:hover { background-color: #0B223D; color: white; }

    .tj-footer {
        position: fixed; bottom: 0; left: 0; width: 100%; background-color: var(--tj-blue);
        color: white; text-align: center; padding: 20px 0; font-size: 12px; z-index: 1000; box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.1);
    }

    @media (max-width: 768px) {
        .tj-header, .hero-container { margin-left: -1rem; margin-right: -1rem; padding-left: 80px; padding-right: 1rem; }
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

# Callback para Checkbox "Selecionar Todos"
def toggle_todos():
    val = st.session_state['chk_todos_ui']
    if not st.session_state['df_edicao'].empty:
        st.session_state['df_edicao']['Válido?'] = val

with st.sidebar:
    st.markdown("### Filtros de Pesquisa")
    
    tipos_permitidos = st.multiselect(
        "Considerar Preços:",
        ["Homologado", "Estimado"],
        default=["Homologado"]
    )
    
    regra_calculo = st.selectbox(
        "Parâmetro de Cálculo",
        ["Decreto Estadual (GO) 9900/2021"]
    )
    
    st.markdown("---")
    
    meses_corte = st.slider("Período de Pesquisa", min_value=6, max_value=60, value=36, step=6, format="%d meses")
    paginas = st.number_input("Volume de Busca (Páginas)", min_value=1, max_value=50, value=3)

# --- 4. ENGINE DE PESQUISA (TRAVADO) ---
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
        for p in range(1, paginas + 1):
            params = {"q": termo, "tipos_documento": "edital", "ordenacao": "-dataPublicacaoPncp", "pagina": str(p), "tam_pagina": "50"}
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
        if val_homologado and float(val_homologado) > 0:
            return float(val_homologado)
            
        num_item = item.get("numeroItem")
        url_resultado = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{num_item}/resultados"
        try:
            res_resultado = self.session.get(url_resultado, timeout=3)
            if res_resultado.status_code == 200:
                dados_resultado = res_resultado.json()
                for r in dados_resultado:
                    val = r.get("valorUnitarioHomologado")
                    if val and float(val) > 0:
                        return float(val)
        except: pass
            
        situacao = str(item.get("situacaoCompraItem", ""))
        if situacao in ['4', '6']:
            val_fallback = item.get("valorUnitario")
            if val_fallback and float(val_fallback) > 0:
                return float(val_fallback)
                
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
                for item in resp.json():
                    desc = str(item.get("descricao", "")).lower()
                    
                    # LOGICA: Busca Multi-Termos (Separados por Espaço)
                    termos = termo_busca.lower().split()
                    if all(t in desc for t in termos):
                        preco_final = 0.0
                        tipo_valor = ""
                        
                        val_h = self._obter_valor_homologado_robusto(cnpj, ano, seq, item)
                        if val_h > 0:
                            preco_final = val_h
                            tipo_valor = "Homologado"
                        else:
                            val_e = item.get("valorUnitarioEstimado")
                            if val_e and float(val_e) > 0:
                                preco_final = float(val_e)
                                tipo_valor = "Estimado"
                        
                        if preco_final > 0:
                            itens.append({
                                "Data": datetime.strptime(data_pub, "%Y-%m-%d").strftime("%d/%m/%Y"),
                                "Órgão": razao.upper(),
                                "Item": item.get("descricao"),
                                "Qtd": item.get("quantidade"),
                                "Preço": preco_final,
                                "Valor Unitário": formatar_moeda_ordenavel(preco_final), 
                                "Tipo": tipo_valor,
                                "Link PNCP": link_audit 
                            })
            return itens
        except: return []

# --- 5. ESTATÍSTICA ---
def processar_precos_regra(df, regra):
    if df.empty: return df, pd.DataFrame(), 0, 0, 0
    
    if regra == "Decreto Estadual (GO) 9900/2021":
        mediana_geral = df['Preço'].median()
        limite_inferior = mediana_geral * 0.75
        limite_superior = mediana_geral * 1.25
        
        df_validos = df[(df['Preço'] >= limite_inferior) & (df['Preço'] <= limite_superior)].copy()
        df_outliers = df[(df['Preço'] < limite_inferior) | (df['Preço'] > limite_superior)].copy()
        
        return df_validos, df_outliers, mediana_geral, limite_inferior, limite_superior

def ordenar_validos(df):
    if df.empty: return df
    df['Tipo'] = pd.Categorical(df['Tipo'], categories=['Homologado', 'Estimado'], ordered=True)
    return df.sort_values(by=['Tipo', 'Preço'])

def ordenar_outliers(df):
    if df.empty: return df
    idx_max = df['Preço'].idxmax()
    idx_min = df['Preço'].idxmin()
    row_max = df.loc[[idx_max]]
    if idx_max == idx_min: return row_max
    row_min = df.loc[[idx_min]]
    restante = df.drop([idx_max, idx_min], errors='ignore')
    return pd.concat([row_max, row_min, restante])

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
    <div class="hero-subtitle">Mineração com validação em cascata e curadoria técnica</div>
</div>
""", unsafe_allow_html=True)

# FORMULÁRIO CENTRAL
with st.form(key='search_form'):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        termo = st.text_input("Qual item você deseja pesquisar?", placeholder="Ex: Monitor 24 polegadas, Papel Sulfite A4...", label_visibility="collapsed")
    with col_btn:
        btn_buscar = st.form_submit_button("Pesquisar")

# --- EXECUÇÃO DA BUSCA ---
if btn_buscar and termo:
    if not tipos_permitidos:
        st.error("Selecione pelo menos um Tipo de Preço na barra lateral.")
        st.stop()
        
    engine = PNCPEngine()
    
    with st.status("Localizando editais na base nacional...", expanded=True) as status:
        editais = engine.buscar_editais(termo, paginas)
        
        if not editais:
            status.update(label="Nenhum edital encontrado.", state="error")
            st.session_state['dados_brutos'] = pd.DataFrame() 
        else:
            st.write("Editais encontrados. Executando extração de preços...")
            
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
                status.update(label="Itens não encontrados ou fora do status exigido.", state="error")
                st.session_state['dados_brutos'] = pd.DataFrame()
            else:
                status.update(label="Mineração concluída!", state="complete")
                
                df_raw = pd.DataFrame(all_items)
                st.session_state['dados_brutos'] = df_raw
                st.session_state['termo_pesquisado'] = termo
                
                # FORÇA RESET DOS HASHES PARA NOVO PROCESSAMENTO
                st.session_state['filter_hash'] = ""
                st.session_state['step2_ready'] = False
                

# --- PROCESSAMENTO E TRIAGEM (PASSO 1 E 2) ---
if not st.session_state['dados_brutos'].empty:
    
    df_raw = st.session_state['dados_brutos'].copy()
    termo_atual = st.session_state['termo_pesquisado']
    
    # Aplica os Filtros Laterais Atuais
    try:
        df_raw['dt'] = pd.to_datetime(df_raw['Data'], format="%d/%m/%Y", errors='coerce')
        limite_data = datetime.now() - relativedelta(months=meses_corte)
        df_raw = df_raw[(df_raw['dt'] >= limite_data) & (df_raw['Tipo'].isin(tipos_permitidos))].copy()
        df_raw = df_raw.drop(columns=['dt'])
    except:
        df_raw = df_raw[df_raw['Tipo'].isin(tipos_permitidos)].copy()

    if df_raw.empty:
        st.warning("Nenhum item restou após a aplicação dos filtros de data/tipo.")
    else:
        # Verifica se os filtros mudaram para resetar o Editor e calcular os Outliers Iniciais
        current_hash = f"{len(df_raw)}_{meses_corte}_{''.join(tipos_permitidos)}_{regra_calculo}"
        
        if st.session_state['filter_hash'] != current_hash:
            st.session_state['filter_hash'] = current_hash
            st.session_state['step2_ready'] = False
            
            # Saneamento Prévio (para desmarcar os outliers automaticamente)
            df_edicao = df_raw.copy()
            _, _, _, lim_inf_pre, lim_sup_pre = processar_precos_regra(df_edicao, regra_calculo)
            
            if lim_inf_pre > 0 or lim_sup_pre > 0:
                df_edicao.insert(0, "Válido?", (df_edicao['Preço'] >= lim_inf_pre) & (df_edicao['Preço'] <= lim_sup_pre))
            else:
                df_edicao.insert(0, "Válido?", True)
                
            st.session_state['df_edicao'] = df_edicao
        
        # --- PASSO 1: TRIAGEM ---
        st.markdown("---")
        st.markdown("### Passo 1: Validação do objeto")
        st.write("Abaixo estão os registros localizados. Os preços considerados outliers estatísticos já foram desmarcados por padrão. Revise e selecione os itens correspondentes antes de calcular as estatísticas.")
        
        # Checkbox fora do form aciona a alteração global imediata
        st.checkbox("Selecionar todos / nenhum", value=True, key='chk_todos_ui', on_change=toggle_todos)
        
        # Formulário impede que o data_editor dê refresh constante ao clicar nas linhas
        with st.form("form_triagem"):
            df_show = st.session_state['df_edicao'].drop(columns=['Preço']) # Esconde o float numérico
            
            df_editado = st.data_editor(
                df_show,
                column_config={
                    "Válido?": st.column_config.CheckboxColumn("Válido?", default=True),
                    "Valor Unitário": st.column_config.TextColumn("Valor Unitário"),
                    "Link PNCP": st.column_config.LinkColumn("Link PNCP", display_text="Acessar PNCP")
                },
                disabled=["Data", "Órgão", "Item", "Tipo", "Qtd", "Valor Unitário", "Link PNCP"],
                hide_index=True,
                use_container_width=True
            )
            btn_validar = st.form_submit_button("Validar preço")
        
        if btn_validar:
            # Ao clicar, salva o estado atual do editor na memória e avança pro Passo 2
            st.session_state['df_edicao']['Válido?'] = df_editado['Válido?']
            st.session_state['step2_ready'] = True
            st.rerun()

        # --- PASSO 2: CÁLCULOS FINAIS ---
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

                # --- CÁLCULOS DO DASHBOARD ---
                media_saneada = df_validos['Preço'].mean() if not df_validos.empty else 0
                mediana_saneada = df_validos['Preço'].median() if not df_validos.empty else 0
                menor_valido = df_validos['Preço'].min() if not df_validos.empty else 0
                maior_valido = df_validos['Preço'].max() if not df_validos.empty else 0
                
                menor_encontrado = df_selecionado['Preço'].min() if not df_selecionado.empty else 0
                maior_encontrado = df_selecionado['Preço'].max() if not df_selecionado.empty else 0
                total_registros = len(df_selecionado)
                total_uteis = len(df_validos)

                # --- RENDERIZAÇÃO DOS CARDS ---
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
                l2_c3.markdown(f"<div class='metric-card metric-card-secondary'><div class='metric-lbl'>Total de Registros Encontrados</div><div class='metric-val'>{total_registros}</div></div>", unsafe_allow_html=True)
                l2_c4.markdown(f"<div class='metric-card metric-card-secondary'><div class='metric-lbl'>Total de Registros Úteis</div><div class='metric-val'>{total_uteis}</div></div>", unsafe_allow_html=True)

                # --- TABELAS FINAIS ---
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### Tabela 1: Preços válidos")
                
                df_view_validos = df_validos[['Data', 'Órgão', 'Item', 'Tipo', 'Qtd', 'Valor Unitário', 'Link PNCP']]
                st.dataframe(
                    df_view_validos,
                    column_config={"Link PNCP": st.column_config.LinkColumn("Link PNCP", display_text=None)},
                    use_container_width=True, hide_index=True
                )

                if not df_outliers_sorted.empty:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("#### Tabela 2: Preços descartados")
                    
                    df_view_outliers = df_outliers_sorted[['Data', 'Órgão', 'Item', 'Tipo', 'Qtd', 'Valor Unitário', 'Link PNCP']]
                    st.dataframe(
                        df_view_outliers,
                        column_config={"Link PNCP": st.column_config.LinkColumn("Link PNCP", display_text=None)},
                        use_container_width=True, hide_index=True
                    )

                # --- RELATÓRIO PDF ---
                def gerar_pdf(df_v, df_o, termo):
                    html = f"""
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
                        <h1>Relatório de Pesquisa de Mercado</h1>
                        <div class="stats">
                            <b>Objeto:</b> {termo}<br>
                            <b>Metodologia:</b> {regra_calculo}<br>
                            <b>Média Saneada:</b> {formatar_moeda_simples(media_saneada)} | <b>Mediana:</b> {formatar_moeda_simples(mediana_geral)} <br>
                            <b>Menor Válido:</b> {formatar_moeda_simples(menor_valido)} | <b>Maior Válido:</b> {formatar_moeda_simples(maior_valido)} <br>
                            <b>Amostras Úteis:</b> {total_uteis} itens de {total_registros} selecionados na curadoria.
                        </div>
                        
                        <h3>Tabela 1: Preços válidos</h3>
                        <table><thead><tr><th width="8%">Data</th><th width="15%">Órgão</th><th width="25%">Item</th><th width="10%">Tipo</th><th width="12%">Preço</th><th width="30%">Link PNCP</th></tr></thead><tbody>
                    """
                    for _, r in df_v.iterrows():
                        html += f"<tr><td>{r['Data']}</td><td>{r['Órgão']}</td><td>{r['Item']}</td><td>{r['Tipo']}</td><td>{r['Valor Unitário'].strip()}</td><td><a href='{r['Link PNCP']}'>{r['Link PNCP']}</a></td></tr>"
                    html += "</tbody></table>"

                    if not df_o.empty:
                        html += "<h3 style='margin-top: 30px;'>Tabela 2: Preços descartados</h3><table><thead><tr><th width='8%'>Data</th><th width='15%'>Órgão</th><th width='25%'>Item</th><th width='10%'>Tipo</th><th width='12%'>Preço</th><th width='30%'>Link PNCP</th></tr></thead><tbody>"
                        for _, r in df_o.iterrows():
                            html += f"<tr><td>{r['Data']}</td><td>{r['Órgão']}</td><td>{r['Item']}</td><td>{r['Tipo']}</td><td>{r['Valor Unitário'].strip()}</td><td><a href='{r['Link PNCP']}'>{r['Link PNCP']}</a></td></tr>"
                        html += "</tbody></table>"

                    html += "<script>window.print()</script></body></html>"
                    return html.encode('utf-8')

                st.markdown("---")
                c_dw, _ = st.columns([1, 4])
                c_dw.download_button("Imprimir Relatório Oficial", gerar_pdf(df_validos, df_outliers_sorted, termo_atual), "relatorio_pesquisa.html")

# --- FOOTER ---
st.markdown("""
<div class="tj-footer">
    © 2026 Poder Judiciário do Estado de Goiás<br>
    Sistema de Apoio à Instrução Processual - Dados Públicos
</div>
""", unsafe_allow_html=True)
