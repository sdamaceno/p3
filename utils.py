import hashlib
import re
import unicodedata
import pandas as pd
from texts import get_format

def normalizar_texto(texto):
    if not isinstance(texto, str): return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()

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

def parse_numero_localizado(valor):
    """Converte strings (ex: '15.000', '1,5') em float nativo de acordo com a localização i18n."""
    if pd.isna(valor) or valor == "":
        return 1.0
    if isinstance(valor, (int, float)):
        return float(valor)
    
    val_str = str(valor).strip()
    dec_sep = get_format("DECIMAL_SEP")
    thou_sep = get_format("THOUSANDS_SEP")
    
    if thou_sep:
        val_str = val_str.replace(thou_sep, "")
    if dec_sep and dec_sep != ".":
        val_str = val_str.replace(dec_sep, ".")
        
    try:
        return float(val_str)
    except ValueError:
        return 1.0

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