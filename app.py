import streamlit as st
import tempfile
import os
import hashlib
from core.gemini_reasoner import extrair_solucao
from core.claude_coder import gerar_latex

# Configuração da página do Streamlit
st.set_page_config(page_title="Log2Tex Agent", page_icon="🤖", layout="wide")

# Inicializa a memória da sessão para evitar duplicação de arquivos
if "arquivos_processados" not in st.session_state:
    st.session_state.arquivos_processados = set()

def calcular_hash(arquivo):
    """Gera uma assinatura única (hash MD5) para o arquivo enviado."""
    return hashlib.md5(arquivo.getvalue()).hexdigest()

st.title("🤖 Log2Tex: Debug-to-Tutorial Pipeline")
st.markdown("Faça o upload do seu histórico de depuração (.pdf, .md ou .txt) para extrair a solução e gerar o LaTeX.")

# File uploader (agora aceita PDF também)
uploaded_file = st.file_uploader("Envie o arquivo de log", type=["pdf", "md", "txt"])

if uploaded_file is not None:
    arquivo_hash = calcular_hash(uploaded_file)
    
    # Filtro Anti-Duplicação
    if arquivo_hash in st.session_state.arquivos_processados:
        st.warning("⚠️ Este arquivo já foi processado nesta sessão! Envie um arquivo diferente para evitar gastos desnecessários de tokens.")
    else:
        st.success("✅ Arquivo inédito detectado. Pronto para análise.")
        
        if st.button("🚀 Processar e Gerar Tutorial", type="primary"):
            
            with st.spinner("Lendo arquivo e iniciando camada de Reasoning (Gemini 1.5 Pro)..."):
                # Mantém a extensão correta (.pdf ou .md) no arquivo temporário
                extensao = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Passo 1: Extração com Gemini (Multimodal)
                resumo_gemini = extrair_solucao(tmp_file_path)
                
                # Remove o arquivo temporário do seu PC
                os.remove(tmp_file_path)
                
                # Salva o hash na memória para bloquear envios repetidos
                st.session_state.arquivos_processados.add(arquivo_hash)
                
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