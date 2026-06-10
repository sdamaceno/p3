import streamlit as st # type: ignore[import]
import pandas as pd
import concurrent.futures
import time
import io
import re
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

from utils import formatar_moeda_simples, formatar_moeda_ordenavel, gerar_hash_item, parse_numero_localizado
from estatistica import processar_precos_regra, ordenar_validos, ordenar_outliers
from pncp_api import PNCPEngine
from pdf_engine import gerar_pdf_oficial
import typography
import layout
import components
from texts import get_text

st.set_page_config(page_title=get_text("NOME_SISTEMA"), layout="wide", initial_sidebar_state="collapsed")
fuso_br = timezone(timedelta(hours=-3))

typography.load()
layout.load()
components.load()

# Motor Avançado de Extração Semântica e Estrutural (Smart Extract)
def processar_arquivo_inteligente(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    texto = ""
    df_final = pd.DataFrame()
    objeto_str = ""
    try:
        if ext in ['xlsx', 'xls', 'ods']: 
            df_final = pd.read_excel(uploaded_file)
        elif ext in ['csv']: 
            df_final = pd.read_csv(uploaded_file, delimiter=';')
        elif ext == 'pdf':
            import pdfplumber
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    texto += page.extract_text() + "\n"
                    tabs = page.extract_tables()
                    if tabs and df_final.empty:
                        for t in tabs:
                            if t and len(t) > 1 and len(t[0]) >= 4:
                                cols = [str(c).strip() if c else f"Col_{idx}" for idx, c in enumerate(t[0])]
                                df_final = pd.DataFrame(t[1:], columns=cols)
                                break
        elif ext in ['docx', 'doc']:
            import docx
            doc = docx.Document(uploaded_file)
            texto = "\n".join([p.text for p in doc.paragraphs])
            if doc.tables and df_final.empty:
                t = doc.tables[0]
                data = [[cell.text.strip() for cell in row.cells] for row in t.rows]
                if len(data) > 1:
                    cols = [str(c).strip() if c else f"Col_{idx}" for idx, c in enumerate(data[0])]
                    df_final = pd.DataFrame(data[1:], columns=cols)
        elif ext == 'odt':
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(uploaded_file) as z:
                content_xml = z.read('content.xml')
                root = ET.fromstring(content_xml)
                paragraphs = []
                for el in root.iter():
                    if el.tag.endswith('}p') or el.tag.endswith('}h'):
                        txt = "".join(el.itertext()).strip()
                        if txt: 
                            paragraphs.append(txt)
                texto = "\n".join(paragraphs)
                
                tabelas_odt = []
                for table in root.iter('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table'):
                    rows_data = []
                    for row in table.iter('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-row'):
                        row_cells = []
                        for cell in row.iter('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-cell'):
                            cell_text = "".join(cell.itertext()).strip()
                            row_cells.append(cell_text)
                        if any(row_cells): 
                            rows_data.append(row_cells)
                    if len(rows_data) > 1:
                        max_cols = max(len(r) for r in rows_data)
                        for r in rows_data:
                            while len(r) < max_cols: 
                                r.append("")
                        cols = [str(c).strip() if c else f"Col_{idx}" for idx, c in enumerate(rows_data[0])]
                        df_potencial = pd.DataFrame(rows_data[1:], columns=cols)
                        if len(df_potencial.columns) >= 4:
                            tabelas_odt.append(df_potencial)
                if tabelas_odt and df_final.empty:
                    df_final = tabelas_odt[0]
        elif ext in ['md', 'txt']:
            texto = uploaded_file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        st.error(f"Erro no processador de arquivos do Design System: {e}")

    if texto:
        match = re.search(r'(?i)1\.\s*OBJETO\s*(.*?)(?=\n\s*[2-9]\.\s|ESTRUTURA DE LOTES|Lote\s|Item\s|2\.\s|3\.\s|$)', texto, re.DOTALL)
        objeto_str = match.group(1).strip() if match else texto[:1500]
        
        if df_final.empty and '\t' in texto:
            linhas = texto.split('\n')
            for i, l in enumerate(linhas):
                if '\t' in l:
                    try:
                        tabela_str = "\n".join(linhas[i:]).strip()
                        df_raw = pd.read_csv(io.StringIO(tabela_str), sep='\t', header=None, dtype=str)
                        df_final = df_raw.fillna("").apply(lambda x: x.str.strip().str.replace('"', ''))
                    except: 
                        pass
                    break

    if not df_final.empty:
        colunas_oficiais = ["Lote", "Item", "Descrição", "Métrica", "Tipo", "Quantidade"]
        mapa_chaves = {"lote": "Lote", "item": "Item", "descri": "Descrição", "métric": "Métrica", "metric": "Métrica", "tipo": "Tipo", "quant": "Quantidade", "qtd": "Quantidade"}
        try:
            df_final.columns = df_final.columns.astype(str).str.strip()
            primeira_linha = df_final.columns.str.lower()
            
            if any(any(chave in celula for chave in mapa_chaves.keys()) for celula in primeira_linha):
                df_mapeado = pd.DataFrame()
                for k, v in mapa_chaves.items():
                    for col in df_final.columns:
                        if k in str(col).lower():
                            df_mapeado[v] = df_final[col]
                            break
                for col in colunas_oficiais:
                    if col not in df_mapeado.columns: 
                        df_mapeado[col] = ""
                df_final = df_mapeado[colunas_oficiais]
            else:
                primeira_linha_dados = df_final.iloc[0].astype(str).str.lower().str.strip()
                if any(any(chave in celula for chave in mapa_chaves.keys()) for celula in primeira_linha_dados):
                    indice_mapeado = {mapa_chaves[k]: idx for idx, cel in enumerate(primeira_linha_dados) for k in mapa_chaves if k in cel}
                    dados_uteis = df_final.iloc[1:].reset_index(drop=True)
                    df_mapeado = pd.DataFrame(columns=colunas_oficiais)
                    for col in colunas_oficiais: 
                        df_mapeado[col] = dados_uteis.iloc[:, indice_mapeado[col]] if col in indice_mapeado else ""
                    df_final = df_mapeado
                else:
                    df_pos = pd.DataFrame(columns=colunas_oficiais)
                    for i, col in enumerate(colunas_oficiais):
                        df_pos[col] = df_final.iloc[:, i] if i < len(df_final.columns) else ""
                    df_final = df_pos
        except: 
            pass

        df_final['Lote'] = df_final.get('Lote', pd.Series(dtype=str)).replace(r'^\s*$', pd.NA, regex=True).ffill()
        df_final['Quantidade'] = df_final.get('Quantidade', pd.Series(dtype=str)).apply(parse_numero_localizado)
        df_final = df_final.dropna(subset=["Item", "Descrição"]).copy()

    return objeto_str, df_final

cols_pncp = ["Válido?", "Data", "Empresa/Órgão", "Item", "Qtd", "Preço", "Valor Unitário", "Origem", "Tipo"]
cols_rastreio = ["Data do Contato", "Horário", "Empresa", "CNPJ/CPF", "Tipo de fonte", "Descrição da fonte", "Link da fonte", "Nome do Contato", "E-mail", "Telefone", "Situação", "Preço", "Valor Unitário"]
cols_historico_busca = ["Data/Hora", "Termo Pesquisado", "Novos Registros"]
opcoes_origem_decreto = ["VI - Pesquisa direta c/ fornecedores", "I - Base estadual NFe", "II - Portal de Compras GO", "III - PNCP / Ferramentas específicas", "IV - Mídia / Tabelas / Sítios eletrônicos", "V - Contratações similares da adm. pública"]
opcoes_situacao = ["Solicitação de proposta enviada", "Confirmação de recebimento da solicitação", "Proposta recebida", "Não enviou proposta comercial", "Proposta recebida com equívoco", "Proposta retificada recebida"]

CONFIG_COLUNAS_TABELA = {
    "Lote": st.column_config.TextColumn("Lote", width=55),
    "Item": st.column_config.TextColumn("Item", width=55),
    "Descrição": st.column_config.TextColumn("Descrição do Objeto", required=True, width=450),
    "Métrica": st.column_config.TextColumn("Métrica", width=85),
    "Tipo": st.column_config.TextColumn("Tipo", width=95),
    "Quantidade": st.column_config.NumberColumn("Quantidade", width=85, format="%g"),
}

if 'lista_contratacoes' not in st.session_state:
    st.session_state['lista_contratacoes'] = [{ "id": 1, "titulo": "Contratação 1", "pca": "", "demanda": "", "tr_objeto_salvo": False, "tr_itens_salvos": False, "objeto_contratacao": "", "df_tr": pd.DataFrame(columns=["Lote", "Item", "Descrição", "Métrica", "Tipo", "Quantidade"]), "banco_precos": {}, "acao_ativa": (None, None), "regra_calculo": "Preços válidos - Mediana ±25% e Média", "meses_corte": 24, "paginas_pncp": 3, "delay_pncp": None, "palavras_chave_massa": {}, "massa_status": "idle", "massa_idx": 0, "massa_total": 0, "massa_novos": 0 }]

for ctx in st.session_state['lista_contratacoes']:
    if 'massa_status' not in ctx:
        ctx['massa_status'] = 'idle'
        ctx['massa_idx'] = 0
        ctx['massa_total'] = 0
        ctx['massa_novos'] = 0
    if 'pca' not in ctx:
        ctx['pca'] = ""
        ctx['demanda'] = ""

st.markdown(f"<h1>{get_text('NOME_SISTEMA')}</h1>", unsafe_allow_html=True)

for idx_c, ctx in enumerate(st.session_state['lista_contratacoes']):
    with st.expander(ctx['titulo'], expanded=(idx_c == len(st.session_state['lista_contratacoes']) - 1)):
        c_nome, c_pca = st.columns([3, 1], gap="medium")
        with c_nome: 
            ctx['titulo'] = components.text_input(get_text("LBL_RENOMEAR_CONTRATACAO"), value=ctx['titulo'], key=f"ren_title_{ctx['id']}")
        with c_pca: 
            ctx['pca'] = components.text_input(get_text("LBL_PCA"), value=ctx['pca'], placeholder=get_text("PH_PCA"), key=f"pca_{ctx['id']}")
        ctx['demanda'] = components.text_input(get_text("LBL_DEMANDA"), value=ctx['demanda'], key=f"demanda_{ctx['id']}")
        
        layout.divider_sub()
        
        on_objeto = components.toggle(f"{get_text('GRP_OBJETO')}", value=True, key=f"tg_obj_{ctx['id']}")
        if on_objeto:
            col_obj, col_itens = st.columns([1, 2], gap="large")
            if not ctx['tr_objeto_salvo']:
                with col_obj:
                    layout.title_section(get_text('LBL_COL_ESQ'))
                    txt_input = components.text_area(value=ctx['objeto_contratacao'], placeholder=get_text("LBL_DICA_COLA"), key=f"obj_area_{ctx['id']}")
                
                with col_itens:
                    layout.title_section(get_text('LBL_COL_DIR'))
                    df_tr_editado = components.data_editor(ctx['df_tr'], column_config=CONFIG_COLUNAS_TABELA, key=f"editor_tr_{ctx['id']}")
                
                with col_obj:
                    c_btn1, c_btn2 = st.columns([1, 1], gap="medium")
                    with c_btn1:
                        if components.button_primary(get_text("BTN_SALVAR_OBJ"), key=f"save_obj_btn_{ctx['id']}"):
                            if txt_input.strip():
                                ctx['objeto_contratacao'] = txt_input.strip()
                                df_validos = df_tr_editado.dropna(subset=["Item", "Descrição"]).copy()
                                df_validos['Lote'] = df_validos['Lote'].replace(r'^\s*$', pd.NA, regex=True).ffill()
                                df_validos['Quantidade'] = df_validos['Quantidade'].apply(parse_numero_localizado)
                                
                                ctx['df_tr'] = df_validos
                                ctx['tr_objeto_salvo'] = True
                                ctx['tr_itens_salvos'] = True
                                
                                for _, row in df_validos.iterrows():
                                    h = gerar_hash_item(row)
                                    if h not in ctx['banco_precos']:
                                        ctx['banco_precos'][h] = {"df_pncp": pd.DataFrame(columns=cols_pncp), "df_manual_rastreio": pd.DataFrame(columns=cols_rastreio), "historico_buscas": pd.DataFrame(columns=cols_historico_busca), "estatistica_pronta": False, "media_saneada": 0.0, "mediana": 0.0, "amostras": 0, "df_validos": pd.DataFrame(), "df_outliers": pd.DataFrame()}
                                st.rerun()
                                
                    with c_btn2:
                        up_file_tr = components.file_uploader(key=f"up_{ctx['id']}")
                        if up_file_tr:
                            obj_texto, df_extraido = processar_arquivo_inteligente(up_file_tr)
                            if obj_texto or not df_extraido.empty:
                                if obj_texto: 
                                    ctx['objeto_contratacao'] = obj_texto
                                    ctx['tr_objeto_salvo'] = True
                                if not df_extraido.empty:
                                    ctx['df_tr'] = df_extraido
                                    ctx['tr_itens_salvos'] = True
                                    
                                    for _, row in df_extraido.iterrows():
                                        h = gerar_hash_item(row)
                                        if h not in ctx['banco_precos']:
                                            ctx['banco_precos'][h] = {"df_pncp": pd.DataFrame(columns=cols_pncp), "df_manual_rastreio": pd.DataFrame(columns=cols_rastreio), "historico_buscas": pd.DataFrame(columns=cols_historico_busca), "estatistica_pronta": False, "media_saneada": 0.0, "mediana": 0.0, "amostras": 0, "df_validos": pd.DataFrame(), "df_outliers": pd.DataFrame()}
                                st.success(get_text("MSG_SUCESSO_IMPORT"))
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Falha estrutural: Nenhuma descrição (1. OBJETO) ou tabela de itens válida foi reconhecida no arquivo.")
            else:
                with col_obj:
                    layout.title_section(get_text('LBL_COL_ESQ'))
                    st.info(ctx['objeto_contratacao'])
                    if components.button_secondary(get_text("BTN_EDITAR_OBJ"), key=f"edt_obj_btn_{ctx['id']}"):
                        ctx['tr_objeto_salvo'] = False
                        ctx['tr_itens_salvos'] = False
                        st.rerun()
                with col_itens:
                    layout.title_section(get_text('LBL_COL_DIR'))
                    components.dataframe(ctx['df_tr'].dropna(subset=["Item", "Descrição"]), column_config=CONFIG_COLUNAS_TABELA)

        layout.divider_sub()

        # --- SUBGRUPO 2: ANÁLISE DE MERCADO ---
        on_analise = components.toggle(f"{get_text('GRP_ANALISE')}", value=True, key=f"tg_anl_{ctx['id']}")
        if on_analise:
            if ctx['tr_itens_salvos']:
                df_validos_tr = ctx['df_tr'].dropna(subset=["Item", "Descrição"])
                qtd_itens = len(df_validos_tr)
                delay_sugerido = 1 if qtd_itens <= 3 else (3 if qtd_itens <= 10 else 5)
                if ctx['delay_pncp'] is None: ctx['delay_pncp'] = delay_sugerido
                
                layout.title_section(get_text('TITULO_PARAMETROS'))
                c_p1, c_p2, c_p3, c_p4 = st.columns(4, gap="small")
                with c_p1: ctx['regra_calculo'] = components.selectbox(get_text("LBL_REGRA_CALCULO"), ["Preços válidos - Mediana ±25% e Média"], key=f"regra_calc_{ctx['id']}")
                with c_p2: ctx['meses_corte'] = components.slider(get_text("LBL_MESES_CORTE"), min_value=12, max_value=60, value=ctx['meses_corte'], step=6, format_str="%d meses", key=f"corte_{ctx['id']}")
                with c_p3: ctx['paginas_pncp'] = components.number_input(get_text("LBL_PAGINAS_PNCP"), min_value=1, max_value=5, value=ctx['paginas_pncp'], key=f"pag_{ctx['id']}")
                with c_p4: ctx['delay_pncp'] = components.selectbox(get_text("LBL_DELAY_ANTI_BOT"), options=[1, 2, 3, 5, 10], index=[1, 2, 3, 5, 10].index(ctx['delay_pncp']), format_func=lambda x: f"{x}s" + (" (Risco WAF)" if x==1 else (" (Recomendado)" if x==delay_sugerido else "")), key=f"delay_{ctx['id']}")
                
                layout.divider_main()
                
                # --- BUSCA EM MASSA ---
                is_massa_active = ctx['massa_status'] != 'idle'
                with st.expander(get_text("LBL_BUSCA_MASSA_TIT"), expanded=is_massa_active):
                    st.markdown(get_text("LBL_BUSCA_MASSA_DESC"))
                    for _, r_m in df_validos_tr.iterrows():
                        h_m = gerar_hash_item(r_m)
                        if h_m not in ctx['palavras_chave_massa']:
                            ctx['palavras_chave_massa'][h_m] = " ".join(r_m['Descrição'].split()[:3])
                        ctx['palavras_chave_massa'][h_m] = components.text_input(f"Item {r_m['Item']} ({r_m['Métrica']}) - {r_m['Descrição'][:50]}...", value=ctx['palavras_chave_massa'][h_m], key=f"kw_massa_{ctx['id']}_{h_m}", disabled=is_massa_active)
                    
                    layout.divider_main()
                    
                    if not is_massa_active:
                        if components.button_primary(get_text("BTN_BUSCAR_MASSA"), key=f"btn_massa_{ctx['id']}"):
                            ctx['massa_status'] = 'running'; ctx['massa_idx'] = 0; ctx['massa_novos'] = 0; ctx['massa_total'] = len(df_validos_tr); st.rerun()
                    else:
                        col_ctrl1, col_ctrl2 = st.columns(2)
                        with col_ctrl1:
                            if ctx['massa_status'] == 'running':
                                if components.button_secondary(get_text("BTN_PAUSAR_MASSA"), key=f"btn_pause_{ctx['id']}"): ctx['massa_status'] = 'paused'; st.rerun()
                            elif ctx['massa_status'] == 'paused':
                                if components.button_primary(get_text("BTN_RETOMAR_MASSA"), key=f"btn_resume_{ctx['id']}"): ctx['massa_status'] = 'running'; st.rerun()
                        with col_ctrl2:
                            if components.button_secondary(get_text("BTN_PARAR_MASSA"), key=f"btn_stop_{ctx['id']}"): ctx['massa_status'] = 'idle'; ctx['massa_idx'] = 0; st.rerun()
                        
                        st.progress(ctx['massa_idx'] / ctx['massa_total'] if ctx['massa_total'] > 0 else 0)
                        if ctx['massa_status'] == 'paused': st.warning(get_text("STATUS_MASSA_PAUSADO").format(atual=ctx['massa_idx']+1, total=ctx['massa_total']))
                            
                        if ctx['massa_status'] == 'running':
                            if ctx['massa_idx'] < ctx['massa_total']:
                                idx = ctx['massa_idx']
                                r_m = df_validos_tr.iloc[idx]
                                h_m = gerar_hash_item(r_m)
                                termo_m = ctx['palavras_chave_massa'][h_m]
                                banco_m = ctx['banco_precos'][h_m]
                                st.info(get_text("STATUS_MASSA_ITEM_BUSCA").format(atual=idx+1, total=ctx['massa_total'], termo=termo_m))
                                
                                engine_m = PNCPEngine()
                                editais_m, tipo_m = engine_m.buscar_editais_inteligente(termo_m, ctx['paginas_pncp'], None)
                                all_items_m = []
                                if editais_m:
                                    ext_status = st.empty()
                                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor_m:
                                        futures_m = [executor_m.submit(engine_m.minerar_itens, ed_m, termo_m) for ed_m in editais_m]
                                        for ed_idx, f_m in enumerate(concurrent.futures.as_completed(futures_m), 1):
                                            all_items_m.extend(f_m.result())
                                            ext_status.info(get_text("STATUS_MASSA_LENDO_EDITAL").format(atual=idx+1, total=ctx['massa_total'], ed_atual=ed_idx, ed_total=len(editais_m)))
                                    ext_status.empty()
                                
                                ctx['massa_novos'] += len(all_items_m)
                                banco_m["historico_buscas"] = pd.concat([banco_m["historico_buscas"], pd.DataFrame([{"Data/Hora": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"), "Termo Pesquisado": termo_m, "Novos Registros": len(all_items_m)}])], ignore_index=True)
                                if all_items_m:
                                    df_novos_m = pd.DataFrame(all_items_m)
                                    df_novos_m.insert(0, "Válido?", True)
                                    banco_m["df_pncp"] = pd.concat([banco_m["df_pncp"], df_novos_m], ignore_index=True)
                                
                                ctx['massa_idx'] += 1
                                if ctx['massa_idx'] < ctx['massa_total']:
                                    delay_segundos = int(ctx['delay_pncp'])
                                    st.warning(get_text("STATUS_MASSA_PAUSA").format(atual=idx+1, total=ctx['massa_total'], seg=delay_segundos))
                                    time.sleep(delay_segundos); st.rerun()
                                else:
                                    ctx['massa_status'] = 'idle'
                                    st.success(get_text("STATUS_MASSA_FIM").format(qtd=ctx['massa_novos']))
                                    time.sleep(3); st.rerun()
                
                layout.spacing()
                components.render_table_header(get_text("COL_LOTE"), get_text("COL_DESC"), get_text("COL_STATUS"), get_text("COL_ACOES"))

                for _, row in df_validos_tr.iterrows():
                    h_id = gerar_hash_item(row)
                    banco = ctx['banco_precos'].get(h_id)
                    if not banco: continue
                    lote_lbl = row['Lote'] if pd.notna(row['Lote']) and str(row['Lote']).strip() != "" else "Único"
                    st.markdown(components.render_item_row_start(), unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns([1, 4, 1.5, 3], gap="small")
                    c1.write(f"**{row['Item']}** ({lote_lbl})")
                    c2.markdown(f"<span>{row['Descrição']}</span>", unsafe_allow_html=True)
                    c3.markdown(components.render_status_badge(banco['estatistica_pronta'], formatar_moeda_simples(banco['media_saneada']), get_text("BADGE_PENDENTE")), unsafe_allow_html=True)
                    with c4:
                        b1, b2, b3 = st.columns(3, gap="small")
                        with b1:
                            if components.button_secondary(get_text("BTN_PNCP"), key=f"p_{ctx['id']}_{h_id}"): ctx['acao_ativa'] = ("pncp", h_id); st.rerun()
                        with b2:
                            if components.button_secondary(get_text("BTN_MANUAL"), key=f"c_{ctx['id']}_{h_id}"): ctx['acao_ativa'] = ("manual", h_id); st.rerun()
                        with b3:
                            if components.button_secondary(get_text("BTN_VALIDAR"), key=f"v_{ctx['id']}_{h_id}"): ctx['acao_ativa'] = ("validar", h_id); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                acao, active_hash = ctx['acao_ativa']
                if acao and active_hash:
                    df_matches = df_validos_tr[df_validos_tr.apply(gerar_hash_item, axis=1) == active_hash]
                    row_ativa = df_matches.iloc[0]
                    banco_ativo = ctx['banco_precos'][active_hash]
                    layout.divider_main()
                    layout.title_group(row_ativa['Descrição'])
                    
                    if acao == "pncp":
                        with st.form(f"form_pncp_{ctx['id']}_{active_hash}"):
                            termo = components.text_input("Busca:", value=" ".join(row_ativa['Descrição'].split()[:3]), key=f"ti_{ctx['id']}_{active_hash}")
                            if components.form_submit_button(get_text("BTN_BUSCAR_PNCP")):
                                engine = PNCPEngine()
                                status = st.status(get_text("STATUS_BUSCA_INICIAL"), expanded=True)
                                editais, tipo = engine.buscar_editais_inteligente(termo, ctx['paginas_pncp'], status)
                                all_items = []
                                if editais:
                                    total_ed = len(editais)
                                    status.update(label=get_text("STATUS_EXTRAINDO").format(tipo=tipo), state="running")
                                    progress_bar = st.progress(0)
                                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                                        futures = [executor.submit(engine.minerar_itens, ed, termo) for ed in editais]
                                        for i, f in enumerate(concurrent.futures.as_completed(futures), 1):
                                            all_items.extend(f.result())
                                            progress_bar.progress(i / total_ed)
                                    progress_bar.empty()
                                    
                                qtd = len(all_items)
                                banco_ativo["historico_buscas"] = pd.concat([banco_ativo["historico_buscas"], pd.DataFrame([{"Data/Hora": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"), "Termo Pesquisado": termo, "Novos Registros": qtd}])], ignore_index=True)
                                if all_items:
                                    df_novos = pd.DataFrame(all_items)
                                    df_novos.insert(0, "Válido?", True)
                                    banco_ativo["df_pncp"] = pd.concat([banco_ativo["df_pncp"], df_novos], ignore_index=True)
                                    status.update(label=get_text("STATUS_CONCLUIDO").format(qtd=qtd), state="complete")
                                else:
                                    status.update(label=get_text("MSG_ERRO_NADA"), state="error")
                        components.data_editor(banco_ativo["historico_buscas"], column_config={"Termo Pesquisado": st.column_config.TextColumn("Termo Pesquisado", width="large")}, key=f"hist_{ctx['id']}_{active_hash}")

                    elif acao == "manual":
                        with st.form(f"form_man_{ctx['id']}_{active_hash}"):
                            layout.title_section(get_text("LBL_NOVO_REGISTRO"))
                            c1, c2, c3 = st.columns(3)
                            with c1: m_emp = components.text_input("Empresa", value="", key=f"emp_{ctx['id']}_{active_hash}")
                            with c2: m_preco = components.number_input("Preço", min_value=0.0, key=f"preco_{ctx['id']}_{active_hash}")
                            with c3: m_sit = components.selectbox("Situação:", opcoes_situacao, key=f"sit_{ctx['id']}_{active_hash}")
                            if components.form_submit_button(get_text("BTN_SALVAR_REGISTRO")):
                                log = {"Data do Contato": datetime.now(fuso_br).strftime("%d/%m/%Y"), "Horário": datetime.now(fuso_br).strftime("%H:%M"), "Empresa": m_emp, "Situação": m_sit, "Preço": m_preco, "Valor Unitário": formatar_moeda_ordenavel(m_preco), "Link da fonte": "", "Descrição da fonte": ""}
                                banco_ativo["df_manual_rastreio"] = pd.concat([banco_ativo["df_manual_rastreio"], pd.DataFrame([log])], ignore_index=True)
                                st.rerun()
                        components.data_editor(banco_ativo["df_manual_rastreio"], column_config={"Link da fonte": st.column_config.LinkColumn("Link")}, key=f"man_{ctx['id']}_{active_hash}")

                    elif acao == "validar":
                        df_pncp_atual = banco_ativo["df_pncp"].copy()
                        if not df_pncp_atual.empty:
                            limite_data = (datetime.now() - relativedelta(months=ctx['meses_corte']))
                            df_pncp_atual['Válido?'] = pd.to_datetime(df_pncp_atual['Data'], format="%d/%m/%Y", errors='coerce').apply(lambda d: True if pd.isna(d) else d >= limite_data)
                        
                        df_man_valido = pd.DataFrame()
                        if not banco_ativo["df_manual_rastreio"].empty:
                            df_man_valido = banco_ativo["df_manual_rastreio"].copy()
                            df_man_valido["Origem"] = "Manual"; df_man_valido["Item"] = row_ativa['Descrição']; df_man_valido["Qtd"] = 1; df_man_valido["Tipo"] = "Manual"; df_man_valido["Válido?"] = True
                            df_man_valido = df_man_valido.rename(columns={"Data do Contato": "Data", "Empresa": "Empresa/Órgão"})[[c for c in cols_pncp if c in df_man_valido.columns]]
                        
                        with st.form(f"form_val_{ctx['id']}_{active_hash}"):
                            col_config_val = {"Empresa/Órgão": st.column_config.TextColumn("Empresa/Órgão", disabled=True), "Origem": st.column_config.LinkColumn("Origem", disabled=True), "Item": st.column_config.TextColumn("Item", disabled=True), "Preço": st.column_config.NumberColumn("Preço", format="R$ %.2f", disabled=True)}
                            pncp_res = components.data_editor(df_pncp_atual, column_config=col_config_val, key=f"val_pncp_ed_{ctx['id']}_{active_hash}") if not df_pncp_atual.empty else pd.DataFrame()
                            man_res = components.data_editor(df_man_valido, column_config=col_config_val, key=f"val_man_ed_{ctx['id']}_{active_hash}") if not df_man_valido.empty else pd.DataFrame()
                            
                            if components.form_submit_button(get_text("BTN_CALCULAR_MEDIANA")):
                                df_merge = pd.concat([pncp_res, man_res], ignore_index=True)
                                df_v, df_o, m_geral, _, _ = processar_precos_regra(df_merge[df_merge["Válido?"] == True], ctx['regra_calculo'])
                                banco_ativo["df_validos"] = ordenar_validos(df_v); banco_ativo["df_outliers"] = ordenar_outliers(df_o); banco_ativo["media_saneada"] = df_v['Preço'].mean() if not df_v.empty else 0; banco_ativo["mediana"] = m_geral; banco_ativo["amostras"] = len(df_v); banco_ativo["estatistica_pronta"] = True
                                ctx['acao_ativa'] = (None, None); st.rerun()

                        if banco_ativo["estatistica_pronta"]:
                            layout.spacing()
                            maior_v = banco_ativo["df_validos"]['Preço'].max() if not banco_ativo["df_validos"].empty else 0
                            l1_c1, l1_c2, l1_c3 = st.columns(3)
                            l1_c1.markdown(components.render_metric_card(get_text('LBL_PRECO_FINAL'), formatar_moeda_simples(banco_ativo['media_saneada'])), unsafe_allow_html=True)
                            l1_c2.markdown(components.render_metric_card(get_text('LBL_AMOSTRAS'), banco_ativo['amostras']), unsafe_allow_html=True)
                            l1_c3.markdown(components.render_metric_card(get_text('LBL_MAIOR_VALOR'), formatar_moeda_simples(maior_v)), unsafe_allow_html=True)

        layout.divider_sub()

        # --- SUBGRUPO 3: RELATÓRIO ---
        on_relatorio = components.toggle(f"{get_text('GRP_RELATORIO')}", value=True, key=f"tg_rel_{ctx['id']}")
        if on_relatorio:
            if ctx['tr_itens_salvos']:
                df_validos_tr = ctx['df_tr'].dropna(subset=["Item", "Descrição"])
                lotes_dict = {}
                valor_total_global = 0.0
                for _, row in df_validos_tr.iterrows():
                    l_key = row["Lote"] if pd.notna(row["Lote"]) and str(row["Lote"]).strip() else "Único"
                    if l_key not in lotes_dict: lotes_dict[l_key] = []
                    banco = ctx['banco_precos'].get(gerar_hash_item(row))
                    if banco:
                        med = banco['media_saneada']
                        q = float(row.get("Quantidade", 1))
                        valor_total_global += (med * q)
                        lotes_dict[l_key].append({"Item": row["Item"], "Descrição": row["Descrição"], "Qtd": row["Quantidade"], "Unid.": row["Métrica"], "Preço Numérico": med})
                
                components.render_total_global(get_text('VALOR_TOTAL_GLOBAL'), formatar_moeda_simples(valor_total_global))

                if components.button_primary(get_text("BTN_GERAR_PDF"), key=f"pdf_g_{ctx['id']}"):
                    pdf_bytes = gerar_pdf_oficial(df_validos_tr, lotes_dict, valor_total_global, ctx['objeto_contratacao'], ctx['regra_calculo'], datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M'), ctx['banco_precos'])
                    st.download_button(get_text("BTN_SALVAR_PDF"), data=pdf_bytes, file_name=f"Analise_Mercado_{ctx['titulo'].replace(' ', '_')}.pdf", mime="application/pdf", key=f"pdf_d_{ctx['id']}")

    layout.spacing()

layout.divider_main()
if components.button_primary(get_text("BTN_NOVA_CONTRATACAO"), key="btn_new_contract"):
    proximo_id = len(st.session_state['lista_contratacoes']) + 1
    st.session_state['lista_contratacoes'].append(
        {
            "id": proximo_id,
            "titulo": f"Contratação {proximo_id}",
            "pca": "",
            "demanda": "",
            "tr_objeto_salvo": False,
            "tr_itens_salvos": False,
            "objeto_contratacao": "",
            "df_tr": pd.DataFrame(columns=["Lote", "Item", "Descrição", "Métrica", "Tipo", "Quantidade"]),
            "banco_precos": {},
            "acao_ativa": (None, None),
            "regra_calculo": "Preços válidos - Mediana ±25% e Média",
            "meses_corte": 24,
            "paginas_pncp": 3,
            "delay_pncp": None,
            "palavras_chave_massa": {},
            "massa_status": "idle",
            "massa_idx": 0,
            "massa_total": 0,
            "massa_novos": 0
        }
    )
    st.rerun()