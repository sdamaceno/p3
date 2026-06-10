import streamlit as st

def load():
    st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 1600px !important; margin: 0 auto; }
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        .stApp { margin-top: 0px; background-color: #F8FAFC; }
        div[data-testid="column"] { padding-bottom: 0px !important; }
        
        .tit-contratacao { margin-bottom: 5px; }
        .tit-grupo { margin-bottom: 10px; }
        
        /* Formatação Idêntica a um Label Nativo (Sem upper, weight normal, cor padrão) */
        .section-title { 
            font-size: 12pt; 
            font-weight: 400; 
            color: #1E293B; 
            margin-bottom: 6px; 
        }
    </style>
    """, unsafe_allow_html=True)

def title_contract(title): st.markdown(f"<div class='tit-contratacao'><h3>{title}</h3></div>", unsafe_allow_html=True)
def title_group(title): st.markdown(f"<div class='tit-grupo'><h4>{title}</h4></div>", unsafe_allow_html=True)
def title_section(title): st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
def divider_sub(): st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
def divider_main(): st.markdown("---")
def spacing(): st.markdown("<br>", unsafe_allow_html=True)