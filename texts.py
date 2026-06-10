# texts.py
LANG = "pt-br"

FORMATOS = {
    "pt-br": { "DECIMAL_SEP": ",", "THOUSANDS_SEP": "." },
    "en-us": { "DECIMAL_SEP": ".", "THOUSANDS_SEP": "," }
}

TEXTOS = {
    "pt-br": {
        "NOME_SISTEMA": "SAM - Solução de Análise de Mercado",
        
        "GRP_OBJETO": "Objeto",
        "GRP_ANALISE": "Análise de Mercado",
        "GRP_RELATORIO": "Relatório",
        
        "LBL_COL_ESQ": "Descrição resumida do objeto:",
        "LBL_COL_DIR": "Estrutura de Lotes e Itens:",
        "LBL_DICA_COLA": "Cole aqui a descrição resumida do objeto isolada ou unificada com a tabela de lotes/itens...",
        "LBL_UPLOAD": "Enviar arquivo",
        "BTN_SALVAR_OBJ": "Salvar Objeto",
        "BTN_EDITAR_OBJ": "Editar Objeto",
        "MSG_SUCESSO_IMPORT": "Dados importados com sucesso!",
        
        "LBL_BUSCA_MASSA_TIT": "Configuração de Busca em Massa no PNCP",
        "LBL_BUSCA_MASSA_DESC": "Palavras-chave sugeridas pelo robô (edite se necessário antes de disparar):",
        "BTN_BUSCAR_MASSA": "Pesquisar Todos os Itens em Lote",
        "BTN_PAUSAR_MASSA": "Pausar Busca",
        "BTN_RETOMAR_MASSA": "Retomar Busca",
        "BTN_PARAR_MASSA": "Parar (Cancelar)",
        "STATUS_MASSA_INICIO": "Iniciando varredura geral em lote (Concorrência Limitada)...",
        "STATUS_MASSA_ITEM_BUSCA": "Item {atual}/{total}: Buscando editais para '{termo}'...",
        "STATUS_MASSA_LENDO_EDITAL": "Item {atual}/{total}: Extraindo dados (Edital {ed_atual} de {ed_total})...",
        "STATUS_MASSA_PAUSA": "Item {atual}/{total}: Pausa Anti-Bot de {seg}s para evitar bloqueio...",
        "STATUS_MASSA_PAUSADO": "Busca pausada (Item {atual} de {total}). Clique em 'Retomar' para continuar.",
        "STATUS_MASSA_FIM": "Varredura em lote concluída de forma segura! {qtd} cotações integradas.",
        
        "TITULO_PAINEL": "Painel de Ações por Item",
        "COL_LOTE": "Lote",
        "COL_DESC": "Descrição",
        "COL_STATUS": "Status",
        "COL_ACOES": "Ações",
        "BADGE_PENDENTE": "Pendente",
        "BTN_PNCP": "PNCP",
        "BTN_MANUAL": "Cadastrar",
        "BTN_VALIDAR": "Validar",
        "BTN_BUSCAR_PNCP": "Buscar no PNCP",
        "LBL_NOVO_REGISTRO": "Novo Registro",
        "BTN_SALVAR_REGISTRO": "Salvar",
        "BTN_CALCULAR_MEDIANA": "Calcular Mediana/Média",
        
        "STATUS_BUSCA_INICIAL": "Iniciando varredura no PNCP...",
        "STATUS_TENTATIVA_1": "Tentativa 1: Buscando editais com termos exatos...",
        "STATUS_TENTATIVA_2": "Tentativa 2: Refinando termos (busca flexível)...",
        "STATUS_TENTATIVA_3": "Tentativa 3: Expandindo tipos de documentos...",
        "STATUS_EXTRAINDO": "Editais localizados (Modo: {tipo}). Extraindo itens...",
        "STATUS_PROCESSANDO_EDITAL": "Extraindo itens... (Edital {atual} de {total})",
        "STATUS_CONCLUIDO": "Busca concluída! {qtd} cotações encontradas.",
        "MSG_ERRO_EDITAIS": "Editais encontrados, mas sem os itens exatos.",
        "MSG_ERRO_NADA": "Nenhum resultado retornado pelo PNCP. Tentativa gravada.",
        "LBL_DICA_TERMOS": "Dica: Tente pesquisar com menos palavras.",
        
        "TITULO_PARAMETROS": "Parâmetros Estatísticos e de Busca",
        "LBL_REGRA_CALCULO": "Parâmetro de Cálculo",
        "LBL_MESES_CORTE": "Período de PNCP/Atas",
        "LBL_PAGINAS_PNCP": "Páginas (PNCP)",
        "LBL_DELAY_ANTI_BOT": "Intervalo Anti-Bot (Segundos)",
        "VALOR_TOTAL_GLOBAL": "VALOR TOTAL ESTIMADO DA CONTRATAÇÃO",
        "BTN_GERAR_PDF": "Baixar PDF Oficial",
        "BTN_SALVAR_PDF": "Salvar PDF",
        
        "BTN_NOVA_CONTRATACAO": "Criar Nova Contratação Sequencial",
        "LBL_RENOMEAR_CONTRATACAO": "Nome da Contratação:",
        "LBL_PCA": "PCA:",
        "PH_PCA": "PCA ###",
        "LBL_DEMANDA": "Demanda:",
        
        "LBL_PRECO_FINAL": "Preço Final Adotado",
        "LBL_AMOSTRAS": "Amostras Utilizadas",
        "LBL_MAIOR_VALOR": "Maior Valor Aceito",
    }
}

def get_text(chave): return TEXTOS[LANG].get(chave, f"[{chave}]")
def get_format(chave): return FORMATOS[LANG].get(chave)