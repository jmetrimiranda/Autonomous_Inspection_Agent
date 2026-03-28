import streamlit as st
import tempfile
import os
import hashlib
import time
import google.generativeai as genai
from core.gemini_reasoner import extrair_solucao_multi
from core.claude_coder import gerar_latex
from core.oracle_chat import criar_sessao_oraculo

# ── Configuração da Página ──────────────────────────────────────────
st.set_page_config(
    page_title="Autonomous Inspection Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Customizado (Gemini-Style Dark UI) ──────────────────────────
st.markdown("""
<style>
    /* ── Reset & Layout ── */
    .block-container { padding-top: 1.5rem; max-width: 900px; }
    header[data-testid="stHeader"] { background: transparent; }
    footer { visibility: hidden; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }

    /* ── Tabs (pill style) ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #1e293b;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 24px;
        color: #94a3b8;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #10b981 !important;
        color: #fff !important;
    }

    /* ── Chat: esconde avatares padrão do Streamlit ── */
    .stChatMessage [data-testid="stChatMessageAvatarUser"],
    .stChatMessage [data-testid="stChatMessageAvatarAssistant"] {
        display: none;
    }

    /* ── Chat bolhas base ── */
    .stChatMessage {
        border-radius: 18px;
        padding: 0.2rem 0.4rem;
        margin-bottom: 0.3rem;
    }

    /* ── Bolha do User (alinhada à direita, fundo accent) ── */
    .stChatMessage[data-testid="stChatMessage-user"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 100%);
        border: 1px solid #334155;
        margin-left: 20%;
        border-bottom-right-radius: 4px;
    }

    /* ── Bolha do Assistant (alinhada à esquerda, fundo sutil) ── */
    .stChatMessage[data-testid="stChatMessage-assistant"] {
        background-color: transparent;
        margin-right: 10%;
        border-bottom-left-radius: 4px;
    }

    /* ── Chat input bar (Gemini-style) ── */
    .stChatInput {
        border-radius: 24px;
    }
    .stChatInput > div {
        border-radius: 24px;
        border: 1px solid #334155;
        background-color: #1e293b;
    }

    /* ── Status containers ── */
    details[data-testid="stStatusWidget"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
    }

    /* ── Botões ── */
    .stButton > button[kind="primary"] {
        background-color: #10b981;
        border: none;
        border-radius: 10px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover { background-color: #059669; }

    .stDownloadButton > button {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
    }

    /* ── Branding ── */
    .brand-text {
        font-size: 0.7rem;
        color: #475569;
        text-align: center;
        padding: 1rem 0;
    }

    /* ── Ações da mensagem (copiar, etc.) ── */
    .msg-actions { margin-top: 4px; }
    .msg-actions button {
        background: none;
        border: none;
        color: #64748b;
        cursor: pointer;
        font-size: 0.8rem;
        padding: 2px 8px;
        border-radius: 6px;
    }
    .msg-actions button:hover { background-color: #334155; color: #e2e8f0; }

    /* ── Ficheiros carregados na sidebar ── */
    .file-chip {
        display: inline-flex;
        align-items: center;
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 4px 10px;
        margin: 3px 0;
        font-size: 0.8rem;
        color: #cbd5e1;
    }
    .file-chip .icon { margin-right: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Inicialização de Estado ─────────────────────────────────────────
defaults = {
    "arquivos_processados": set(),
    "gemini_files": [],          # lista de gemini file objects
    "chat_session": None,
    "mensagens_chat": [],
    "resumo_gemini": None,
    "codigo_latex": None,
    "nomes_ficheiros": [],       # nomes dos ficheiros carregados
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def calcular_hash(arquivo):
    return hashlib.md5(arquivo.getvalue()).hexdigest()


def typewriter(text, speed=0.015):
    """Efeito de digitação palavra por palavra (estilo Gemini/ChatGPT)."""
    container = st.empty()
    displayed = ""
    words = text.split(" ")
    for i, word in enumerate(words):
        displayed += word + (" " if i < len(words) - 1 else "")
        container.markdown(displayed + "▌")
        time.sleep(speed)
    container.markdown(displayed)


def limpar_sessao():
    for key, val in defaults.items():
        st.session_state[key] = type(val)() if isinstance(val, (set, list)) else val


# ── SIDEBAR ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 Inspection Agent")
    st.markdown("---")

    uploaded_files = st.file_uploader(
        "📎 Carregar ficheiros de registo",
        type=["pdf", "md", "txt"],
        accept_multiple_files=True,
        help="Suporta PDF, Markdown e texto plano. Pode enviar vários ficheiros.",
    )

    st.markdown("")
    if st.button("🗑️  Limpar Chat / Nova Sessão", use_container_width=True):
        limpar_sessao()
        st.rerun()

    # Mostra ficheiros activos
    st.markdown("---")
    if st.session_state.nomes_ficheiros:
        st.markdown(f"**{len(st.session_state.nomes_ficheiros)} ficheiro(s) activo(s):**")
        for nome in st.session_state.nomes_ficheiros:
            ext = os.path.splitext(nome)[1].lower()
            icon = "📕" if ext == ".pdf" else "📝" if ext == ".md" else "📄"
            st.markdown(f'<div class="file-chip"><span class="icon">{icon}</span>{nome}</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhum ficheiro carregado", icon="📄")

    st.markdown('<p class="brand-text">Powered by Gemini 3.1 Pro + Claude Sonnet 4</p>', unsafe_allow_html=True)

# ── PROCESSAMENTO DO UPLOAD (multi-file com st.status) ──────────────
if uploaded_files:
    novos_ficheiros = []
    for uf in uploaded_files:
        h = calcular_hash(uf)
        if h not in st.session_state.arquivos_processados:
            novos_ficheiros.append((uf, h))

    if novos_ficheiros:
        with st.status(f"🚀 A carregar {len(novos_ficheiros)} ficheiro(s)...", expanded=True) as status:
            for uf, h in novos_ficheiros:
                st.write(f"📤 A enviar **{uf.name}**...")
                extensao = os.path.splitext(uf.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as tmp_file:
                    tmp_file.write(uf.getvalue())
                    tmp_file_path = tmp_file.name

                gf = genai.upload_file(path=tmp_file_path)

                st.write(f"⏳ A processar **{uf.name}** no servidor...")
                while gf.state.name == "PROCESSING":
                    time.sleep(2)
                    gf = genai.get_file(gf.name)

                if gf.state.name == "FAILED":
                    st.error(f"❌ Falha ao processar {uf.name}")
                else:
                    st.session_state.gemini_files.append(gf)
                    st.session_state.nomes_ficheiros.append(uf.name)
                    st.write(f"✅ **{uf.name}** pronto.")

                os.remove(tmp_file_path)
                st.session_state.arquivos_processados.add(h)

            # (Re)inicializa o Oráculo com todos os ficheiros
            if st.session_state.gemini_files:
                st.write("🔮 A despertar o Oráculo com todos os documentos...")
                try:
                    chat, carregados, excluidos = criar_sessao_oraculo(st.session_state.gemini_files)
                    st.session_state.chat_session = chat
                    st.session_state.mensagens_chat = []

                    if excluidos:
                        nomes_excl = [st.session_state.nomes_ficheiros[i] for i in excluidos]
                        st.warning(
                            f"⚠️ {len(excluidos)} ficheiro(s) excediam o limite de tokens e foram excluídos "
                            f"do chat: **{', '.join(nomes_excl)}**. Tente ficheiros menores ou envie-os separadamente."
                        )
                        n_ok = len(carregados)
                    else:
                        n_ok = len(st.session_state.gemini_files)

                    status.update(label=f"✅ {n_ok} ficheiro(s) activo(s) no Oráculo — Agente pronto!", state="complete")
                except ValueError as e:
                    st.error(f"❌ {e}")
                    status.update(label="❌ Ficheiros demasiado grandes para o modelo", state="error")
            else:
                status.update(label="❌ Nenhum ficheiro foi processado com sucesso", state="error")

# ── HEADER ──────────────────────────────────────────────────────────
st.markdown("# 🔬 Autonomous Inspection Agent")
st.markdown(
    '<span style="color:#64748b;font-size:0.95rem;">Análise inteligente de logs robóticos — '
    "extraia tutoriais LaTeX ou converse com o Oráculo.</span>",
    unsafe_allow_html=True,
)

# ── TABS ────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📚 Gerador LaTeX", "🔮 Chat com Oráculo"])

# ── TAB 1: GERADOR DE TUTORIAL LATEX ───────────────────────────────
with tab1:
    st.markdown("### Extracção e Geração de Tutorial")
    st.markdown(
        '<span style="color:#94a3b8;">O Gemini extrai o raciocínio dos logs e o Claude gera o código LaTeX.</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    if st.session_state.gemini_files:
        if st.button("🚀 Processar e Gerar Tutorial", type="primary", use_container_width=True):
            with st.status("🧠 Pipeline Agentic em execução...", expanded=True) as status:
                # Passo 1: salvar todos os ficheiros temporariamente para o reasoner
                st.write(f"**Etapa 1/2** — Gemini: Extraindo raciocínio de {len(uploaded_files)} ficheiro(s)...")
                tmp_paths = []
                for uf in uploaded_files:
                    extensao = os.path.splitext(uf.name)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as tmp_file:
                        tmp_file.write(uf.getvalue())
                        tmp_paths.append(tmp_file.name)

                resumo_gemini = extrair_solucao_multi(tmp_paths)

                for p in tmp_paths:
                    os.remove(p)

                st.session_state.resumo_gemini = resumo_gemini
                st.write("✅ Raciocínio extraído.")

                # Passo 2: LaTeX com Claude
                st.write("**Etapa 2/2** — Claude: Gerando código LaTeX...")
                codigo_latex = gerar_latex(resumo_gemini)
                st.session_state.codigo_latex = codigo_latex
                status.update(label="✅ Tutorial gerado com sucesso!", state="complete")

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
            '<div style="text-align:center;padding:4rem 1rem;color:#64748b;">'
            '<p style="font-size:3rem;">📄</p>'
            "<p>Carregue ficheiro(s) na barra lateral para iniciar.</p></div>",
            unsafe_allow_html=True,
        )

# ── TAB 2: CHATBOT DO ORÁCULO (Gemini-style) ───────────────────────
with tab2:
    if st.session_state.chat_session is not None:
        # Mostra contexto activo
        n = len(st.session_state.nomes_ficheiros)
        nomes = ", ".join(st.session_state.nomes_ficheiros)
        st.markdown(
            f'<div style="text-align:center;padding:8px;margin-bottom:1rem;'
            f'background:#1e293b;border-radius:12px;border:1px solid #334155;">'
            f'<span style="color:#94a3b8;font-size:0.85rem;">🔮 Oráculo activo com '
            f'<strong style="color:#10b981;">{n}</strong> documento(s): {nomes}</span></div>',
            unsafe_allow_html=True,
        )

        # Histórico de mensagens
        for msg in st.session_state.mensagens_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                # Botões de acção nas mensagens do assistente
                if msg["role"] == "assistant":
                    st.markdown(
                        '<div class="msg-actions">'
                        '<button title="Copiar" onclick="navigator.clipboard.writeText(this.closest(\'[data-testid]\').querySelector(\'p\')?.innerText || \'\')">📋 Copiar</button>'
                        "</div>",
                        unsafe_allow_html=True,
                    )

        # Input fixo no rodapé
        prompt = st.chat_input("Pergunte ao Oráculo sobre os seus registos...")

        if prompt:
            st.chat_message("user").markdown(prompt)
            st.session_state.mensagens_chat.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.status("🔮 A consultar os registos...", expanded=False):
                    resposta = st.session_state.chat_session.send_message(prompt)
                typewriter(resposta.text)
                st.markdown(
                    '<div class="msg-actions">'
                    '<button title="Copiar" onclick="navigator.clipboard.writeText(this.closest(\'[data-testid]\').querySelector(\'p\')?.innerText || \'\')">📋 Copiar</button>'
                    "</div>",
                    unsafe_allow_html=True,
                )

            st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta.text})
    else:
        st.markdown(
            '<div style="text-align:center;padding:5rem 1rem;color:#64748b;">'
            '<p style="font-size:4rem;">🔮</p>'
            "<h3>Converse com os seus Registos</h3>"
            "<p>Carregue ficheiro(s) na barra lateral para despertar o Oráculo.</p>"
            '<p style="font-size:0.85rem;color:#475569;margin-top:1rem;">'
            "O Oráculo filtra apenas as soluções de sucesso dos seus logs.</p></div>",
            unsafe_allow_html=True,
        )
