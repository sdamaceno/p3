import io
import urllib.parse
import pandas as pd
import streamlit as st
from utils import formatar_moeda_simples, gerar_hash_item

try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None  # Define como None para que possamos interceptar o erro de forma mais amigável

def gerar_pdf_oficial(df_validos_tr, lotes_dict, valor_total_global, obj_global, regra_calculo, data_emissao, banco_precos):
    
    # Blindagem: Intercepta a falta da biblioteca antes de rodar toda a lógica
    if pisa is None:
        st.error("A biblioteca 'xhtml2pdf' não está instalada no servidor. Por favor, instale usando o comando: pip install xhtml2pdf")
        return b"" # Retorna bytes vazios para evitar quebrar o Streamlit
        
    html_pdf = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4 portrait;
                margin-top: 3.5cm; margin-bottom: 2cm; margin-left: 1.5cm; margin-right: 1.5cm;
                @frame header_frame {{ -pdf-frame-content: header_content; left: 1.5cm; right: 1.5cm; top: 1cm; height: 2.5cm; }}
                @frame footer_frame {{ -pdf-frame-content: footer_content; left: 1.5cm; right: 1.5cm; bottom: 0.5cm; height: 1cm; }}
            }}
            body {{ font-family: "Times New Roman", Times, serif; font-size: 12px; color: black; line-height: 1; margin: 0; padding: 0; }}
            p {{ margin: 0; padding: 0; text-align: justify; line-height: 1; }}
            h1, h2, h3, h4 {{ font-family: "Times New Roman", Times, serif; font-size: 12px; font-weight: bold; color: black; margin: 24px 0 0 0; padding: 0; line-height: 1; }}
            h1:first-child {{ margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; border: 0.25pt solid #666; table-layout: fixed; margin: 0; padding: 0; }}
            th, td {{ border: 0.25pt solid #666; padding: 2px; font-size: 10px; vertical-align: middle; word-wrap: break-word; line-height: 1; }}
            th {{ font-weight: bold; text-align: center; background-color: #f2f2f2; }}
            tr {{ page-break-inside: avoid; }}
            .right-txt {{ text-align: right; font-weight: bold; }}
            .center-txt {{ text-align: center; }}
        </style>
    </head>
    <body>
        <div id="header_content">
            <table>
                <tr>
                    <td rowspan="3" style="width: 35%; text-align: center; vertical-align: middle; font-family: Arial, Helvetica, sans-serif;">
                        <span style="font-size: 14px; font-weight: bold;">PODER JUDICIÁRIO</span><br>
                        <span style="font-size: 11px;">Tribunal de Justiça do Estado de Goiás</span><br>
                        <span style="font-size: 9px; color: #000000;">Coordenadoria de Contratos e Aquisições de TIC</span>
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
                    <td style="width: 25%; text-align: center; font-size: 11px; vertical-align: middle; height: 15px;"><b>Revisão:</b> 008</td>
                    <td style="width: 25%; text-align: center; font-size: 11px; vertical-align: middle;"><b>Código/Versão:</b> CCA-006</td>
                    <td style="width: 15%; text-align: center; font-size: 11px; vertical-align: middle;"><b>Página:</b> <pdf:pagenumber> / <pdf:pagecount></td>
                </tr>
            </table>
        </div>
        
        <div id="footer_content">
            <p style="text-align: right; font-size: 10px;">Documento gerado eletronicamente em {data_emissao}</p>
        </div>

        <h1 style="margin-top: 0;">OBJETO</h1>
        <p>{obj_global}</p>
        
        <h1>METODOLOGIA</h1>
        <p><b>Estatística Aplicada:</b> {regra_calculo}</p>
        
        <p class="right-txt" style="font-size:14px; margin-top: 24px;">VALOR TOTAL ESTIMADO: {formatar_moeda_simples(valor_total_global)}</p>
    """
    
    for nome_lote, itens in lotes_dict.items():
        titulo = f"LOTE {nome_lote}" if nome_lote != "Único" else "QUADRO DE ITENS"
        html_pdf += f"<h2>{titulo}</h2>"
        html_pdf += "<table repeat-header='yes'><thead><tr><th width='5%'>Item</th><th width='40%'>Descrição</th><th width='5%'>Qtd</th><th width='10%'>Unid.</th><th width='20%'>Valor Ref. Unit.</th><th width='20%'>Subtotal</th></tr></thead><tbody>"
        subt_lote = 0.0
        for it in itens:
            try: q = float(it['Qtd']) 
            except: q = 1
            subt_item_val = it['Preço Numérico'] * q
            subt_lote += subt_item_val
            html_pdf += f"<tr><td class='center-txt'>{it['Item']}</td><td>{it['Descrição']}</td><td class='center-txt'>{it['Qtd']}</td><td class='center-txt'>{it['Unid.']}</td><td class='center-txt'>{formatar_moeda_simples(it['Preço Numérico'])}</td><td class='center-txt'>{formatar_moeda_simples(subt_item_val)}</td></tr>"
        html_pdf += f"<tr><td colspan='5' class='right-txt'>Subtotal {titulo}:</td><td class='center-txt'><b>{formatar_moeda_simples(subt_lote)}</b></td></tr></tbody></table>"
    
    html_pdf += "<h1>ANEXO I - RELATÓRIO DE RASTREABILIDADE (ART. 6º)</h1>"
    for _, row in df_validos_tr.iterrows():
        h_id = gerar_hash_item(row)
        banco = banco_precos.get(h_id)
        if not banco: continue
        
        # Uso do .get() para evitar key errors caso os dataframes estejam ausentes no dict
        df_rastreio = banco.get('df_manual_rastreio', pd.DataFrame())
        
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

    html_pdf += "<h1>ANEXO II - COMPOSIÇÃO ESTATÍSTICA FINAL</h1>"
    for _, row in df_validos_tr.iterrows():
        h_id = gerar_hash_item(row)
        banco = banco_precos.get(h_id)
        if not banco: continue
        html_pdf += f"<h2>ITEM {row['Item']}: {row['Descrição']}</h2>"
        html_pdf += f"<p style='margin-bottom: 24px;'><b>Média Saneada Aplicada:</b> {formatar_moeda_simples(banco.get('media_saneada', 0))} | <b>Amostras Válidas:</b> {banco.get('amostras', 0)}</p>"
        
        df_v = banco.get('df_validos', pd.DataFrame())
        if not df_v.empty:
            html_pdf += "<h2>Preços Válidos Adotados no Cálculo</h2>"
            html_pdf += "<table repeat-header='yes'><thead><tr><th width='12%'>Data</th><th width='30%'>Empresa/Órgão</th><th width='18%'>Valor Unit.</th><th width='40%'>Origem (Fundamento)</th></tr></thead><tbody>"
            for _, r in df_v.iterrows():
                orig_str = str(r['Origem'])[:150] + "..." if len(str(r['Origem'])) > 150 else str(r['Origem'])
                html_pdf += f"<tr><td class='center-txt'>{r['Data']}</td><td>{r['Empresa/Órgão']}</td><td class='center-txt'>{formatar_moeda_simples(r['Preço'])}</td><td>{orig_str}</td></tr>"
            html_pdf += "</tbody></table>"
            
        df_o = banco.get('df_outliers', pd.DataFrame())
        if not df_o.empty:
            html_pdf += "<h2>Preços Descartados (Outliers ou Desmarcados Manualmente)</h2>"
            html_pdf += "<table repeat-header='yes'><thead><tr><th width='12%'>Data</th><th width='30%'>Empresa/Órgão</th><th width='18%'>Valor Unit.</th><th width='40%'>Origem (Fundamento)</th></tr></thead><tbody>"
            for _, r in df_o.iterrows():
                orig_str = str(r['Origem'])[:150] + "..." if len(str(r['Origem'])) > 150 else str(r['Origem'])
                html_pdf += f"<tr><td class='center-txt'>{r['Data']}</td><td>{r['Empresa/Órgão']}</td><td class='center-txt'>{formatar_moeda_simples(r['Preço'])}</td><td>{orig_str}</td></tr>"
            html_pdf += "</tbody></table>"
    
    # ANEXO III - TRILHA DE AUDITORIA DO PNCP
    html_pdf += "<div style='page-break-before: always;'></div>"
    html_pdf += "<h1>ANEXO III - TRILHA DE AUDITORIA DE BUSCAS NO PNCP</h1>"
    html_pdf += "<p style='margin-bottom: 24px;'>Este anexo documenta todas as tentativas de busca realizadas no Portal Nacional de Contratações Públicas (PNCP), assegurando a rastreabilidade e a transparência em conformidade com as diretrizes de pesquisa de preços.</p>"

    for _, row in df_validos_tr.iterrows():
        h_id = gerar_hash_item(row)
        banco = banco_precos.get(h_id)
        if not banco: continue
        
        df_hist = banco.get('historico_buscas', pd.DataFrame())
        if not df_hist.empty:
            html_pdf += f"<h2>ITEM {row['Item']}: {row['Descrição']}</h2>"
            html_pdf += "<table repeat-header='yes'><thead><tr><th width='15%'>Data/Hora</th><th width='40%'>Termo Pesquisado</th><th width='15%'>Resultados</th><th width='30%'>URL Pública (Auditoria)</th></tr></thead><tbody>"
            
            for _, r_hist in df_hist.iterrows():
                termo = str(r_hist.get('Termo Pesquisado', ''))
                # Codifica a string para URL (substituindo espaços por %20 etc)
                termo_encoded = urllib.parse.quote(termo)
                url_auditoria = f"https://pncp.gov.br/app/editais?q={termo_encoded}"
                
                link_html = f"<a href='{url_auditoria}' style='color: blue; text-decoration: underline;'>Acessar Site do PNCP</a>"
                
                html_pdf += f"<tr><td class='center-txt'>{r_hist.get('Data/Hora', '')}</td><td>{termo}</td><td class='center-txt'>{r_hist.get('Novos Registros', 0)}</td><td class='center-txt'>{link_html}</td></tr>"
            
            html_pdf += "</tbody></table>"

    html_pdf += "</body></html>"
    
    result_pdf = io.BytesIO()
    pisa.CreatePDF(src=html_pdf, dest=result_pdf, encoding='utf-8')
    return result_pdf.getvalue()