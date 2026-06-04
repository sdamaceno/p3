import requests
from datetime import datetime
from utils import normalizar_texto, formatar_moeda_ordenavel

class PNCPEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://pncp.gov.br/app/editais",
            "Origin": "https://pncp.gov.br",
            "Connection": "close",
        })
        self.base_url_search = "https://pncp.gov.br/api/search/"
        self.base_url_api = "https://pncp.gov.br/pncp-api/v1"

    def _get(self, url, params=None, timeout=10):
        return requests.get(url, params=params, headers=self.session.headers, timeout=timeout)

    def buscar_editais_inteligente(self, termo, paginas=3, status_placeholder=None):
        from texts import get_text # Importação isolada para manter o model limpo
        base_url = "https://pncp.gov.br/api/search/"
        busca_api = termo.replace('"', '').replace("'", "")
        
        if status_placeholder: status_placeholder.update(label=get_text("STATUS_TENTATIVA_1"), state="running")
        editais = self._executar_busca(base_url, busca_api, "edital", paginas)
        if editais: return editais, "Exata"

        stop_words = {"de", "da", "do", "para", "com", "sem", "e", "o", "a", "em", "um", "uma"}
        termos_limpos = [w for w in busca_api.split() if w.lower() not in stop_words]
        busca_flexivel = " ".join(termos_limpos)
        
        if busca_flexivel != busca_api:
            if status_placeholder: status_placeholder.update(label=get_text("STATUS_TENTATIVA_2"), state="running")
            editais = self._executar_busca(base_url, busca_flexivel, "edital", paginas)
            if editais: return editais, "Flexível"

        if status_placeholder: status_placeholder.update(label=get_text("STATUS_TENTATIVA_3"), state="running")
        editais = self._executar_busca(base_url, busca_flexivel, "", paginas)
        if editais: return editais, "Ampliada"

        return [], "Falha"

    def _executar_busca(self, url, termo, tipo_doc, paginas, status_placeholder=None):
        editais_encontrados = []
        if not tipo_doc:
            tipo_doc = "edital"
        for p in range(1, paginas + 1):
            params = {"q": termo, "ordenacao": "-dataPublicacaoPncp", "pagina": str(p), "tam_pagina": "50", "tipos_documento": tipo_doc}
            try:
                resp = self._get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    items = resp.json().get('items', [])
                    if not items:
                        break
                    editais_encontrados.extend(items)
                elif resp.status_code in [401, 403]:
                    if status_placeholder:
                        status_placeholder.update(label=f"❌ Acesso negado ao PNCP (HTTP {resp.status_code})", state="error")
                    raise PermissionError(f"Acesso negado ao PNCP (HTTP {resp.status_code}): {resp.text[:200]}")
                else:
                    if status_placeholder:
                        status_placeholder.update(label=f"❌ PNCP retornou {resp.status_code}: {resp.text[:180]}", state="error")
                    break
            except requests.RequestException as exc:
                if status_placeholder:
                    status_placeholder.update(label=f"❌ Erro de conexão PNCP: {exc}", state="error")
                break
        return editais_encontrados

    def _obter_valor_homologado_robusto(self, cnpj, ano, seq, item):
        val_h = item.get("valorUnitarioHomologado")
        if val_h and float(val_h) > 0: return float(val_h)
        num_item = item.get("numeroItem")
        url_res = f"{self.base_url_api}/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{num_item}/resultados"
        try:
            res = self._get(url_res, timeout=4)
            if res.status_code == 200:
                for r in res.json():
                    val = r.get("valorUnitarioHomologado")
                    if val and float(val) > 0: return float(val)
            elif res.status_code in [401, 403, 404]:
                pass
        except (requests.RequestException, ValueError):
            pass
        if str(item.get("situacaoCompraItem", "")) in ['4', '6']:
            val_f = item.get("valorUnitario")
            if val_f and float(val_f) > 0: return float(val_f)
        return 0.0

    def minerar_itens(self, edital, termo_busca):
        try:
            cnpj = edital.get("orgao_cnpj") or edital.get("cnpj")
            razao = edital.get("orgao_nome") or edital.get("razaoSocial") or "N/D"
            ano = edital.get("ano")
            seq = edital.get("numero_sequencial")
            data_pub = edital.get("data_publicacao_pncp")[:10]
            if not (cnpj and ano and seq): return []
            
            link_audit = f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"
            url_itens = f"{self.base_url_api}/orgaos/{cnpj}/compras/{ano}/{seq}/itens"
            resp = self._get(url_itens, timeout=10)
            
            itens = []
            if resp.status_code == 200:
                stop_words = {"de", "da", "do", "para", "com", "sem", "e", "o", "a", "em", "um", "uma", "aquisicao", "contratacao"}
                termos_chave = [normalizar_texto(t) for t in termo_busca.split() if t.lower() not in stop_words]
                for item in resp.json():
                    desc_norm = normalizar_texto(item.get("descricao", ""))
                    if all(t in desc_norm for t in termos_chave):
                        val_h = self._obter_valor_homologado_robusto(cnpj, ano, seq, item)
                        if val_h > 0:
                            itens.append({
                                "Data": datetime.strptime(data_pub, "%Y-%m-%d").strftime("%d/%m/%Y"),
                                "Empresa/Órgão": razao.upper(), 
                                "Item": item.get("descricao"), "Qtd": item.get("quantidade"),
                                "Preço": float(val_h), "Valor Unitário": formatar_moeda_ordenavel(val_h), 
                                "Origem": link_audit, "Tipo": "PNCP"
                            })
            elif resp.status_code in [401, 403]:
                raise PermissionError(f"Acesso negado ao PNCP (HTTP {resp.status_code}): {resp.text[:200]}")
            return itens
        except (requests.RequestException, ValueError) as e:
            return []
        except PermissionError:
            raise