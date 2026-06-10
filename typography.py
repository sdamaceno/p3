import streamlit as st

def load():
    st.markdown("""
    <style>
        /* Aplicação de fonte focada apenas em elementos de texto reais, preservando SVGs e glifos do Streamlit */
        html, body, p, label, input, textarea, td, th, li { 
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important; 
            font-size: 12pt !important;
            font-weight: 400;
            color: #1E293B;
        }
        
        /* Regra de Ouro: Negrito máximo de 300 */
        b, strong { 
            font-weight: 300 !important; 
            color: #0F2C4C; 
        }
        
        /* Cabeçalho H1 Limpo - 24pt */
        h1 { 
            font-size: 24pt !important; 
            font-weight: 800 !important; 
            letter-spacing: -0.5px; 
            margin: 20px 0 30px 0 !important; 
            color: #1E293B; 
            text-align: center; 
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        
        h3 { font-size: 16pt !important; font-weight: 300 !important; color: #0F2C4C !important; margin-bottom: 5px; }
        h4 { font-size: 14pt !important; font-weight: 300 !important; color: #0F2C4C !important; margin: 0px !important; }
    </style>
    """, unsafe_allow_html=True)