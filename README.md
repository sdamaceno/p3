# Sistema de Planejamento e Cotações (Fase Interna)

**Órgão:** Tribunal de Justiça do Estado de Goiás (TJGO)  
**Coordenadoria:** Contratos e Aquisições de TIC (CCA-006)  
**Versão Atual:** 8.0 (Multi-Contratação, Busca em Massa Assíncrona e Smart Paste)

---

## 📌 1. Visão Geral do Projeto
Aplicação desenvolvida para automatizar a Fase Interna de licitações de TIC. O sistema consolida o Termo de Referência (Estrutura da Demanda), realiza a Pesquisa de Mercado de forma híbrida (PNCP + Cotações Manuais Rastreáveis), aplica saneamento estatístico (Mediana ±25%) e gera o Relatório Conclusivo de Análise de Mercado em PDF estritamente formatado nos padrões do Tribunal, incluindo anexo de Trilha de Auditoria pública. 

O design utiliza um layout compacto, flat e fluido, focado na extrema produtividade do comprador, permitindo a gestão simultânea de múltiplas contratações em uma única tela por meio de uma árvore de estados dinâmica.

## 🚀 2. Instalação e Configuração

Este projeto usa `xhtml2pdf`, que no Linux pode exigir dependências de sistema adicionais.

Para preparar o ambiente em **Debian/Ubuntu**:

```bash
sudo apt-get update
sudo apt-get install -y libcairo2-dev pkg-config python3-dev
```

Em seguida, instale as dependências do Python:

```bash
# Se estiver usando um ambiente virtual, ative-o antes de instalar:
# source venv/bin/activate
python -m pip install -r requirements.txt
```

Para rodar a aplicação padrão:

```bash
streamlit run app.py
```

Em atualizações, pode ser necessário alguns comandos (principalmente se estiver no ambiente do VS Code):

Vá no terminal do VS Code onde o Streamlit está rodando, pressione **Ctrl + C** para parar a aplicação. Depois, inicie novamente com:

```bash
streamlit run app.py
```

Verifique também a visibilidade da porta da aplicação.

No painel inferior do VS Code, vá na aba "Ports" (Portas), encontre a porta **8501**, clique com o botão direito na coluna "Visibility" (Visibilidade) e mude de "Private" (Privada) para "Public" (Pública).

Atualize a página e o sistema voltará a aparecer instantaneamente.

Pode ser necessário também desativar a Proteção CORS do Streamlit no Terminal.

Se o GitHub continuar bloqueando por causa dos cabeçalhos de segurança que o Streamlit gera, podemos forçar o Streamlit a aceitar o tráfego do proxy do Codespaces.

Derrube a aplicação no terminal (pressionando Ctrl + C) e rode novamente usando este comando com as flags de liberação:

```bash
streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false
```

**Tudo irá funcionar. Porém, depende**.

## 🛠️ 3. Stack Tecnológica e Infraestrutura
* **Framework Web:** Streamlit (base web com injeção de CSS puro para controle estrito de UI/UX, ocultação de barras de rolagem nativas e layout responsivo de até 1600px).
* **Processamento de Dados:** Pandas, regex, unicodedata.
* **Multithreading & Concorrência:** `concurrent.futures` com limitação de workers para paralelismo seguro na extração de dados do PNCP.
* **Integração de APIs:** Requests (Buscas no PNCP) com `urllib.parse` para parametrização de URLs de auditoria.
* **Geração de PDF:** `xhtml2pdf` (conversão direta de HTML/CSS para PDF de forma nativa e estrita).
* **Internacionalização (i18n):** Arquivo Python centralizado (`texts.py`) atuando como dicionário global de interface e motor de conversão de tipagem local (ex: conversão de números "15.000,50" para floats do padrão norte-americano sem uso de colunas auxiliares).

## 🏗️ 4. Arquitetura de Arquivos (Padrão MVC Lógico)
A aplicação segue o princípio de responsabilidade única (SOLID), dividida nos seguintes arquivos base:
* `app.py` **(Controller)**: Roteador principal baseado em `st.session_state` (Máquinas de Estado). Controla o fluxo de dados, a arquitetura multi-contratação, buscas assíncronas e renderização condicional.
* `texts.py` **(Dictionary/i18n)**: Arquivo central de textos e formatos monetários/decimais. Nenhuma string é colocada de forma *hardcoded* nas views.
* `ui.py` **(View)**: Concentra a identidade visual (CSS injetado hackeando componentes nativos do Streamlit, como botões de upload) e funções de renderização de componentes de alto nível.
* `pncp_api.py` **(Model)**: Motor de extração semântica e comunicação com a API do Portal Nacional de Contratações Públicas.
* `estatistica.py` **(Model)**: Motor de cálculo e saneamento estatístico (Mediana, Outliers).
* `pdf_engine.py` **(View/Export)**: Renderização isolada HTML/CSS do Relatório Oficial e da Trilha de Auditoria.
* `utils.py` **(Helper)**: Funções globais de formatação, regex, hashing de identificação e parser numérico localizado.

## ⚙️ 5. Módulos e Fluxo de Uso
A estrutura operacional aboliu o uso de "abas" (tabs). O sistema agora permite criar contratações infinitas geridas em série (Contratação 1, Contratação 2...), renomeáveis em tempo real. Cada contratação possui três grupos lógicos colapsáveis (`st.expander`):

* **Grupo 1: Objeto (Estrutura da Demanda):**
  * **Colagem Inteligente (Smart Paste):** O usuário cola o Termo de Referência inteiro (prosa seguida da tabela do Excel/Word). O sistema detecta os delimitadores de tabulação (`\t`), separa o texto corrido (inserindo em "Objeto") e converte a matriz na "Tabela de Itens".
  * **Upload Otimizado:** Botão de upload redesenhado via CSS para atuar lado a lado com os comandos de salvamento, ocultando meta-instruções nativas. As áreas de input somem ao salvar, exibindo apenas a tabela final de forma limpa.

* **Grupo 2: Análise de Mercado:**
  * Painel de filtros reposicionado (Regra de cálculo, meses de corte, páginas e **Delay Anti-Bot**).
  * **Busca em Massa (Máquina de Estados):** Ferramenta autônoma que sugere palavras-chave para todos os itens da estrutura. Quando ativada, dispara um processamento iterativo, item a item. Permite feedback visual profundo, pausa (`st.session_state['massa_status'] == 'paused'`) e cancelamento em tempo real.
  * Validação manual e inserção do Art. 6º continuam operando individualmente por lote.

* **Grupo 3: Relatório Oficial:**
  * Fechamento do valor global e exportação do PDF estritamente chancelado com a identidade do órgão e métricas calculadas.

## 📊 6. Regras de Negócio
* **Saneamento Estatístico:** Extração da Mediana, definição dos limites inferior (-25%) e superior (+25%), e extração da Média Saneada final.
* **Prevenção Anti-Bot (WAF):** Limitação estrita do pool de threads para `max_workers=3` nas requisições da API. Inclusão de um tempo de delay (Pausa) calculado dinamicamente com base no volume de itens da tabela (ex: 5 segundos para tabelas densas) para evitar bloqueios do Firewall do Governo Federal (PNCP).
* **Conversão i18n na Raiz:** A coluna de "Quantidade" aceita formatos BR (ex: "15.000") inseridos via input ou upload e os converte nativamente para tipos Float durante o salvamento através do parser global em `utils.py`, sem depender de colunas fantasmas de renderização.

## 🛑 7. Regras de Ouro (System Instructions)
Qualquer desenvolvedor ou agente de IA que atue neste repositório deve obedecer estritamente às seguintes travas:

1. **Regra de Escopo (MVC):** Alterar APENAS o arquivo/módulo correspondente à nova feature. É expressamente proibido refatorar outras camadas sem solicitação.
2. **REGRA DOS DADOS REAIS:** JAMAIS EXIBA DADOS SIMULADOS!!! O sistema é uma ferramenta jurídica governamental e deve operar exclusivamente com dados reais do mercado ou da API do PNCP.
3. **Trava de Estilização do PDF:** As regras do `xhtml2pdf` em `pdf_engine.py` são críticas. É expressamente proibido o uso da tag `<pdf:nextpage />` (utilizar `page-break-before: always;`). Não quebrar as diretrizes de quebra de página (`page-break-inside`).
4. **Controle de Textos (i18n):** Nenhuma string deve ser inserida "hardcoded" na interface. Tudo deve ser mapeado no dicionário em `texts.py`.
5. **Usabilidade e Responsividade Extremas:** O layout deve usar toda a largura disponível (até 1600px de limite estético), garantindo a responsividade fluida (`use_container_width`). As tabelas **não podem gerar barras horizontais nativas** em telas ultrawide.
6. **Protocolo de Entrega do LLM:** Todo arquivo alterado em Python deve ser fornecido por completo em um único bloco de código. O uso de *snippets* (fragmentos parciais) para Python é estritamente proibido para mitigar quebras de indentação.

## 🗺️ 8. Roadmap e Evolução Tecnológica
* **Front-End:** Migração da camada de apresentação (View) para **React**, visando escalabilidade corporativa assíncrona.
* **Back-End:** A regra de negócio, a Máquina de Estados e os motores de raspagem serão migrados para uma API RESTful rodando em **FastAPI**.

## 🐛 9. Troubleshooting e Problemas Conhecidos
**Erro HTTP 401 (Unauthorized) no GitHub Codespaces:**
A porta redirecionada pelo Streamlit (8501) pode retornar um erro 401 por inatividade do túnel seguro do contêiner.
* **Solução:** No VS Code, abra o painel inferior, acesse a aba **Ports** (Portas), clique com o botão direito na coluna **Visibility** da porta `8501` e altere de *Private* para **Public**. Atualize a página do navegador.