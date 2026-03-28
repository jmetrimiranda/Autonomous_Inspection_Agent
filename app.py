import streamlit as st
import tempfile
import os
import hashlib
import time
import google.generativeai as genai
from core.gemini_reasoner import extrair_solucao
from core.claude_coder import gerar_latex
from core.oracle_chat import criar_sessao_oraculo

# ── Configuração da Página ──────────────────────────────────────────
st.set_page_config(
    page_title="Autonomous Inspection Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Customizado (SOTA Dark UI) ─────────────────────────────────
st.markdown("""
<style>
    /* Remove padding superior padrão */
    .block-container { padding-top: 2rem; }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] .stFileUploader label {
        font-size: 0.9rem;
        color: #94a3b8;
    }

    /* Chat messages */
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1e293b;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background-color: #10b981 !important;
        color: #ffffff !important;
    }

    /* Status containers */
    details[data-testid="stStatusWidget"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
    }

    /* Botões */
    .stButton > button[kind="primary"] {
        background-color: #10b981;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #059669;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
    }

    /* Esconde o rodapé padrão do Streamlit */
    footer { visibility: hidden; }

    /* Branding sutil */
    .brand-text {
        font-size: 0.75rem;
        color: #475569;
        text-align: center;
        padding: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Inicialização de Estado ─────────────────────────────────────────
if "arquivos_processados" not in st.session_state:
    st.session_state.arquivos_processados = set()
if "gemini_file" not in st.session_state:
    st.session_state.gemini_file = None
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []
if "resumo_gemini" not in st.session_state:
    st.session_state.resumo_gemini = None
if "codigo_latex" not in st.session_state:
    st.session_state.codigo_latex = None


def calcular_hash(arquivo):
    return hashlib.md5(arquivo.getvalue()).hexdigest()


def typewriter(text, speed=0.02):
    """Simula efeito de digitação palavra por palavra (estilo ChatGPT)."""
    container = st.empty()
    displayed = ""
    words = text.split(" ")
    for i, word in enumerate(words):
        displayed += word + (" " if i < len(words) - 1 else "")
        container.markdown(displayed + "▌")
        time.sleep(speed)
    container.markdown(displayed)


def limpar_sessao():
    """Reseta todo o estado para uma nova sessão."""
    st.session_state.arquivos_processados = set()
    st.session_state.gemini_file = None
    st.session_state.chat_session = None
    st.session_state.mensagens_chat = []
    st.session_state.resumo_gemini = None
    st.session_state.codigo_latex = None


# ── SIDEBAR ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 Inspection Agent")
    st.markdown("---")

    uploaded_file = st.file_uploader(
        "📎 Carregar ficheiro de registo",
        type=["pdf", "md", "txt"],
        help="Suporta PDF, Markdown e texto plano.",
    )

    st.markdown("")
    if st.button("🗑️ Limpar Chat / Novo Ficheiro", use_container_width=True):
        limpar_sessao()
        st.rerun()

    # Indicador de estado
    st.markdown("---")
    if st.session_state.gemini_file is not None:
        st.success("Ficheiro activo", icon="✅")
    else:
        st.info("Nenhum ficheiro carregado", icon="📄")

    st.markdown('<p class="brand-text">Powered by Gemini + Claude</p>', unsafe_allow_html=True)

# ── PROCESSAMENTO DO UPLOAD (com st.status) ─────────────────────────
if uploaded_file is not None:
    arquivo_hash = calcular_hash(uploaded_file)

    if arquivo_hash not in st.session_state.arquivos_processados:
        with st.status("🚀 A preparar o Agente...", expanded=True) as status:
            # Etapa 1: Upload
            st.write("📤 A enviar ficheiro para o servidor Gemini...")
            extensao = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            st.session_state.gemini_file = genai.upload_file(path=tmp_file_path)
            st.write("✅ Ficheiro enviado com sucesso.")

            # Etapa 2: Processamento
            st.write("⏳ A processar no servidor (pode demorar alguns segundos)...")
            while st.session_state.gemini_file.state.name == "PROCESSING":
                time.sleep(2)
                st.session_state.gemini_file = genai.get_file(st.session_state.gemini_file.name)

            if st.session_state.gemini_file.state.name == "FAILED":
                status.update(label="❌ Erro no processamento", state="error")
                st.error("O servidor falhou ao processar o ficheiro.")
            else:
                # Etapa 3: Inicializar Oráculo
                st.write("🔮 A despertar o Oráculo...")
                st.session_state.chat_session = criar_sessao_oraculo(st.session_state.gemini_file)
                st.session_state.mensagens_chat = []
                status.update(label="✅ Agente pronto!", state="complete")

            os.remove(tmp_file_path)
            st.session_state.arquivos_processados.add(arquivo_hash)

# ── HEADER ──────────────────────────────────────────────────────────
st.markdown("# 🔬 Autonomous Inspection Agent")
st.markdown(
    '<span style="color:#64748b;">Análise inteligente de logs robóticos — '
    "extraia tutoriais LaTeX ou converse com o Oráculo sobre os seus registos.</span>",
    unsafe_allow_html=True,
)

# ── TABS ────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📚 Gerador LaTeX", "🔮 Chat com Oráculo"])

# ── TAB 1: GERADOR DE TUTORIAL LATEX ───────────────────────────────
with tab1:
    st.markdown("### Extracção e Geração de Tutorial")
    st.markdown(
        '<span style="color:#94a3b8;">O Gemini extrai o raciocínio do log e o Claude gera o código LaTeX.</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    if st.session_state.gemini_file is not None:
        if st.button("🚀 Processar e Gerar Tutorial", type="primary", use_container_width=True):
            # Passo 1: Reasoning com Gemini
            with st.status("🧠 Pipeline Agentic em execução...", expanded=True) as status:
                st.write("**Etapa 1/2** — Gemini: Extraindo raciocínio do log...")
                extensao = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name

                resumo_gemini = extrair_solucao(tmp_file_path)
                os.remove(tmp_file_path)
                st.session_state.resumo_gemini = resumo_gemini
                st.write("✅ Raciocínio extraído.")

                # Passo 2: LaTeX com Claude
                st.write("**Etapa 2/2** — Claude: Gerando código LaTeX...")
                codigo_latex = gerar_latex(resumo_gemini)
                st.session_state.codigo_latex = codigo_latex
                status.update(label="✅ Tutorial gerado com sucesso!", state="complete")

        # Exibe resultados se existirem
        if st.session_state.resumo_gemini is not None:
            with st.expander("👀 Ver Raciocínio Extraído (Gemini)", expanded=False):
                st.markdown(st.session_state.resumo_gemini)

        if st.session_state.codigo_latex is not None:
            st.markdown("#### Código LaTeX Gerado")
            st.code(st.session_state.codigo_latex, language="latex")
            st.download_button(
                label="⬇️ Baixar arquivo .tex",
                data=st.session_state.codigo_latex,
                file_name="tutorial_solucao.tex",
                mime="text/plain",
                use_container_width=True,
            )
    else:
        st.markdown(
            """
            <div style="text-align:center; padding:3rem 1rem; color:#64748b;">
                <p style="font-size:3rem;">📄</p>
                <p>Carregue um ficheiro na barra lateral para iniciar.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── TAB 2: CHATBOT DO ORÁCULO ──────────────────────────────────────
with tab2:
    st.markdown("### Converse com os seus Registos")
    st.markdown(
        '<span style="color:#94a3b8;">Pergunte ao Oráculo sobre soluções de sucesso nos seus logs.</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    if st.session_state.chat_session is not None:
        # Histórico de mensagens
        for msg in st.session_state.mensagens_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input fixo no rodapé
        prompt = st.chat_input("Ex: Qual foi o comando final que fez o AMCL funcionar?")

        if prompt:
            st.chat_message("user").markdown(prompt)
            st.session_state.mensagens_chat.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.status("🔮 O Oráculo está a consultar os registos...", expanded=False):
                    resposta = st.session_state.chat_session.send_message(prompt)
                typewriter(resposta.text)

            st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta.text})
    else:
        st.markdown(
            """
            <div style="text-align:center; padding:3rem 1rem; color:#64748b;">
                <p style="font-size:3rem;">🔮</p>
                <p>Carregue um ficheiro para despertar o Oráculo.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
