import streamlit as st
import tempfile
import os
from core.gemini_reasoner import extrair_solucao
from core.claude_coder import gerar_latex

# Configuração da página do Streamlit
st.set_page_config(page_title="Log2Tex Agent", page_icon="🤖", layout="wide")

st.title("🤖 Log2Tex: Debug-to-Tutorial Pipeline")
st.markdown("Faça o upload do seu histórico de depuração (.md ou .txt) para extrair a solução e gerar o LaTeX.")

# File uploader
uploaded_file = st.file_uploader("Envie o arquivo de log (Markdown ou TXT)", type=["md", "txt"])

if uploaded_file is not None:
    if st.button("🚀 Processar e Gerar Tutorial", type="primary"):
        
        with st.spinner("Lendo arquivo e iniciando camada de Reasoning (Gemini 1.5 Pro)..."):
            # Salva o arquivo temporariamente para o Gemini ler
            with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Passo 1: Extração com Gemini
            resumo_gemini = extrair_solucao(tmp_file_path)
            
            # Remove o arquivo temporário
            os.remove(tmp_file_path)
            
        st.success("Reasoning concluído! Extração da solução finalizada.")
        
        with st.expander("👀 Ver Raciocínio Extraído (Gemini)"):
            st.markdown(resumo_gemini)
            
        with st.spinner("Traduzindo lógica para sintaxe LaTeX (Claude 3.5 Sonnet)..."):
            # Passo 2: Geração de LaTeX com Claude
            codigo_latex = gerar_latex(resumo_gemini)
            
        st.success("Código LaTeX gerado com sucesso!")
        
        # Exibe o código gerado
        st.code(codigo_latex, language="latex")
        
        # Botão para download do arquivo .tex
        st.download_button(
            label="⬇️ Baixar arquivo .tex",
            data=codigo_latex,
            file_name="tutorial_solucao.tex",
            mime="text/plain"
        )
