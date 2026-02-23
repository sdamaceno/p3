import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import concurrent.futures
import time
import hashlib
import re
import io
import json
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

# Biblioteca de PDF (Requer: xhtml2pdf no requirements.txt)
try:
    from xhtml2pdf import pisa
except ImportError:
    st.error("Biblioteca 'xhtml2pdf' não encontrada. Verifique o arquivo requirements.txt no GitHub.")

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Planejamento de Compras - Análise de Mercado",
    layout="wide",
    initial_sidebar_state="expanded"
)

fuso_br = timezone(timedelta(hours=-3))

# --- FUNÇÕES DE LINGUAGEM E EXTRAÇÃO DE PALAVRAS-CHAVE ---
def extrair_palavras_chave(texto, limite=10):
    if not texto: return ""
    stopwords = {"de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu", "sua", "ou", "ser", "quando", "muito", "há", "nos", "já", "está", "eu", "também", "só", "pelo", "pela", "até", "isso", "ela", "entre", "era", "depois", "sem", "mesmo", "aos", "ter", "seus", "quem", "nas", "me", "esse", "eles", "estão", "você", "tinha", "foram", "essa", "num", "nem", "suas", "meu", "às", "minha", "têm", "numa", "pelos", "elas", "havia", "seja", "qual", "será", "nós", "tenho", "lhe", "deles", "essas", "esses", "pelas", "este", "fosse", "dele", "tu", "te", "vocês", "vos", "lhes", "meus", "minhas", "teu", "tua", "teus", "tuas", "nosso", "nossa", "nossos", "nossas", "dela", "delas", "esta", "estes", "estas", "aquele", "aquela", "aqueles", "aquelas", "isto", "aquilo", "estou", "estamos", "estão", "estive", "esteve", "estivemos", "estiveram", "estava", "estávamos", "estavam", "estivera", "estivéramos", "esteja", "sejamos", "sejam", "estivesse", "estivéssemos", "estivessem", "estiver", "estivermos", "estiverem", "hei", "há", "havemos", "hão", "houve", "houvemos", "houveram", "houvera", "houvéramos", "haja", "hajamos", "hajam", "houvesse", "houvéssemos", "houvessem", "houver", "houvermos", "houverem", "houverei", "houverá", "houveremos", "houverão", "houveria", "houveríamos", "houveriam", "sou", "somos", "são", "era", "éramos", "eram", "fui", "foi", "fomos", "foram", "fora", "fôramos", "seja", "sejamos", "sejam", "fosse", "fôssemos", "fossem", "for", "formos", "forem", "serei", "será", "seremos", "serão", "seria", "seríamos", "seriam", "tenho", "tem", "temos", "tém", "tinha", "tínhamos", "tinham", "tive", "teve", "tivemos", "tiveram", "tivera", "tivéramos", "tenha", "tenhamos", "tenham", "tivesse", "tivéssemos", "tivessem", "tiver", "tivermos", "tiverem", "terei", "terá", "teremos", "terão", "teria", "teríamos", "teriam"}
    palavras = re.findall(r'\b[a-zÀ-ÿ]{3,}\b', texto.lower())
    filtradas = [p for p in palavras if p not in stopwords]
    contagem = Counter(filtradas)
    top_words = [word for word, count in contagem.most_common(limite)]
    return " ".join(top_words)

# --- FUNÇÕES DE FORMATAÇÃO E UTILIDADES ---
def formatar_moeda_simples(valor):
    try:
        formatted = f"{float(valor):,.2f}"
        return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def formatar_moeda_ordenavel(valor):
    try:
        val_f = float(valor)
        s = f"{val_f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s.rjust(15, ' ')}"
    except: return "R$ " + "0,00".rjust(15, ' ')

def formata_origem_pdf(origem):
    origem_str = str(origem)
    if origem_str.startswith("http"):
        return f"<a href='{origem_str}' style='color: blue; text-decoration: underline;'>Acessar Fonte</a>"
    return origem_str

def gerar_hash_item(row):
    lote = "Único" if pd.isna(row.get('Lote')) or str(row.get('Lote')).strip() == "" else str(row.get('Lote')).strip()
    item = str(row.get('Item', '')).strip()
    return hashlib.md5(f"{lote}_{item}".encode()).hexdigest()[:10]

# Validações BR
def validar_formatar_cpf_cnpj(doc):
    if not doc: return ""
    doc_cl = re.sub(r'\D', '', str(doc))
    if len(doc_cl) == 11: return f"{doc_cl[:3]}.{doc_cl[3:6]}.{doc_cl[6:9]}-{doc_cl[9:]}"
    elif len(doc_cl) == 14: return f"{doc_cl[:2]}.{doc_cl[2:5]}.{doc_cl[5:8]}/{doc_cl[8:12]}-{doc_cl[12:]}"
    return None

def validar_formatar_telefone(tel):
    if not tel: return ""
    t_cl = re.sub(r'\D', '', str(tel))
    if len(t_cl) == 11: return f"({t_cl[:2]}) {t_cl[2:7]}-{t_cl[7:]}"
    elif len(t_cl) == 10: return f"({t_cl[:2]}) {t_cl[2:6]}-{t_cl[6:]}"
    return None

def validar_email(email):
    if not email: return True
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", str(email)) is not None

def validar_link(link):
    if not link: return True
    return re.match(r"^https?://", str(link)) is not None

# --- 2. CSS & DESIGN COMPACTO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Inter:wght@400;500&display=swap');
    :root { --tj-blue: #0F2C4C; --tj-gold: #B08D55; --text-main: #1E293B; }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--text-main); background-color: #F8FAFC; }
    h1, h2, h3, h4, h5 { font-family: 'Plus Jakarta Sans', sans-serif; }
    footer {visibility: hidden;}
    .block-container { padding-top: 1.5rem !important; padding-bottom: 100px !important; }
    header[data-testid="stHeader"] { background-color: transparent !important; box-shadow: none !important; }
    header[data-testid="stHeader"] > div:not(:first-child) { display: none !important; }
    [data-testid="stSidebar"] { background-color: #F8FAFC; border-right: 1px solid #E2E8F0; }
    .stApp { margin-top: 0px; }
    .tj-header { background: #FFFFFF; padding: 20px 5rem 20px 85px; margin-top: -1.5rem; margin-left: -5rem; margin-right: -5rem; border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .tj-logo-text { font-family: 'Plus Jakarta Sans'; font-weight: 700; font-size: 18px; color: var(--tj-blue); line-height: 1.2; }
    .tj-sub { font-weight: 400; font-size: 13px; color: #64748B; border-left: 1px solid #CBD5E1; padding-left: 10px; margin-left: 10px; }
    .hero-container { background: linear-gradient(180deg, #E6F2FF 0%, #FFFFFF 100%); padding: 40px 5rem; margin-left: -5rem; margin-right: -5rem; text-align: center; border-bottom: 1px solid #F1F5F9; margin-bottom: 30px; }
    .hero-title { color: var(--tj-blue); font-size: 32px; font-weight: 800; margin-bottom: 5px; }
    .metric-card { background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 15px; text-align: center; border-top: 4px solid var(--tj-gold); display: flex; flex-direction: column; justify-content: center; }
    .metric-card-secondary { border-top: 4px solid #64748B; background-color: #F8FAFC; }
    .metric-val { font-size: 20px; font-weight: 700; color: var(--tj-blue); }
    .metric-lbl { font-size: 11px; color: #64748B; text-transform: uppercase; margin-bottom: 4px; font-weight: 600; }
    .stButton > button { background-color: var(--tj-blue); color: white; border: none; border-radius: 6px; font-weight: 600; width: 100%; }
    .stButton > button:hover { background-color: #0B223D; color: white; }
    .tj-footer { position: fixed; bottom: 0; left: 0; width: 100%; background-color: var(--tj-blue); color: white; text-align: center; padding: 20px 0; font-size: 12px; z-index: 1000; box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.1); }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 600; }
    .total-global-compact { background-color: #E6F2FF; padding: 15px 25px; border-radius: 6px; border-left: 5px solid #0F2C4C; display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; margin-top: 10px; }
    .total-global-title { margin: 0; color: #0F2C4C; font-size: 16px; font-weight: 700; text-transform: uppercase; }
    .total-global-value { margin: 0; color: #0F2C4C; font-size: 26px; font-weight: 800; }
    .item-row { border-bottom: 1px solid #E2E8F0; padding: 10px 0; display: flex; align-items: center;}
</style>
""", unsafe_allow_html=True)

# --- 3. MEMÓRIA DE SESSÃO E ESTRUTURAS ---
cols_pncp = ["Válido?", "Data", "Empresa/Órgão", "Item", "Qtd", "Preço", "Valor Unitário", "Origem", "Tipo"]
cols_rastreio = ["Data do Contato", "Horário", "Empresa", "CNPJ/CPF", "Tipo de fonte", "Descrição da fonte", "Link da fonte", "Nome do Contato", "E-mail", "Telefone", "Situação", "Preço", "Valor Unitário"]
cols_historico_busca = ["Data/Hora", "Termo Pesquisado", "Novos Registros"]

if 'tr_objeto_salvo' not in st.session_state: st.session_state['tr_objeto_salvo'] = False
if 'tr_itens_salvos' not in st.session_state: st.session_state['tr_itens_salvos'] = False
if 'objeto_contratacao' not in st.session_state: st.session_state['objeto_contratacao'] = ""
if 'keywords_extraidas' not in st.session_state: st.session_state['keywords_extraidas'] = ""
if 'df_tr' not in st.session_state: st.session_state['df_tr'] = pd.DataFrame(columns=["Lote", "Item", "Descrição", "Métrica", "Tipo", "Quantidade"])
if 'banco_precos' not in st.session_state: st.session_state['banco_precos'] = {}
if 'acao_ativa' not in st.session_state: st.session_state['acao_ativa'] = (None, None)

if 'df_processos' not in st.session_state:
    st.session_state['df_processos'] = pd.DataFrame([
        {"Fase": "Planejamento (Fase Interna)", "Etapa": "Identificação da Contratação", "Ator": "Requisitante", "Entrada": "DOD / Solicitação", "Saída": "Objeto Definido", "Automação": "Manual"},
        {"Fase": "Planejamento (Fase Interna)", "Etapa": "Estruturação de Lotes", "Ator": "Equipe Técnica", "Entrada": "Planilha Excel", "Saída": "Itens Validados", "Automação": "Importação/Manual"},
        {"Fase": "Pesquisa de Mercado", "Etapa": "Extração Base PNCP", "Ator": "Sistema (Robô)", "Entrada": "Termo de Busca", "Saída": "Preços Homologados", "Automação": "Automático (API)"},
        {"Fase": "Pesquisa de Mercado", "Etapa": "Cotação Direta (Fornecedores)", "Ator": "Comprador", "Entrada": "E-mail / Telefone", "Saída": "Propostas Salvas", "Automação": "Manual / Rastreável"},
        {"Fase": "Saneamento", "Etapa": "Validação Estatística", "Ator": "Sistema", "Entrada": "Preços Brutos", "Saída": "Outliers Removidos", "Automação": "Automático (Mediana ±25%)"},
        {"Fase": "Relatório", "Etapa": "Geração do Termo Final", "Ator": "Sistema", "Entrada": "Dados Tratados", "Saída": "Relatório Oficial (PDF)", "Automação": "Automático (XHTML2PDF)"}
    ])

opcoes_origem_decreto = ["VI - Pesquisa direta c/ fornecedores", "I - Base estadual NFe", "II - Portal de Compras GO", "III - PNCP / Ferramentas específicas", "IV - Mídia / Tabelas / Sítios eletrônicos", "V - Contratações similares da adm. pública"]
opcoes_situacao = ["Solicitação de proposta enviada", "Confirmação de recebimento da solicitação", "Proposta recebida", "Não enviou proposta comercial", "Proposta recebida com equívoco", "Proposta retificada recebida"]

# Sidebar
with st.sidebar:
    st.markdown("### Parâmetros Estatísticos")
    st.text_input("Considerar PNCP:", value="Apenas Homologados", disabled=True)
    regra_calculo = st.selectbox("Parâmetro de Cálculo", ["Preços válidos - Mediana ±25% e Média"])
    meses_corte = st.slider("Período de PNCP/Atas", min_value=12, max_value=60, value=24, step=6, format="%d meses")
    paginas_pncp = st.number_input("Volume Busca PNCP (Páginas)", min_value=1, max_value=5, value=3)
    
    st.markdown("---")
    st.markdown("### 🔑 Assistente de Palavras-Chave")
    qtd_kw = st.slider("Qtd. Máx. de Termos Extraídos", min_value=5, max_value=20, value=10)
    
    if st.session_state['tr_objeto_salvo']:
        st.caption("Termos extraídos do seu Objeto (Sugestão):")
        kw_editadas = st.text_area("Termos:", value=st.session_state['keywords_extraidas'], height=80, key="kw_box")
        st.session_state['keywords_extraidas'] = kw_editadas
    else:
        st.info("Salve o Objeto na Aba 1 para gerar as palavras-chave.")

# --- 4. ENGINE PNCP "CASCATA INTELIGENTE" ---
class PNCPEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", "Accept": "application/json"})

    def buscar_editais_inteligente(self, termo, paginas=3, status_placeholder=None):
        base_url = "https://pncp.gov.br/api/search/"
        busca_api = termo.replace('"', '').replace("'", "")
        
        # 1. Tentativa Exata (Rigorosa)
        if status_placeholder: status_placeholder.update(label="🔎 Tentativa 1: Buscando frase exata nos editais...", state="running")
        editais = self._executar_busca(base_url, busca_api, "edital", paginas)
        if editais: return editais, "Exata"

        # 2. Tentativa Flexível (Termos soltos)
        stop_words = {"de", "da", "do", "para", "com", "sem", "e", "o", "a", "em", "um", "uma"}
        termos_limpos = [w for w in busca_api.split() if w.lower() not in stop_words]
        busca_flexivel = " ".join(termos_limpos)
        
        if busca_flexivel != busca_api:
            if status_placeholder: status_placeholder.update(label="🔄 Tentativa 2: Refinando termos para busca ampla...", state="running")
            editais = self._executar_busca(base_url, busca_flexivel, "edital", paginas)
            if editais: return editais, "Flexível"

        # 3. Tentativa Ampliada (Sem filtro de documento)
        if status_placeholder: status_placeholder.update(label="⚠️ Tentativa 3: Expandindo para todos os tipos de documentos...", state="running")
        editais = self._executar_busca(base_url, busca_flexivel, "", paginas)
        if editais: return editais, "Ampliada"

        return [], "Falha"

    def _executar_busca(self, url, termo, tipo_doc, paginas):
        editais_encontrados = []
        for p in range(1, paginas + 1):
            params = {"q": termo, "ordenacao": "-dataPublicacaoPncp", "pagina": str(p), "tam_pagina": "50"}
            if tipo_doc: params["tipos_documento"] = tipo_doc
            try:
                resp = self.session.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    items = resp.json().get('items', [])
                    if not items: break
                    editais_encontrados.extend(items)
                else: break
            except: break
        return editais_encontrados

    def _obter_valor_homologado_robusto(self, cnpj, ano, seq, item):
        val_homologado = item.get("valorUnitarioHomologado")
        if val_homologado and float(val_homologado) > 0: return float(val_homologado)
        
        num_item = item.get("numeroItem")
        url_resultado = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{num_item}/resultados"
        try:
            res_resultado = self.session.get(url_resultado, timeout=4)
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
                stop_words = {"de", "da", "do", "para", "com", "sem", "e", "o", "a", "em", "um", "uma", "aquisicao", "contratacao"}
                termos_chave = [t for t in termo_busca.lower().split() if t not in stop_words]
                
                for item in resp.json():
                    desc = str(item.get("descricao", "")).lower()
                    if all(t in desc for t in termos_chave):
                        val_h = self._obter_valor_homologado_robusto(cnpj, ano, seq, item)
                        if val_h > 0:
                            itens.append({
                                "Data": datetime.strptime(data_pub, "%Y-%m-%d").strftime("%d/%m/%Y"),
                                "Empresa/Órgão": razao.upper(), 
                                "Item": item.get("descricao"),
                                "Qtd": item.get("quantidade"),
                                "Preço": float(val_h), 
                                "Valor Unitário": formatar_moeda_ordenavel(val_h), 
                                "Origem": link_audit,
                                "Tipo": "PNCP"
                            })
            return itens
        except: return []

# --- 5. ESTATÍSTICA ---
def processar_precos_regra(df, regra):
    if df.empty: return df, pd.DataFrame(), 0, 0, 0
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

# --- 6. MECANISMO DE PROJETO (BACKUP/RESTORE) ---
def empacotar_projeto():
    config_df = pd.DataFrame([{"Key": "objeto_contratacao", "Value": st.session_state.get('objeto_contratacao', '')}])
    df_tr_export = st.session_state.get('df_tr', pd.DataFrame(columns=["Lote", "Item", "Descrição", "Métrica", "Tipo", "Quantidade"])).copy()
    if not df_tr_export.empty: df_tr_export['Hash'] = df_tr_export.apply(gerar_hash_item, axis=1)

    pncp_list, man_list, est_list, hist_list = [], [], [], []
    for h, banco in st.session_state.get('banco_precos', {}).items():
        if not banco['df_pncp'].empty:
            df_p = banco['df_pncp'].copy()
            df_p['Hash'] = h
            pncp_list.append(df_p)
        if not banco['df_manual_rastreio'].empty:
            df_m = banco['df_manual_rastreio'].copy()
            df_m['Hash'] = h
            man_list.append(df_m)
        if not banco['historico_buscas'].empty:
            df_h = banco['historico_buscas'].copy()
            df_h['Hash'] = h
            hist_list.append(df_h)
            
        est_list.append({"Hash": h, "estatistica_pronta": banco['estatistica_pronta'], "media_saneada": banco['media_saneada'], "mediana": banco['mediana'], "amostras": banco['amostras']})

    df_pncp_export = pd.concat(pncp_list, ignore_index=True) if pncp_list else pd.DataFrame(columns=cols_pncp + ['Hash'])
    df_man_export = pd.concat(man_list, ignore_index=True) if man_list else pd.DataFrame(columns=cols_rastreio + ['Hash'])
    df_hist_export = pd.concat(hist_list, ignore_index=True) if hist_list else pd.DataFrame(columns=cols_historico_busca + ['Hash'])
    df_est_export = pd.DataFrame(est_list) if est_list else pd.DataFrame(columns=["Hash", "estatistica_pronta", "media_saneada", "mediana", "amostras"])

    return {"Config": config_df, "TR": df_tr_export, "PNCP": df_pncp_export, "Manual": df_man_export, "Stats": df_est_export, "Historico": df_hist_export}

def gerar_arquivo_exportacao(formato):
    dfs = empacotar_projeto()
    buffer = io.BytesIO()
    if formato == "JSON (Recomendado)":
        out_dict = {k: v.fillna("").to_dict(orient='records') for k, v in dfs.items()}
        buffer.write(json.dumps(out_dict, indent=4).encode('utf-8'))
        return buffer.getvalue(), "projeto_tr.json", "application/json"
    elif formato == "XLSX (Excel)":
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            for k, v in dfs.items(): v.to_excel(writer, sheet_name=k, index=False)
        return buffer.getvalue(), "projeto_tr.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif formato == "ODS (LibreOffice)":
        with pd.ExcelWriter(buffer, engine='odf') as writer:
            for k, v in dfs.items(): v.to_excel(writer, sheet_name=k, index=False)
        return buffer.getvalue(), "projeto_tr.ods", "application/vnd.oasis.opendocument.spreadsheet"
    elif formato == "CSV (ZIP)":
        with zipfile.ZipFile(buffer, 'w') as zf:
            for k, v in dfs.items():
                csv_str = v.to_csv(index=False, sep=';', encoding='utf-8-sig')
                zf.writestr(f"{k}.csv", csv_str)
        return buffer.getvalue(), "projeto_csv.zip", "application/zip"

def carregar_projeto(file):
    dfs = {}
    try:
        if file.name.endswith(".json"):
            data = json.load(file)
            for k, v in data.items(): dfs[k] = pd.DataFrame(v)
        elif file.name.endswith(".xlsx"): dfs = pd.read_excel(file, sheet_name=None, engine='openpyxl')
        elif file.name.endswith(".ods"): dfs = pd.read_excel(file, sheet_name=None, engine='odf')
        elif file.name.endswith(".zip"):
            with zipfile.ZipFile(file, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.csv'): dfs[name.replace('.csv', '')] = pd.read_csv(zf.open(name), sep=';')
        
        if 'Config' in dfs and not dfs['Config'].empty:
            st.session_state['objeto_contratacao'] = str(dfs['Config'].loc[0, 'Value'])
            st.session_state['tr_objeto_salvo'] = True
            st.session_state['keywords_extraidas'] = extrair_palavras_chave(str(dfs['Config'].loc[0, 'Value']), 10)

        if 'TR' in dfs and not dfs['TR'].empty:
            tr_df = dfs['TR']
            for c in ["Lote", "Item", "Descrição", "Métrica", "Tipo", "Quantidade"]:
                if c not in tr_df.columns: tr_df[c] = ""
            tr_df['Quantidade_Calc'] = pd.to_numeric(tr_df['Quantidade'], errors='coerce').fillna(1)
            st.session_state['df_tr'] = tr_df.drop(columns=['Hash'], errors='ignore')
            st.session_state['tr_itens_salvos'] = True

            pncp_df = dfs.get('PNCP', pd.DataFrame())
            man_df = dfs.get('Manual', pd.DataFrame())
            stats_df = dfs.get('Stats', pd.DataFrame())
            hist_df = dfs.get('Historico', pd.DataFrame())

            for d in [pncp_df, man_df]:
                if 'Válido?' in d.columns: d['Válido?'] = d['Válido?'].astype(str).str.lower().map({'true': True, '1': True, '1.0': True}).fillna(False)
            if 'estatistica_pronta' in stats_df.columns:
                stats_df['estatistica_pronta'] = stats_df['estatistica_pronta'].astype(str).str.lower().map({'true': True, '1': True}).fillna(False)

            new_banco = {}
            for _, row in tr_df.iterrows():
                old_hash = row.get('Hash', gerar_hash_item(row))
                new_hash = gerar_hash_item(row)

                df_p = pncp_df[pncp_df['Hash'] == old_hash].drop(columns=['Hash']) if ('Hash' in pncp_df.columns and not pncp_df.empty) else pd.DataFrame(columns=cols_pncp)
                df_m = man_df[man_df['Hash'] == old_hash].drop(columns=['Hash']) if ('Hash' in man_df.columns and not man_df.empty) else pd.DataFrame(columns=cols_rastreio)
                df_h = hist_df[hist_df['Hash'] == old_hash].drop(columns=['Hash']) if ('Hash' in hist_df.columns and not hist_df.empty) else pd.DataFrame(columns=cols_historico_busca)
                
                df_p = df_p.reindex(columns=cols_pncp).dropna(how='all')
                df_m = df_m.reindex(columns=cols_rastreio).dropna(how='all')
                df_h = df_h.reindex(columns=cols_historico_busca).dropna(how='all')

                stat_row = stats_df[stats_df['Hash'] == old_hash] if ('Hash' in stats_df.columns and not stats_df.empty) else pd.DataFrame()

                est_pronta = bool(stat_row.iloc[0]['estatistica_pronta']) if not stat_row.empty else False
                media_san = float(stat_row.iloc[0]['media_saneada']) if not stat_row.empty else 0.0
                mediana = float(stat_row.iloc[0]['mediana']) if not stat_row.empty else 0.0
                amostras = int(stat_row.iloc[0]['amostras']) if not stat_row.empty else 0

                df_validos, df_outliers = pd.DataFrame(), pd.DataFrame()
                if est_pronta:
                    p_val = df_p.copy()
                    m_val = pd.DataFrame()
                    if not df_m.empty:
                        filtro = (df_m['Preço'] > 0) & (df_m['Situação'].str.contains('Proposta recebida|Portal|Mídia|Contrataç', case=False, na=False, regex=True))
                        df_man_v = df_m[filtro].copy()
                        if not df_man_v.empty:
                            df_man_v["Origem"] = df_man_v.apply(lambda r: r['Link da fonte'] if pd.notna(r.get('Link da fonte')) and str(r.get('Link da fonte')).strip() else r.get('Descrição da fonte',''), axis=1)
                            df_man_v = df_man_v.rename(columns={"Data do Contato": "Data", "Empresa": "Empresa/Órgão"})
                            df_man_v["Item"] = row['Descrição']
                            df_man_v["Qtd"] = 1
                            df_man_v["Tipo"] = "Manual"
                            m_val = df_man_v[[c for c in cols_pncp if c in df_man_v.columns]]

                    frames = []
                    if not p_val.empty: frames.append(p_val)
                    if not m_val.empty: frames.append(m_val)
                    if frames:
                        df_merge = pd.concat(frames, ignore_index=True)
                        df_validados = df_merge[df_merge["Válido?"] == True].copy()
                        if not df_validados.empty:
                            df_v, df_o, _, _, _ = processar_precos_regra(df_validados, "Preços válidos - Mediana ±25% e Média")
                            df_validos = ordenar_validos(df_v)
                            df_outliers = ordenar_outliers(df_o)

                new_banco[new_hash] = {
                    "df_pncp": df_p, "df_manual_rastreio": df_m, "df_validacao": pd.DataFrame(columns=cols_pncp),
                    "historico_buscas": df_h,
                    "estatistica_pronta": est_pronta, "media_saneada": media_san, "mediana": mediana,
                    "amostras": amostras, "df_validos": df_validos, "df_outliers": df_outliers
                }
            st.session_state['banco_precos'] = new_banco
            st.session_state['acao_ativa'] = (None, None)
            return True
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        return False


# --- 7. INTERFACE DE ABAS ---
st.markdown("""
<div class="tj-header">
    <div style="display:flex; align-items:center;">
        <div>
            <div class="tj-logo-text">PODER JUDICIÁRIO</div>
            <div class="tj-logo-text" style="font-weight:400; font-size:14px;">Tribunal de Justiça do Estado de Goiás</div>
        </div>
    </div>
    <div class="tj-sub"><strong>Planejamento e Cotações</strong><br>Análise de Mercado Híbrida</div>
</div>
<div class="hero-container">
    <div class="hero-title">Sistema de Composição de Preços</div>
    <div class="hero-subtitle">Mapeamento de Demanda, Busca no PNCP e Cadastramento de Cotações Manuais</div>
</div>
""", unsafe_allow_html=True)

tab_tr, tab_cotacao, tab_resumo, tab_projeto, tab_bpm = st.tabs([
    "1. Estrutura da Demanda", 
    "2. Composição de Preços", 
    "3. Relatório Oficial",
    "4. Gestão de Projetos",
    "5. Mapeamento de Processos (BPM)"
])

# ==========================================
# ABA 1: ESTRUTURA DA DEMANDA
# ==========================================
with tab_tr:
    st.markdown("### Identificação da Contratação")
    
    if not st.session_state['tr_objeto_salvo']:
        st.info("💡 **Dica:** Você pode dar Ctrl+V para colar textos longos.")
        st.session_state['objeto_contratacao'] = st.text_area("Objeto da Demanda (Descrição Global)", value=st.session_state['objeto_contratacao'], height=100)
        c_obj_btn, _ = st.columns([1, 4])
        if c_obj_btn.button("💾 Salvar Objeto"):
            if st.session_state['objeto_contratacao'].strip():
                st.session_state['tr_objeto_salvo'] = True
                st.session_state['keywords_extraidas'] = extrair_palavras_chave(st.session_state['objeto_contratacao'], qtd_kw)
                st.rerun()
            else:
                st.error("Preencha a descrição do objeto antes de salvar.")
    else:
        st.info(f"**Objeto da Demanda:**\n\n{st.session_state['objeto_contratacao']}")
        c_obj_btn, _ = st.columns([1, 4])
        if c_obj_btn.button("✎ Editar Objeto"):
            st.session_state['tr_objeto_salvo'] = False
            st.rerun()
            
    st.markdown("---")
    st.markdown("### Estrutura de Lotes e Itens")
    if not st.session_state['tr_itens_salvos']:
        st.caption("Cole (Ctrl+V) dados da sua planilha. **Atenção:** Apenas 'Lote' e 'Item' exigem formato numérico obrigatório.")
        
        df_tr_editado = st.data_editor(
            st.session_state['df_tr'],
            num_rows="dynamic",
            column_config={
                "Lote": st.column_config.NumberColumn("Lote", help="Apenas números", step=1),
                "Item": st.column_config.NumberColumn("Item", required=True, step=1),
                "Descrição": st.column_config.TextColumn("Descrição do Objeto", required=True, width="large"),
                "Métrica": st.column_config.TextColumn("Métrica (Texto Livre)"),
                "Tipo": st.column_config.TextColumn("Tipo (Texto Livre)"),
                "Quantidade": st.column_config.TextColumn("Quantidade (Texto/Numérico)"),
            },
            use_container_width=True,
            hide_index=False
        )
        
        c_it_btn, _ = st.columns([1, 4])
        if c_it_btn.button("💾 Salvar Estrutura de Itens"):
            df_validos = df_tr_editado.dropna(subset=["Item", "Descrição"]).copy()
            if df_validos.empty:
                st.error("A tabela precisa ter ao menos um item válido com Número e Descrição.")
            else:
                df_validos['Lote'] = df_validos['Lote'].ffill()
                df_validos['Quantidade_Calc'] = pd.to_numeric(df_validos['Quantidade'], errors='coerce').fillna(1)
                
                st.session_state['df_tr'] = df_validos
                st.session_state['tr_itens_salvos'] = True
                
                for _, row in df_validos.iterrows():
                    h = gerar_hash_item(row)
                    if h not in st.session_state['banco_precos']:
                        st.session_state['banco_precos'][h] = {
                            "df_pncp": pd.DataFrame(columns=cols_pncp),
                            "df_manual_rastreio": pd.DataFrame(columns=cols_rastreio),
                            "df_validacao": pd.DataFrame(columns=cols_pncp), 
                            "historico_buscas": pd.DataFrame(columns=cols_historico_busca),
                            "estatistica_pronta": False,
                            "media_saneada": 0.0,
                            "mediana": 0.0,
                            "amostras": 0,
                            "df_validos": pd.DataFrame(),
                            "df_outliers": pd.DataFrame()
                        }
                st.rerun()
    else:
        df_validos = st.session_state['df_tr'].dropna(subset=["Item", "Descrição"])
        st.dataframe(df_validos.drop(columns=['Quantidade_Calc'], errors='ignore'), hide_index=True, use_container_width=True)
        c_it_btn, _ = st.columns([1, 4])
        if c_it_btn.button("✎ Editar Estrutura"):
            st.session_state['tr_itens_salvos'] = False
            st.rerun()

# ==========================================
# ABA 2: COMPOSIÇÃO DE PREÇOS E VALIDAÇÃO
# ==========================================
with tab_cotacao:
    if not st.session_state['tr_itens_salvos']:
        st.warning("⚠️ Finalize e clique em 'Salvar Estrutura de Itens' na Aba 1 antes de realizar as cotações.")
    else:
        df_validos_tr = st.session_state['df_tr'].dropna(subset=["Item", "Descrição"])
        
        st.markdown("### Painel de Ações por Item")
        st.markdown("<div style='background-color:#0F2C4C; color:white; padding:10px; border-radius:4px; font-weight:bold; display:flex;'>", unsafe_allow_html=True)
        c_h1, c_h2, c_h3, c_h4 = st.columns([1, 4, 1.5, 3.5])
        c_h1.write("Item (Lote)")
        c_h2.write("Descrição")
        c_h3.write("Status Preço")
        c_h4.write("Ações")
        st.markdown("</div>", unsafe_allow_html=True)

        for _, row in df_validos_tr.iterrows():
            h_id = gerar_hash_item(row)
            banco = st.session_state['banco_precos'].get(h_id)
            if not banco: continue

            lote_lbl = row['Lote'] if pd.notna(row['Lote']) and str(row['Lote']).strip() != "" else "Único"
            
            st.markdown("<div class='item-row'>", unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns([1, 4, 1.5, 3.5])
            c1.write(f"**{row['Item']}** ({lote_lbl})")
            c2.write(row['Descrição'])
            
            if banco['estatistica_pronta']:
                c3.markdown(f"<span style='color:green; font-weight:bold;'>✔ {formatar_moeda_simples(banco['media_saneada'])}</span>", unsafe_allow_html=True)
            else:
                c3.markdown("<span style='color:#64748B;'>Pendente</span>", unsafe_allow_html=True)
                
            with c4:
                btn_p, btn_c, btn_v = st.columns(3)
                if btn_p.button("🔍 PNCP", key=f"p_{h_id}", help="Buscar no PNCP", use_container_width=True):
                    st.session_state['acao_ativa'] = ("pncp", h_id)
                if btn_c.button("✍️ Cadastrar", key=f"c_{h_id}", help="Cotações Manuais", use_container_width=True):
                    st.session_state['acao_ativa'] = ("manual", h_id)
                if btn_v.button("⚖️ Validar", key=f"v_{h_id}", help="Validar tabelas isoladas", use_container_width=True):
                    st.session_state['acao_ativa'] = ("validar", h_id)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        
        acao, active_hash = st.session_state['acao_ativa']
        if acao and active_hash:
            df_matches = df_validos_tr[df_validos_tr.apply(gerar_hash_item, axis=1) == active_hash]
            if df_matches.empty:
                st.session_state['acao_ativa'] = (None, None)
                st.rerun()
            else:
                row_ativa = df_matches.iloc[0]
                nome_item_ativo = row_ativa['Descrição']
                banco_ativo = st.session_state['banco_precos'][active_hash]
                
                st.markdown(f"#### Área de Trabalho: {nome_item_ativo}")
                
                if acao == "pncp":
                    with st.form("form_pncp_busca"):
                        termo_sugerido = " ".join(nome_item_ativo.split()[:3])
                        termo_pncp = st.text_input("Termos de Busca:", value=termo_sugerido)
                        
                        if st.form_submit_button("Iniciar Extração Inteligente"):
                            if termo_pncp.strip():
                                engine = PNCPEngine()
                                status_ui = st.status("Iniciando varredura no PNCP...", expanded=True)
                                editais, tipo = engine.buscar_editais_inteligente(termo_pncp, paginas=paginas_pncp, status_placeholder=status_ui)
                                
                                if editais:
                                    status_ui.update(label=f"Editais localizados (Modo: {tipo}). Extraindo itens...", state="running")
                                    all_items = []
                                    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                                        futures = {executor.submit(engine.minerar_itens, ed, termo_pncp): ed for ed in editais}
                                        for f in concurrent.futures.as_completed(futures):
                                            res = f.result()
                                            if res: all_items.extend(res)
                                            
                                    if all_items:
                                        df_novos = pd.DataFrame(all_items)
                                        df_novos.insert(0, "Válido?", True)
                                        
                                        # Incremental: Adiciona aos já existentes
                                        banco_ativo["df_pncp"] = pd.concat([banco_ativo["df_pncp"], df_novos], ignore_index=True)
                                        
                                        # Log de Busca
                                        novo_log = {
                                            "Data/Hora": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"),
                                            "Termo Pesquisado": termo_pncp,
                                            "Novos Registros": len(all_items)
                                        }
                                        banco_ativo["historico_buscas"] = pd.concat([banco_ativo["historico_buscas"], pd.DataFrame([novo_log])], ignore_index=True)
                                        
                                        status_ui.update(label=f"Sucesso! {len(all_items)} cotações encontradas.", state="complete")
                                        st.success(f"Foram adicionados {len(all_items)} registros à sua validação (Busca: {tipo}).")
                                    else:
                                        status_ui.update(label="Nenhum item correspondente dentro dos editais.", state="error")
                                        st.error("A API retornou editais, mas a descrição interna dos itens não bateu com seus termos.")
                                else:
                                    status_ui.update(label="Nenhum resultado no PNCP.", state="error")
                                    st.warning("O PNCP não retornou nada, mesmo após tentativas de busca flexível.")
                            else:
                                st.warning("Insira um termo para buscar.")
                    
                    if not banco_ativo["historico_buscas"].empty:
                        st.markdown("##### 📜 Histórico de Buscas Realizadas")
                        st.dataframe(banco_ativo["historico_buscas"], hide_index=True, use_container_width=True)

                elif acao == "manual":
                    with st.form("form_add_contato"):
                        st.markdown("**Novo Registro**")
                        c1, c2, c3 = st.columns([1.5, 1, 1.5])
                        m_emp = c1.text_input("Empresa / Órgão Público")
                        m_cnpj = c2.text_input("CNPJ / CPF")
                        m_tipo_fonte = c3.selectbox("Tipo de Fonte (Art. 6º):", opcoes_origem_decreto)
                        
                        c4, c5 = st.columns([2, 2])
                        m_desc_fonte = c4.text_input("Descrição da Fonte")
                        m_link_fonte = c5.text_input("Link da Fonte (URL)")
                        
                        c6, c7, c8 = st.columns([1.5, 1.5, 1])
                        m_contato = c6.text_input("Nome do Contato")
                        m_email = c7.text_input("E-mail")
                        m_telefone = c8.text_input("Telefone")
                        
                        c9, c10, c11, c12 = st.columns([1, 1, 1.5, 1.5])
                        m_data = c9.date_input("Data do Contato", value=datetime.now(fuso_br))
                        m_hora = c10.time_input("Horário", value=datetime.now(fuso_br).time())
                        m_sit = c11.selectbox("Situação:", opcoes_situacao)
                        m_preco = c12.number_input("Preço Unitário (R$)", min_value=0.00, value=0.00, step=0.01)
                        
                        if st.form_submit_button("Registrar Histórico"):
                            erros = []
                            if not m_emp.strip(): erros.append("Empresa é obrigatório.")
                            cnpj_fmt = validar_formatar_cpf_cnpj(m_cnpj)
                            tel_fmt = validar_formatar_telefone(m_telefone)
                            
                            if erros:
                                for e in erros: st.error(e)
                            else:
                                novo_log = {
                                    "Data do Contato": m_data.strftime("%d/%m/%Y"),
                                    "Horário": m_hora.strftime("%H:%M"),
                                    "Empresa": m_emp,
                                    "CNPJ/CPF": cnpj_fmt if cnpj_fmt else "",
                                    "Tipo de fonte": m_tipo_fonte,
                                    "Descrição da fonte": m_desc_fonte,
                                    "Link da fonte": m_link_fonte,
                                    "Nome do Contato": m_contato,
                                    "E-mail": m_email,
                                    "Telefone": tel_fmt if tel_fmt else "",
                                    "Situação": m_sit,
                                    "Preço": float(m_preco),
                                    "Valor Unitário": formatar_moeda_ordenavel(m_preco)
                                }
                                banco_ativo["df_manual_rastreio"] = pd.concat([banco_ativo["df_manual_rastreio"], pd.DataFrame([novo_log])], ignore_index=True)
                                st.success("Adicionado!")
                                time.sleep(0.5)
                                st.rerun()
                    
                    if not banco_ativo["df_manual_rastreio"].empty:
                        df_rastreio_view = banco_ativo["df_manual_rastreio"].drop(columns=['Valor Unitário'], errors='ignore')
                        df_rastreio_editado = st.data_editor(
                            df_rastreio_view,
                            num_rows="dynamic",
                            column_config={"Preço": st.column_config.NumberColumn("Preço (R$)", format="R$ %.2f")},
                            use_container_width=True, hide_index=False, key=f"editor_rastreio_{active_hash}"
                        )
                        if not df_rastreio_editado.equals(df_rastreio_view):
                            df_rastreio_editado['Valor Unitário'] = df_rastreio_editado['Preço'].apply(formatar_moeda_ordenavel)
                            banco_ativo["df_manual_rastreio"] = df_rastreio_editado

                elif acao == "validar":
                    df_pncp_atual = banco_ativo["df_pncp"].copy()
                    if not df_pncp_atual.empty:
                        try:
                            df_pncp_atual['dt'] = pd.to_datetime(df_pncp_atual['Data'], format="%d/%m/%Y", errors='coerce')
                            limite_data = datetime.now(fuso_br) - relativedelta(months=meses_corte)
                            df_pncp_atual['dt'] = df_pncp_atual['dt'].dt.tz_localize(fuso_br)
                            df_pncp_atual = df_pncp_atual[(df_pncp_atual['dt'] >= limite_data)].copy()
                            df_pncp_atual = df_pncp_atual.drop(columns=['dt'])
                        except: pass
                    
                    df_man_full = banco_ativo["df_manual_rastreio"].copy()
                    df_man_valido = pd.DataFrame()
                    if not df_man_full.empty:
                        filtro = (df_man_full['Preço'] > 0) & (df_man_full['Situação'].str.contains('Proposta recebida|Portal|Mídia|Contrataç', case=False, na=False, regex=True))
                        df_man_valido = df_man_full[filtro].copy()
                        if not df_man_valido.empty:
                            df_man_valido["Origem"] = df_man_valido.apply(lambda r: r['Link da fonte'] if pd.notna(r.get('Link da fonte')) and str(r.get('Link da fonte')).strip() else r.get('Descrição da fonte',''), axis=1)
                            df_man_valido = df_man_valido.rename(columns={"Data do Contato": "Data", "Empresa": "Empresa/Órgão"})
                            df_man_valido["Item"] = nome_item_ativo
                            df_man_valido["Qtd"] = 1
                            df_man_valido["Tipo"] = "Manual"
                            df_man_valido["Válido?"] = True
                            df_man_valido = df_man_valido[[c for c in cols_pncp if c in df_man_valido.columns]]

                    with st.form("form_validacao_dupla"):
                        st.markdown("#### 1. Preços Editais Homologados (PNCP)")
                        if df_pncp_atual.empty:
                            st.info("Nenhum preço do PNCP capturado.")
                            pncp_resultado = pd.DataFrame()
                        else:
                            c_t1, _ = st.columns([1, 4])
                            sel_pncp = c_t1.radio("Selecionar PNCP:", ["Todos", "Nenhum"], index=0, horizontal=True)
                            df_pncp_atual["Válido?"] = True if sel_pncp == "Todos" else False
                            pncp_resultado = st.data_editor(
                                df_pncp_atual.drop(columns=['Preço', 'Tipo']),
                                column_config={"Válido?": st.column_config.CheckboxColumn("Válido?")},
                                disabled=["Data", "Empresa/Órgão", "Item", "Qtd", "Valor Unitário", "Origem"],
                                hide_index=True, use_container_width=True, key="val_pncp"
                            )
                            pncp_resultado["Preço"] = df_pncp_atual["Preço"]

                        st.markdown("#### 2. Cotações do Histórico Manual")
                        if df_man_valido.empty:
                            st.info("Nenhuma proposta manual classificada com preço válido.")
                            man_resultado = pd.DataFrame()
                        else:
                            c_t3, _ = st.columns([1, 4])
                            sel_man = c_t3.radio("Selecionar Manuais:", ["Todos", "Nenhum"], index=0, horizontal=True)
                            df_man_valido["Válido?"] = True if sel_man == "Todos" else False
                            man_resultado = st.data_editor(
                                df_man_valido.drop(columns=['Preço', 'Tipo']),
                                column_config={"Válido?": st.column_config.CheckboxColumn("Válido?")},
                                disabled=["Data", "Empresa/Órgão", "Item", "Qtd", "Valor Unitário", "Origem"],
                                hide_index=True, use_container_width=True, key="val_man"
                            )
                            man_resultado["Preço"] = df_man_valido["Preço"]

                        if st.form_submit_button("Calcular Mediana/Média com Preços Válidos", type="primary"):
                            frames_to_concat = []
                            if not pncp_resultado.empty: frames_to_concat.append(pncp_resultado)
                            if not man_resultado.empty: frames_to_concat.append(man_resultado)
                            
                            if not frames_to_concat:
                                st.error("Não há dados para calcular.")
                            else:
                                df_merge = pd.concat(frames_to_concat, ignore_index=True)
                                df_validados = df_merge[df_merge["Válido?"] == True].copy()
                                
                                if df_validados.empty:
                                    st.error("Você desmarcou todos os preços.")
                                else:
                                    df_v, df_o, m_geral, _, _ = processar_precos_regra(df_validados, regra_calculo)
                                    banco_ativo["df_validos"] = ordenar_validos(df_v)
                                    banco_ativo["df_outliers"] = ordenar_outliers(df_o)
                                    banco_ativo["media_saneada"] = df_v['Preço'].mean() if not df_v.empty else 0
                                    banco_ativo["mediana"] = m_geral
                                    banco_ativo["amostras"] = len(df_v)
                                    banco_ativo["estatistica_pronta"] = True
                                    
                                    st.success("Estatística salva com sucesso!")
                                    time.sleep(1)
                                    st.session_state['acao_ativa'] = (None, None)
                                    st.rerun()

                if banco_ativo["estatistica_pronta"]:
                    st.markdown("<br>", unsafe_allow_html=True)
                    l1_c1, l1_c2, l1_c3 = st.columns(3)
                    l1_c1.markdown(f"<div class='metric-card'><div class='metric-lbl'>Preço Final Adotado</div><div class='metric-val'>{formatar_moeda_simples(banco_ativo['media_saneada'])}</div></div>", unsafe_allow_html=True)
                    l1_c2.markdown(f"<div class='metric-card'><div class='metric-lbl'>Amostras Utilizadas</div><div class='metric-val'>{banco_ativo['amostras']}</div></div>", unsafe_allow_html=True)
                    maior_v = banco_ativo["df_validos"]['Preço'].max() if not banco_ativo["df_validos"].empty else 0
                    l1_c3.markdown(f"<div class='metric-card'><div class='metric-lbl'>Maior Valor Aceito</div><div class='metric-val'>{formatar_moeda_simples(maior_v)}</div></div>", unsafe_allow_html=True)

# ==========================================
# ABA 3: RELATÓRIO PDF NATIVO (XHTML2PDF)
# ==========================================
with tab_resumo:
    if not st.session_state['tr_objeto_salvo'] or not st.session_state['tr_itens_salvos']:
        st.warning("⚠️ Finalize o preenchimento da Aba 1 (Análise de Mercado) para visualizar o relatório.")
    else:
        df_validos_tr = st.session_state['df_tr'].dropna(subset=["Item", "Descrição"])
        
        lotes_dict = {}
        valor_total_global = 0.0
        
        for _, row in df_validos_tr.iterrows():
            lote_key = row["Lote"] if pd.notna(row["Lote"]) and str(row["Lote"]).strip() != "" else "Único"
            if lote_key not in lotes_dict: lotes_dict[lote_key] = []
            
            h_id = gerar_hash_item(row)
            banco = st.session_state['banco_precos'].get(h_id)
            if not banco: continue
            
            media_item = banco['media_saneada']
            qtd_num = row.get("Quantidade_Calc", 1)
            subtotal_item = media_item * qtd_num
            valor_total_global += subtotal_item
            
            lotes_dict[lote_key].append({
                "Item": row["Item"],
                "Descrição": row["Descrição"],
                "Qtd": row["Quantidade"],
                "Unid.": row["Métrica"],
                "Valor Ref. Unit.": formatar_moeda_ordenavel(media_item) if media_item > 0 else "Pendente",
                "Subtotal Estimado": formatar_moeda_ordenavel(subtotal_item) if media_item > 0 else "Pendente",
                "Amostras": banco['amostras'],
                "Preço Numérico": media_item 
            })
            
        st.markdown(f"""
        <div class='total-global-compact'>
            <div class='total-global-title'>VALOR TOTAL ESTIMADO DA CONTRATAÇÃO</div>
            <div class='total-global-value'>{formatar_moeda_simples(valor_total_global)}</div>
        </div>
        """, unsafe_allow_html=True)
            
        for nome_lote, itens in lotes_dict.items():
            cabecalho = f"Lote {nome_lote}" if nome_lote != "Único" else "Itens da Contratação"
            st.markdown(f"<h4 class='lote-header'>📦 {cabecalho}</h4>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(itens).drop(columns=['Preço Numérico']), hide_index=True, use_container_width=True)
            
        st.markdown("---")
        if st.button("📄 Gerar Relatório Analítico de Mercado (Download PDF)", type="primary"):
            data_emissao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
            obj_global = str(st.session_state['objeto_contratacao'])
            
            html_pdf = f"""
            <html>
            <head>
                <style>
                    @page {{
                        size: A4 portrait;
                        margin-top: 3.5cm;
                        margin-bottom: 2cm;
                        margin-left: 1.5cm;
                        margin-right: 1.5cm;
                        @frame header_frame {{ -pdf-frame-content: header_content; left: 1.5cm; right: 1.5cm; top: 1cm; height: 2.5cm; }}
                        @frame footer_frame {{ -pdf-frame-content: footer_content; left: 1.5cm; right: 1.5cm; bottom: 0.5cm; height: 1cm; }}
                    }}
                    body {{ font-family: "Times New Roman", Times, serif; font-size: 12px; color: black; line-height: 1; }}
                    p {{ margin: 0; padding: 0; text-align: justify; }}
                    h1, h2, h3, h4 {{ font-family: "Times New Roman", Times, serif; font-size: 12px; font-weight: bold; color: black; margin: 24px 0 6px 0; padding: 0; }}
                    table {{ width: 100%; border-collapse: collapse; border: 0.25pt solid #666; table-layout: fixed; margin: 0; }}
                    th, td {{ border: 0.25pt solid #666; padding: 4px; font-size: 10px; vertical-align: middle; word-wrap: break-word; }}
                    th {{ font-weight: bold; text-align: center; background-color: #f2f2f2; }}
                    .right-txt {{ text-align: right; font-weight: bold; }}
                    .center-txt {{ text-align: center; }}
                </style>
            </head>
            <body>
                <div id="header_content">
                    <table>
                        <tr>
                            <td rowspan="3" style="width: 35%; text-align: center; vertical-align: middle;">
                                <span style="font-family: Arial, Helvetica, sans-serif; font-size: 14px; font-weight: bold;">PODER JUDICIÁRIO</span><br>
                                <span style="font-family: Arial, Helvetica, sans-serif; font-size: 11px;">Tribunal de Justiça do Estado de Goiás</span><br>
                                <span style="font-family: Arial, Helvetica, sans-serif; font-size: 9px; color: #555555;">Coordenadoria de Contratos e Aquisições de TIC</span>
                            </td>
                            <td colspan="3" style="width: 65%; text-align: center; font-size: 14px; font-weight: bold; vertical-align: middle;">
                                ANÁLISE DE MERCADO
                            </td>
                        </tr>
                        <tr>
                            <td colspan="3" style="text-align: center; font-size: 12px; font-weight: bold; vertical-align: middle;">
                                Processo de Planejamento de Aquisições e de Contratações de Soluções de TIC
                            </td>
                        </tr>
                        <tr>
                            <td style="width: 25%; text-align: center; font-size: 11px; vertical-align: middle;"><b>Revisão:</b> 008</td>
                            <td style="width: 25%; text-align: center; font-size: 11px; vertical-align: middle;"><b>Código/Versão:</b> CCA-006</td>
                            <td style="width: 15%; text-align: center; font-size: 11px; vertical-align: middle;"><b>Página:</b> <pdf:pagenumber> / <pdf:pagecount></td>
                        </tr>
                    </table>
                </div>
                
                <div id="footer_content">
                    <p style="text-align: right; font-size: 10px;">Documento gerado eletronicamente em {data_emissao}</p>
                </div>

                <h1 style="margin-top:0;">OBJETO</h1>
                <p>{obj_global}</p>
                
                <h1>METODOLOGIA</h1>
                <p><b>Estatística Aplicada:</b> {regra_calculo}</p>
                <p class="right-txt" style="font-size:14px; margin-top: 10px;">VALOR TOTAL ESTIMADO: {formatar_moeda_simples(valor_total_global)}</p>
            """
            
            for nome_lote, itens in lotes_dict.items():
                titulo = f"LOTE {nome_lote}" if nome_lote != "Único" else "QUADRO DE ITENS"
                html_pdf += f"<br><h2>{titulo}</h2>"
                html_pdf += "<table repeat-header='yes'><thead><tr><th width='5%'>Item</th><th width='40%'>Descrição</th><th width='5%'>Qtd</th><th width='10%'>Unid.</th><th width='20%'>Valor Ref. Unit.</th><th width='20%'>Subtotal</th></tr></thead><tbody>"
                subt_lote = 0.0
                for it in itens:
                    try: q = float(it['Qtd']) 
                    except: q = 1
                    subt_item_val = it['Preço Numérico'] * q
                    subt_lote += subt_item_val
                    html_pdf += f"<tr><td class='center-txt'>{it['Item']}</td><td>{it['Descrição']}</td><td class='center-txt'>{it['Qtd']}</td><td class='center-txt'>{it['Unid.']}</td><td class='center-txt'>{formatar_moeda_simples(it['Preço Numérico'])}</td><td class='center-txt'>{formatar_moeda_simples(subt_item_val)}</td></tr>"
                html_pdf += f"<tr><td colspan='5' class='right-txt'>Subtotal {titulo}:</td><td class='center-txt'><b>{formatar_moeda_simples(subt_lote)}</b></td></tr></tbody></table>"
            
            html_pdf += "<br><h1>ANEXO I - RELATÓRIO DE RASTREABILIDADE (ART. 6º)</h1>"
            for _, row in df_validos_tr.iterrows():
                h_id = gerar_hash_item(row)
                banco = st.session_state['banco_precos'].get(h_id)
                if not banco: continue
                df_rastreio = banco['df_manual_rastreio']
                
                if not df_rastreio.empty:
                    html_pdf += f"<h2>ITEM {row['Item']}: {row['Descrição']}</h2>"
                    html_pdf += "<table repeat-header='yes'><thead><tr><th width='20%'>Empresa (CNPJ)</th><th width='25%'>Fonte da Pesquisa</th><th width='20%'>Contato (E-mail/Tel)</th><th width='10%'>Data/Hora</th><th width='15%'>Situação</th><th width='10%'>Preço</th></tr></thead><tbody>"
                    for _, r_log in df_rastreio.iterrows():
                        nome_doc = f"{r_log.get('Empresa','')}<br>{r_log.get('CNPJ/CPF','')}"
                        fonte_base = f"<b>{str(r_log.get('Tipo de fonte',''))[:15]}</b><br>{r_log.get('Descrição da fonte', '')}"
                        cont_doc = f"{r_log.get('Nome do Contato','')}<br>{r_log.get('E-mail','')}<br>{r_log.get('Telefone','')}"
                        dh_doc = f"{r_log.get('Data do Contato','')}<br>{r_log.get('Horário','')}"
                        pr = r_log.get('Preço', 0)
                        pr_doc = formatar_moeda_simples(pr) if pr > 0 else "-"
                        html_pdf += f"<tr><td>{nome_doc}</td><td>{fonte_base}</td><td>{cont_doc}</td><td class='center-txt'>{dh_doc}</td><td>{r_log.get('Situação','')}</td><td class='center-txt'>{pr_doc}</td></tr>"
                    html_pdf += "</tbody></table>"

            html_pdf += "<br><h1>ANEXO II - COMPOSIÇÃO ESTATÍSTICA FINAL</h1>"
            for _, row in df_validos_tr.iterrows():
                h_id = gerar_hash_item(row)
                banco = st.session_state['banco_precos'].get(h_id)
                if not banco: continue
                
                html_pdf += f"<h2>ITEM {row['Item']}: {row['Descrição']}</h2>"
                html_pdf += f"<p><b>Média Saneada Aplicada:</b> {formatar_moeda_simples(banco['media_saneada'])} | <b>Amostras Válidas:</b> {banco['amostras']}</p>"
                
                df_v = banco['df_validos']
                if not df_v.empty:
                    html_pdf += "<h2>Preços Válidos Adotados no Cálculo</h2>"
                    html_pdf += "<table repeat-header='yes'><thead><tr><th width='12%'>Data</th><th width='30%'>Empresa/Órgão</th><th width='18%'>Valor Unit.</th><th width='40%'>Origem (Fundamento)</th></tr></thead><tbody>"
                    for _, r in df_v.iterrows():
                        orig_str = str(r['Origem'])[:150] + "..." if len(str(r['Origem'])) > 150 else str(r['Origem'])
                        html_pdf += f"<tr><td class='center-txt'>{r['Data']}</td><td>{r['Empresa/Órgão']}</td><td class='center-txt'>{formatar_moeda_simples(r['Preço'])}</td><td>{orig_str}</td></tr>"
                    html_pdf += "</tbody></table>"
                    
                df_o = banco['df_outliers']
                if not df_o.empty:
                    html_pdf += "<h2>Preços Descartados (Outliers ou Desmarcados Manualmente)</h2>"
                    html_pdf += "<table repeat-header='yes'><thead><tr><th width='12%'>Data</th><th width='30%'>Empresa/Órgão</th><th width='18%'>Valor Unit.</th><th width='40%'>Origem (Fundamento)</th></tr></thead><tbody>"
                    for _, r in df_o.iterrows():
                        orig_str = str(r['Origem'])[:150] + "..." if len(str(r['Origem'])) > 150 else str(r['Origem'])
                        html_pdf += f"<tr><td class='center-txt'>{r['Data']}</td><td>{r['Empresa/Órgão']}</td><td class='center-txt'>{formatar_moeda_simples(r['Preço'])}</td><td>{orig_str}</td></tr>"
                    html_pdf += "</tbody></table>"
            
            html_pdf += "</body></html>"
            
            result_pdf = io.BytesIO()
            pdf = pisa.CreatePDF(src=html_pdf, dest=result_pdf, encoding='utf-8')
            
            if not pdf.err:
                st.download_button(
                    label="📥 Baixar Arquivo PDF Oficial",
                    data=result_pdf.getvalue(),
                    file_name="Analise_de_Mercado_Oficial.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            else:
                st.error("Erro interno ao gerar o PDF.")

# ==========================================
# ABA 4: GESTÃO DE PROJETO
# ==========================================
with tab_projeto:
    st.markdown("### Salvar / Exportar Projeto")
    fmt_export = st.selectbox("Formato de Exportação:", ["JSON (Recomendado)", "XLSX (Excel)", "ODS (LibreOffice)", "CSV (ZIP)"])
    if st.button("Gerar Arquivo de Backup"):
        with st.spinner("Empacotando dados do projeto..."):
            data, filename, mime = gerar_arquivo_exportacao(fmt_export)
            st.download_button("📥 Baixar Arquivo de Projeto", data=data, file_name=filename, mime=mime, type="primary")
            
    st.markdown("---")
    st.markdown("### Carregar / Importar Projeto")
    up_file = st.file_uploader("Arraste seu arquivo de backup (.json, .xlsx, .ods, .zip)", type=["json", "xlsx", "ods", "zip"])
    if up_file:
        if st.button("Carregar Projeto"):
            with st.spinner("Restaurando ambiente..."):
                sucesso = carregar_projeto(up_file)
                if sucesso:
                    st.success("Projeto restaurado com sucesso!")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# ABA 5: MAPEAMENTO DE PROCESSOS (BPM) E BPMN VISUAL
# ==========================================
with tab_bpm:
    st.markdown("### Modelador Visual (BPMN 2.0)")
    st.caption("Você pode arrastar, conectar, criar novas tarefas e salvar este desenho em SVG ou BPMN utilizando a barra inferior.")
    
    # XML com caixas LARGAS (150px) para acomodar os textos corretamente sem quebrar as bordas
    bpmn_xml_padrao = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="Process_1" isExecutable="false">
        <bpmn:startEvent id="StartEvent_1" name="Início">
          <bpmn:outgoing>Flow_1</bpmn:outgoing>
        </bpmn:startEvent>
        <bpmn:task id="Task_1" name="Identificação da Contratação">
          <bpmn:incoming>Flow_1</bpmn:incoming>
          <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:task>
        <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1" />
        <bpmn:task id="Task_2" name="Estruturação de Lotes">
          <bpmn:incoming>Flow_2</bpmn:incoming>
          <bpmn:outgoing>Flow_3</bpmn:outgoing>
        </bpmn:task>
        <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="Task_2" />
        <bpmn:task id="Task_3" name="Extração PNCP">
          <bpmn:incoming>Flow_3</bpmn:incoming>
          <bpmn:outgoing>Flow_4</bpmn:outgoing>
        </bpmn:task>
        <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_2" targetRef="Task_3" />
        <bpmn:task id="Task_4" name="Cotação Direta">
          <bpmn:incoming>Flow_4</bpmn:incoming>
          <bpmn:outgoing>Flow_5</bpmn:outgoing>
        </bpmn:task>
        <bpmn:sequenceFlow id="Flow_4" sourceRef="Task_3" targetRef="Task_4" />
        <bpmn:task id="Task_5" name="Validação Estatística">
          <bpmn:incoming>Flow_5</bpmn:incoming>
          <bpmn:outgoing>Flow_6</bpmn:outgoing>
        </bpmn:task>
        <bpmn:sequenceFlow id="Flow_5" sourceRef="Task_4" targetRef="Task_5" />
        <bpmn:task id="Task_6" name="Geração Relatório PDF">
          <bpmn:incoming>Flow_6</bpmn:incoming>
          <bpmn:outgoing>Flow_7</bpmn:outgoing>
        </bpmn:task>
        <bpmn:sequenceFlow id="Flow_6" sourceRef="Task_5" targetRef="Task_6" />
        <bpmn:endEvent id="EndEvent_1" name="Fim">
          <bpmn:incoming>Flow_7</bpmn:incoming>
        </bpmn:endEvent>
        <bpmn:sequenceFlow id="Flow_7" sourceRef="Task_6" targetRef="EndEvent_1" />
      </bpmn:process>
      <bpmndi:BPMNDiagram id="BPMNDiagram_1">
        <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
          <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
            <dc:Bounds x="152" y="102" width="36" height="36" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1">
            <dc:Bounds x="240" y="80" width="150" height="80" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="Task_2_di" bpmnElement="Task_2">
            <dc:Bounds x="440" y="80" width="150" height="80" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="Task_3_di" bpmnElement="Task_3">
            <dc:Bounds x="640" y="80" width="150" height="80" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="Task_4_di" bpmnElement="Task_4">
            <dc:Bounds x="840" y="80" width="150" height="80" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="Task_5_di" bpmnElement="Task_5">
            <dc:Bounds x="1040" y="80" width="150" height="80" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="Task_6_di" bpmnElement="Task_6">
            <dc:Bounds x="1240" y="80" width="150" height="80" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="EndEvent_1_di" bpmnElement="EndEvent_1">
            <dc:Bounds x="1440" y="102" width="36" height="36" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
            <di:waypoint x="188" y="120" />
            <di:waypoint x="240" y="120" />
          </bpmndi:BPMNEdge>
          <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
            <di:waypoint x="390" y="120" />
            <di:waypoint x="440" y="120" />
          </bpmndi:BPMNEdge>
          <bpmndi:BPMNEdge id="Flow_3_di" bpmnElement="Flow_3">
            <di:waypoint x="590" y="120" />
            <di:waypoint x="640" y="120" />
          </bpmndi:BPMNEdge>
          <bpmndi:BPMNEdge id="Flow_4_di" bpmnElement="Flow_4">
            <di:waypoint x="790" y="120" />
            <di:waypoint x="840" y="120" />
          </bpmndi:BPMNEdge>
          <bpmndi:BPMNEdge id="Flow_5_di" bpmnElement="Flow_5">
            <di:waypoint x="990" y="120" />
            <di:waypoint x="1040" y="120" />
          </bpmndi:BPMNEdge>
          <bpmndi:BPMNEdge id="Flow_6_di" bpmnElement="Flow_6">
            <di:waypoint x="1190" y="120" />
            <di:waypoint x="1240" y="120" />
          </bpmndi:BPMNEdge>
          <bpmndi:BPMNEdge id="Flow_7_di" bpmnElement="Flow_7">
            <di:waypoint x="1390" y="120" />
            <di:waypoint x="1440" y="120" />
          </bpmndi:BPMNEdge>
        </bpmndi:BPMNPlane>
      </bpmndi:BPMNDiagram>
    </bpmn:definitions>"""

    html_modeler = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8" />
      <link rel="stylesheet" href="https://unpkg.com/bpmn-js@14.0.0/dist/assets/diagram-js.css" />
      <link rel="stylesheet" href="https://unpkg.com/bpmn-js@14.0.0/dist/assets/bpmn-js.css" />
      <link rel="stylesheet" href="https://unpkg.com/bpmn-js@14.0.0/dist/assets/bpmn-font/css/bpmn.css" />
      <style>
        html, body {{ height: 100%; margin: 0; padding: 0; font-family: sans-serif; }}
        #canvas {{ height: 90vh; width: 100%; border: 1px solid #ccc; background-color: white; }}
        .bjs-powered-by {{ display: none; }}
        .djs-label {{ font-family: Arial, sans-serif !important; font-size: 12px !important; line-height: 1.2 !important; }}
        .toolbar {{ height: 10vh; display: flex; align-items: center; justify-content: center; background-color: #F8FAFC; gap: 15px; border: 1px solid #ccc; border-top: none; }}
        button {{ background-color: #0F2C4C; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }}
        button:hover {{ background-color: #0B223D; }}
      </style>
    </head>
    <body>
      <div id="canvas"></div>
      <div class="toolbar">
          <button onclick="downloadSVG()">Baixar Diagrama (SVG)</button>
          <button onclick="downloadBPMN()">Baixar Diagrama (BPMN)</button>
      </div>
      
      <script src="https://unpkg.com/bpmn-js@14.0.0/dist/bpmn-modeler.development.js"></script>
      <script>
        var bpmnModeler = new BpmnJS({{
          container: '#canvas',
          keyboard: {{ bindTo: window }}
        }});

        var bpmnXML = `{bpmn_xml_padrao}`;

        bpmnModeler.importXML(bpmnXML).then(function(result) {{
            bpmnModeler.get('canvas').zoom('fit-viewport');
        }}).catch(function(err) {{
            console.error('Falha ao renderizar BPMN', err);
        }});

        function downloadSVG() {{
            bpmnModeler.saveSVG({{ format: true }}).then(function(result) {{
                var blob = new Blob([result.svg], {{ type: 'image/svg+xml' }});
                var url = window.URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'Mapeamento_Processo_Mercado.svg';
                a.click();
            }});
        }}

        function downloadBPMN() {{
            bpmnModeler.saveXML({{ format: true }}).then(function(result) {{
                var blob = new Blob([result.xml], {{ type: 'application/bpmn20-xml' }});
                var url = window.URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'Mapeamento_Processo_Mercado.bpmn';
                a.click();
            }});
        }}
      </script>
    </body>
    </html>
    """
    
    components.html(html_modeler, height=700)

# --- FOOTER ---
st.markdown("""
<div class="tj-footer">
    © 2026 Poder Judiciário do Estado de Goiás<br>
    Sistema de Apoio ao Planejamento da Contratação (Fase Interna)
</div>
""", unsafe_allow_html=True)