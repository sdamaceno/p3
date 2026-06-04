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
import ui
from texts import get_text

st.set_page_config(page_title=get_text("NOME_SISTEMA"), layout="wide", initial_sidebar_state="collapsed")
fuso_br = timezone(timedelta(hours=-3))
ui.carregar_estilos()

# Definições estritas de schema de dados
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

# --- ARQUITETURA MULTI-CONTRATAÇÃO EM MEMÓRIA ---
if 'lista_contratacoes' not in st.session_state:
    st.session_state['lista_contratacoes'] = [
        {
            "id": 1,
            "titulo": "Contratação 1",
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
            # Controle de Estado da Busca em Massa
            "massa_status": "idle", # idle, running, paused
            "massa_idx": 0,
            "massa_total": 0,
            "massa_novos": 0
        }
    ]

# Proteção para garantir que instâncias de sessão anteriores ganhem os novos atributos
for ctx in st.session_state['lista_contratacoes']:
    if 'massa_status' not in ctx:
        ctx['massa_status'] = 'idle'
        ctx['massa_idx'] = 0
        ctx['massa_total'] = 0
        ctx['massa_novos'] = 0

ui.renderizar_cabecalho()

for idx_c, ctx in enumerate(st.session_state['lista_contratacoes']):
    
    st.markdown(f"<div class='tit-contratacao'><h3>📜 {ctx['titulo']}</h3></div>", unsafe_allow_html=True)
    
    with st.expander(f"Gerenciar: {ctx['titulo']}", expanded=(idx_c == len(st.session_state['lista_contratacoes']) - 1)):
        
        ctx['titulo'] = st.text_input(get_text("LBL_RENOMEAR_CONTRATACAO"), value=ctx['titulo'], key=f"ren_title_{ctx['id']}")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- GRUPO 1: OBJETO ---
        st.markdown(f"<div class='tit-grupo'><h4>• {get_text('GRP_OBJETO')}</h4></div>", unsafe_allow_html=True)
        with st.container():
            col_obj, col_itens = st.columns([1, 2], gap="large")
            
            if not ctx['tr_objeto_salvo']:
                with col_obj:
                    st.markdown(f"<div class='section-title'>{get_text('LBL_COL_ESQ')}</div>", unsafe_allow_html=True)
                    txt_input = st.text_area(f"obj_area_{ctx['id']}", value=ctx['objeto_contratacao'], height=250, label_visibility="collapsed", placeholder=get_text("LBL_DICA_COLA"))
                
                with col_itens:
                    st.markdown(f"<div class='section-title'>{get_text('LBL_COL_DIR')}</div>", unsafe_allow_html=True)
                    df_tr_editado = st.data_editor(
                        ctx['df_tr'], 
                        num_rows="dynamic", 
                        use_container_width=True,
                        column_config=CONFIG_COLUNAS_TABELA,
                        key=f"editor_tr_{ctx['id']}"
                    )
                
                with col_obj:
                    c_btn1, c_btn2 = st.columns([1, 1], gap="medium")
                    with c_btn1:
                        if st.button(get_text("BTN_SALVAR_OBJ"), type="primary", key=f"save_obj_btn_{ctx['id']}"):
                            if txt_input.strip():
                                linhas = txt_input.strip().split('\n')
                                idx_tabela = -1
                                for i, l in enumerate(linhas):
                                    if '\t' in l:
                                        idx_tabela = i
                                        break
                                
                                objeto_str = txt_input.strip()
                                tabela_str = ""
                                
                                if idx_tabela > 0:
                                    objeto_str = "\n".join(linhas[:idx_tabela]).strip()
                                    tabela_str = "\n".join(linhas[idx_tabela:]).strip()
                                
                                ctx['objeto_contratacao'] = objeto_str
                                
                                if tabela_str:
                                    df_raw = pd.read_csv(io.StringIO(tabela_str), sep='\t', header=None, dtype=str)
                                    df_raw = df_raw.fillna("").apply(lambda x: x.str.strip().str.replace('"', ''))
                                    colunas_oficiais = ["Lote", "Item", "Descrição", "Métrica", "Tipo", "Quantidade"]
                                    mapa_chaves = {"lote": "Lote", "item": "Item", "descri": "Descrição", "métric": "Métrica", "metric": "Métrica", "tipo": "Tipo", "quant": "Quantidade", "qtd": "Quantidade"}
                                    primeira_linha = df_raw.iloc[0].str.lower()
                                    df_final = pd.DataFrame(columns=colunas_oficiais)
                                    
                                    if any(any(chave in celula for chave in mapa_chaves.keys()) for celula in primeira_linha):
                                        indice_mapeado = {mapa_chaves[k]: idx for idx, cel in enumerate(primeira_linha) for k in mapa_chaves if k in cel}
                                        dados_uteis = df_raw.iloc[1:].reset_index(drop=True)
                                        for col in colunas_oficiais: df_final[col] = dados_uteis.iloc[:, indice_mapeado[col]] if col in indice_mapeado else ""
                                    else:
                                        for i, col in enumerate(colunas_oficiais): df_final[col] = df_raw.iloc[:, i] if i < len(df_raw.columns) else ""
                                    
                                    df_final['Lote'] = df_final['Lote'].replace(r'^\s*$', pd.NA, regex=True).ffill()
                                    df_final['Quantidade'] = df_final['Quantidade'].apply(parse_numero_localizado)
                                    df_validos = df_final.dropna(subset=["Item", "Descrição"]).copy()
                                else:
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
                        up_file_tr = st.file_uploader("Upload", type=["xlsx", "csv"], key=f"up_{ctx['id']}", label_visibility="collapsed")
                        if up_file_tr:
                            df_up = pd.read_csv(up_file_tr, delimiter=';') if up_file_tr.name.endswith('.csv') else pd.read_excel(up_file_tr)
                            if len(df_up.columns) >= 6:
                                df_up = df_up.iloc[:, :6]
                                df_up.columns = ["Lote", "Item", "Descrição", "Métrica", "Tipo", "Quantidade"]
                                df_up['Lote'] = df_up['Lote'].replace(r'^\s*$', pd.NA, regex=True).ffill()
                                df_up['Quantidade'] = df_up['Quantidade'].apply(parse_numero_localizado)
                                ctx['df_tr'] = df_up
                                st.success(get_text("MSG_SUCESSO_IMPORT"))
                                time.sleep(0.5)
                                st.rerun()
            else:
                with col_obj:
                    st.markdown(f"<div class='section-title'>{get_text('LBL_COL_ESQ')}</div>", unsafe_allow_html=True)
                    st.info(ctx['objeto_contratacao'])
                    if st.button(get_text("BTN_EDITAR_OBJ"), key=f"edt_obj_btn_{ctx['id']}"):
                        ctx['tr_objeto_salvo'] = False
                        ctx['tr_itens_salvos'] = False
                        st.rerun()
                with col_itens:
                    st.markdown(f"<div class='section-title'>{get_text('LBL_COL_DIR')}</div>", unsafe_allow_html=True)
                    st.dataframe(ctx['df_tr'].dropna(subset=["Item", "Descrição"]), hide_index=True, use_container_width=True, column_config=CONFIG_COLUNAS_TABELA)

        st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)

        # --- GRUPO 2: ANÁLISE DE MERCADO (COM FILTROS INTERNOS E ANTI-BOT) ---
        st.markdown(f"<div class='tit-grupo'><h4>• {get_text('GRP_ANALISE')}</h4></div>", unsafe_allow_html=True)
        with st.container():
            if ctx['tr_itens_salvos']:
                df_validos_tr = ctx['df_tr'].dropna(subset=["Item", "Descrição"])
                qtd_itens = len(df_validos_tr)
                
                # Inteligência sugerida anti-bloqueio
                delay_sugerido = 1 if qtd_itens <= 3 else (3 if qtd_itens <= 10 else 5)
                if ctx['delay_pncp'] is None:
                    ctx['delay_pncp'] = delay_sugerido
                
                st.markdown(f"##### {get_text('TITULO_PARAMETROS')}")
                c_p1, c_p2, c_p3, c_p4 = st.columns(4)
                ctx['regra_calculo'] = c_p1.selectbox(get_text("LBL_REGRA_CALCULO"), ["Preços válidos - Mediana ±25% e Média"], key=f"regra_calc_{ctx['id']}")
                ctx['meses_corte'] = c_p2.slider(get_text("LBL_MESES_CORTE"), min_value=12, max_value=60, step=6, format="%d meses", key=f"corte_{ctx['id']}", value=ctx['meses_corte'])
                ctx['paginas_pncp'] = c_p3.number_input(get_text("LBL_PAGINAS_PNCP"), min_value=1, max_value=5, key=f"pag_{ctx['id']}", value=ctx['paginas_pncp'])
                
                ctx['delay_pncp'] = c_p4.selectbox(
                    get_text("LBL_DELAY_ANTI_BOT"), 
                    options=[1, 2, 3, 5, 10], 
                    index=[1, 2, 3, 5, 10].index(ctx['delay_pncp']),
                    format_func=lambda x: f"{x}s" + (" (Risco WAF)" if x==1 else (" (Recomendado)" if x==delay_sugerido else "")),
                    key=f"delay_{ctx['id']}"
                )
                
                st.markdown("---")
                
                # --- ⚡ MECANISMO DE BUSCA EM MASSA (LOTE COM MÁQUINA DE ESTADOS) ⚡ ---
                is_massa_active = ctx['massa_status'] != 'idle'
                with st.expander(get_text("LBL_BUSCA_MASSA_TIT"), expanded=is_massa_active):
                    st.markdown(get_text("LBL_BUSCA_MASSA_DESC"))
                    
                    for _, r_m in df_validos_tr.iterrows():
                        h_m = gerar_hash_item(r_m)
                        if h_m not in ctx['palavras_chave_massa']:
                            ctx['palavras_chave_massa'][h_m] = " ".join(r_m['Descrição'].split()[:3])
                        
                        ctx['palavras_chave_massa'][h_m] = st.text_input(
                            f"Item {r_m['Item']} ({r_m['Métrica']}) - {r_m['Descrição'][:50]}...", 
                            value=ctx['palavras_chave_massa'][h_m], 
                            key=f"kw_massa_{ctx['id']}_{h_m}",
                            disabled=is_massa_active
                        )
                    
                    st.markdown("---")
                    
                    # Roteador de Botões e Exibição de Status
                    if not is_massa_active:
                        if st.button(get_text("BTN_BUSCAR_MASSA"), key=f"btn_massa_{ctx['id']}", type="primary"):
                            ctx['massa_status'] = 'running'
                            ctx['massa_idx'] = 0
                            ctx['massa_novos'] = 0
                            ctx['massa_total'] = len(df_validos_tr)
                            st.rerun()
                    else:
                        col_ctrl1, col_ctrl2 = st.columns(2)
                        
                        # Renderiza os controles operacionais
                        if ctx['massa_status'] == 'running':
                            if col_ctrl1.button(get_text("BTN_PAUSAR_MASSA"), key=f"btn_pause_{ctx['id']}", use_container_width=True):
                                ctx['massa_status'] = 'paused'
                                st.rerun()
                        elif ctx['massa_status'] == 'paused':
                            if col_ctrl1.button(get_text("BTN_RETOMAR_MASSA"), key=f"btn_resume_{ctx['id']}", type="primary", use_container_width=True):
                                ctx['massa_status'] = 'running'
                                st.rerun()
                        
                        if col_ctrl2.button(get_text("BTN_PARAR_MASSA"), key=f"btn_stop_{ctx['id']}", use_container_width=True):
                            ctx['massa_status'] = 'idle'
                            ctx['massa_idx'] = 0
                            st.rerun()
                        
                        # Exibe o progresso
                        prog = ctx['massa_idx'] / ctx['massa_total'] if ctx['massa_total'] > 0 else 0
                        st.progress(prog)
                        
                        if ctx['massa_status'] == 'paused':
                            st.warning(get_text("STATUS_MASSA_PAUSADO").format(atual=ctx['massa_idx']+1, total=ctx['massa_total']))
                            
                        # EXECUÇÃO DO LAÇO (Um item por rerun)
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
                                
                                qtd_m = len(all_items_m)
                                ctx['massa_novos'] += qtd_m
                                
                                banco_m["historico_buscas"] = pd.concat([banco_m["historico_buscas"], pd.DataFrame([{"Data/Hora": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"), "Termo Pesquisado": termo_m, "Novos Registros": qtd_m}])], ignore_index=True)
                                
                                if all_items_m:
                                    df_novos_m = pd.DataFrame(all_items_m)
                                    df_novos_m.insert(0, "Válido?", True)
                                    banco_m["df_pncp"] = pd.concat([banco_m["df_pncp"], df_novos_m], ignore_index=True)
                                
                                ctx['massa_idx'] += 1
                                
                                # Pausa protetiva e engatilha o próximo loop com rerun
                                if ctx['massa_idx'] < ctx['massa_total']:
                                    delay_segundos = int(ctx['delay_pncp'])
                                    st.warning(get_text("STATUS_MASSA_PAUSA").format(atual=idx+1, total=ctx['massa_total'], seg=delay_segundos))
                                    time.sleep(delay_segundos)
                                    st.rerun()
                                else:
                                    ctx['massa_status'] = 'idle'
                                    st.success(get_text("STATUS_MASSA_FIM").format(qtd=ctx['massa_novos']))
                                    time.sleep(3)
                                    st.rerun()
                
                st.markdown("<br>", unsafe_allow_html=True)
                ui.renderizar_cabecalho_lista_itens()

                # Listagem operacional individualizada
                for _, row in df_validos_tr.iterrows():
                    h_id = gerar_hash_item(row)
                    banco = ctx['banco_precos'].get(h_id)
                    if not banco: continue
                    
                    lote_lbl = row['Lote'] if pd.notna(row['Lote']) and str(row['Lote']).strip() != "" else "Único"
                    
                    st.markdown(ui.gerar_html_linha_item(), unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns([1, 4, 1.5, 3.5])
                    c1.write(f"**{row['Item']}** ({lote_lbl})")
                    c2.write(row['Descrição'])
                    c3.markdown(ui.render_status_badge(banco['estatistica_pronta'], formatar_moeda_simples(banco['media_saneada'])), unsafe_allow_html=True)
                    
                    with c4:
                        b1, b2, b3 = st.columns(3)
                        if b1.button(get_text("BTN_PNCP"), key=f"p_{ctx['id']}_{h_id}"): ctx['acao_ativa'] = ("pncp", h_id); st.rerun()
                        if b2.button(get_text("BTN_MANUAL"), key=f"c_{ctx['id']}_{h_id}"): ctx['acao_ativa'] = ("manual", h_id); st.rerun()
                        if b3.button(get_text("BTN_VALIDAR"), key=f"v_{ctx['id']}_{h_id}"): ctx['acao_ativa'] = ("validar", h_id); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                acao, active_hash = ctx['acao_ativa']
                if acao and active_hash:
                    df_matches = df_validos_tr[df_validos_tr.apply(gerar_hash_item, axis=1) == active_hash]
                    row_ativa = df_matches.iloc[0]
                    banco_ativo = ctx['banco_precos'][active_hash]
                    st.markdown("---")
                    st.markdown(f"#### Área de Trabalho: {row_ativa['Descrição']}")
                    
                    if acao == "pncp":
                        with st.form(f"form_pncp_{ctx['id']}_{active_hash}"):
                            termo = st.text_input("Busca:", value=" ".join(row_ativa['Descrição'].split()[:3]))
                            if st.form_submit_button(get_text("BTN_BUSCAR_PNCP")):
                                engine = PNCPEngine()
                                status = st.status(get_text("STATUS_BUSCA_INICIAL"), expanded=True)
                                editais, tipo = engine.buscar_editais_inteligente(termo, ctx['paginas_pncp'], status)
                                
                                all_items = []
                                if editais:
                                    total_ed = len(editais)
                                    status.update(label=get_text("STATUS_EXTRAINDO").format(tipo=tipo), state="running")
                                    progress_text = get_text("STATUS_PROCESSANDO_EDITAL").format(atual=0, total=total_ed)
                                    progress_bar = st.progress(0, text=progress_text)
                                    
                                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                                        futures = [executor.submit(engine.minerar_itens, ed, termo) for ed in editais]
                                        for i, f in enumerate(concurrent.futures.as_completed(futures), 1):
                                            all_items.extend(f.result())
                                            progress_bar.progress(i / total_ed, text=get_text("STATUS_PROCESSANDO_EDITAL").format(atual=i, total=total_ed))
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
                        st.data_editor(banco_ativo["historico_buscas"], num_rows="dynamic", key=f"hist_{ctx['id']}_{active_hash}", use_container_width=True)

                    elif acao == "manual":
                        with st.form(f"form_man_{ctx['id']}_{active_hash}"):
                            st.markdown(get_text("LBL_NOVO_REGISTRO"))
                            c1, c2, c3 = st.columns(3)
                            m_emp = c1.text_input("Empresa")
                            m_preco = c2.number_input("Preço", min_value=0.0)
                            m_sit = c3.selectbox("Situação:", opcoes_situacao)
                            if st.form_submit_button(get_text("BTN_SALVAR_REGISTRO")):
                                log = {"Data do Contato": datetime.now(fuso_br).strftime("%d/%m/%Y"), "Horário": datetime.now(fuso_br).strftime("%H:%M"), "Empresa": m_emp, "Situação": m_sit, "Preço": m_preco, "Valor Unitário": formatar_moeda_ordenavel(m_preco), "Link da fonte": "", "Descrição da fonte": ""}
                                banco_ativo["df_manual_rastreio"] = pd.concat([banco_ativo["df_manual_rastreio"], pd.DataFrame([log])], ignore_index=True)
                                st.rerun()
                        st.data_editor(banco_ativo["df_manual_rastreio"], num_rows="dynamic", key=f"man_{ctx['id']}_{active_hash}", use_container_width=True, column_config={"Link da fonte": st.column_config.LinkColumn("Link")})

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
                            pncp_res = st.data_editor(df_pncp_atual, column_config=col_config_val, hide_index=True, use_container_width=True, key=f"val_pncp_ed_{ctx['id']}_{active_hash}") if not df_pncp_atual.empty else pd.DataFrame()
                            man_res = st.data_editor(df_man_valido, column_config=col_config_val, hide_index=True, use_container_width=True, key=f"val_man_ed_{ctx['id']}_{active_hash}") if not df_man_valido.empty else pd.DataFrame()
                            
                            if st.form_submit_button(get_text("BTN_CALCULAR_MEDIANA")):
                                df_merge = pd.concat([pncp_res, man_res], ignore_index=True)
                                df_v, df_o, m_geral, _, _ = processar_precos_regra(df_merge[df_merge["Válido?"] == True], ctx['regra_calculo'])
                                banco_ativo["df_validos"] = ordenar_validos(df_v); banco_ativo["df_outliers"] = ordenar_outliers(df_o); banco_ativo["media_saneada"] = df_v['Preço'].mean() if not df_v.empty else 0; banco_ativo["mediana"] = m_geral; banco_ativo["amostras"] = len(df_v); banco_ativo["estatistica_pronta"] = True
                                ctx['acao_ativa'] = (None, None); st.rerun()

                        if banco_ativo["estatistica_pronta"]:
                            st.markdown("<br>", unsafe_allow_html=True)
                            maior_v = banco_ativo["df_validos"]['Preço'].max() if not banco_ativo["df_validos"].empty else 0
                            ui.renderizar_metricas_estatisticas(formatar_moeda_simples(banco_ativo['media_saneada']), banco_ativo['amostras'], formatar_moeda_simples(maior_v))

        st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)

        # --- GRUPO 3: RELATÓRIO ---
        st.markdown(f"<div class='tit-grupo'><h4>• {get_text('GRP_RELATORIO')}</h4></div>", unsafe_allow_html=True)
        with st.container():
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
                
                ui.renderizar_total_global(formatar_moeda_simples(valor_total_global))

                if st.button(get_text("BTN_GERAR_PDF"), type="primary", key=f"pdf_g_{ctx['id']}"):
                    pdf_bytes = gerar_pdf_oficial(df_validos_tr, lotes_dict, valor_total_global, ctx['objeto_contratacao'], ctx['regra_calculo'], datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M'), ctx['banco_precos'])
                    st.download_button(get_text("BTN_SALVAR_PDF"), data=pdf_bytes, file_name=f"Analise_Mercado_{ctx['titulo'].replace(' ', '_')}.pdf", mime="application/pdf", key=f"pdf_d_{ctx['id']}")

    st.markdown("<br><br><br>", unsafe_allow_html=True)

# --- BOTÃO CENTRAL DE ESCALABILIDADE (NOVO OBJETO) ---
st.markdown("---")
if st.button(get_text("BTN_NOVA_CONTRATACAO"), type="primary", use_container_width=True):
    proximo_id = len(st.session_state['lista_contratacoes']) + 1
    st.session_state['lista_contratacoes'].append(
        {
            "id": proximo_id,
            "titulo": f"Contratação {proximo_id}",
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