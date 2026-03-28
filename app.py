import streamlit as st
import tempfile
import os
import hashlib
import google.generativeai as genai
from core.gemini_reasoner import extrair_solucao
from core.claude_coder import gerar_latex
from core.oracle_chat import criar_sessao_oraculo
import time


st.set_page_config(page_title="Agentic Workflow", page_icon="🤖", layout="wide")

# Inicialização de variáveis de estado (Memória da Sessão)
if "arquivos_processados" not in st.session_state:
    st.session_state.arquivos_processados = set()
if "gemini_file" not in st.session_state:
    st.session_state.gemini_file = None
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []

def calcular_hash(arquivo):
    return hashlib.md5(arquivo.getvalue()).hexdigest()

st.title("🤖 Autonomous Inspection Agent")

# O ficheiro é carregado globalmente para ser usado por ambos os separadores
uploaded_file = st.file_uploader("Carregue o seu ficheiro de registo (PDF, MD, TXT)", type=["pdf", "md", "txt"])

if uploaded_file is not None:
    arquivo_hash = calcular_hash(uploaded_file)
    
    if arquivo_hash not in st.session_state.arquivos_processados:
        with st.spinner("A carregar ficheiro para a mente do Agente (Gemini 1.5 Pro)..."):
            extensao = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Carrega o ficheiro para o Google
            st.session_state.gemini_file = genai.upload_file(path=tmp_file_path)
            
            # --- O CÓDIGO QUE FALTAVA: ESPERAR O ARQUIVO FICAR PRONTO ---
            with st.spinner("A processar as 1200 páginas no servidor (isto pode demorar alguns segundos)..."):
                while st.session_state.gemini_file.state.name == "PROCESSING":
                    time.sleep(2)
                    st.session_state.gemini_file = genai.get_file(st.session_state.gemini_file.name)
            
            if st.session_state.gemini_file.state.name == "FAILED":
                st.error("Erro crítico: O servidor falhou ao processar o PDF.")
            else:
                # Só inicializa o Oráculo quando o arquivo estiver ACTIVE
                st.session_state.chat_session = criar_sessao_oraculo(st.session_state.gemini_file)
                st.session_state.mensagens_chat = [] # Limpa o chat anterior
                st.success("✅ Ficheiro carregado e Oráculo pronto!")
            
            os.remove(tmp_file_path)
            st.session_state.arquivos_processados.add(arquivo_hash)
# Criação dos Separadores (Tabs)
tab1, tab2 = st.tabs(["📚 Gerador de LaTeX", "🔮 Chatbot do Oráculo"])

# --- SEPARADOR 1: GERADOR DE TUTORIAL ---
with tab1:
    st.markdown("### Extração em Lote para LaTeX")
    if st.session_state.gemini_file is not None:
        if st.button("🚀 Processar e Gerar Tutorial", type="primary"):
            with st.spinner("A extrair raciocínio..."):
                # No futuro, adaptaremos o gemini_reasoner para aceitar o st.session_state.gemini_file diretamente
                # Por agora, para não quebrar a sua solução existente, mantemos a estrutura atual.
                st.info("A funcionalidade de processamento em lote será ativada aqui.")
    else:
        st.warning("Por favor, carregue um ficheiro acima para iniciar.")

# --- SEPARADOR 2: O CHATBOT DO ORÁCULO ---
with tab2:
    st.markdown("### Converse com os seus Registos")
    st.markdown("*Pergunte o que deu certo na configuração do seu robô e o Oráculo irá filtrar as falhas.*")
    
    if st.session_state.chat_session is not None:
        # Exibe o histórico de mensagens
        for msg in st.session_state.mensagens_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Input do utilizador
        prompt = st.chat_input("Ex: Qual foi o comando final que fez o AMCL funcionar?")
        
        if prompt:
            # Mostra a mensagem do utilizador
            st.chat_message("user").markdown(prompt)
            st.session_state.mensagens_chat.append({"role": "user", "content": prompt})
            
            # Gera a resposta com o Gemini
            with st.chat_message("assistant"):
                with st.spinner("O Oráculo está a consultar os registos..."):
                    resposta = st.session_state.chat_session.send_message(prompt)
                    st.markdown(resposta.text)
                    
            # Guarda a resposta no histórico
            st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta.text})
    else:
        st.info("Carregue um ficheiro para despertar o Oráculo.")
