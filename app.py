import streamlit as st
import tempfile
import os
import time
from core.gemini_reasoner import destilar_log_bruto
from core.claude_coder import gerar_latex
from core.oracle_chat import criar_sessao_oraculo

WORKSPACES_DIR = os.path.join(os.path.dirname(__file__), "data", "workspaces")
os.makedirs(WORKSPACES_DIR, exist_ok=True)

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
    .block-container { padding-top: 1.5rem; max-width: 900px; }
    header[data-testid="stHeader"] { background: transparent; }
    footer { visibility: hidden; }

    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background-color: #1e293b;
        border-radius: 12px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px; padding: 8px 24px;
        color: #94a3b8; font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #10b981 !important; color: #fff !important;
    }

    .stChatMessage [data-testid="stChatMessageAvatarUser"],
    .stChatMessage [data-testid="stChatMessageAvatarAssistant"] { display: none; }
    .stChatMessage { border-radius: 18px; padding: 0.2rem 0.4rem; margin-bottom: 0.3rem; }
    .stChatMessage[data-testid="stChatMessage-user"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 100%);
        border: 1px solid #334155; margin-left: 20%; border-bottom-right-radius: 4px;
    }
    .stChatMessage[data-testid="stChatMessage-assistant"] {
        background-color: transparent; margin-right: 10%; border-bottom-left-radius: 4px;
    }

    .stChatInput { border-radius: 24px; }
    .stChatInput > div {
        border-radius: 24px; border: 1px solid #334155; background-color: #1e293b;
    }

    details[data-testid="stStatusWidget"] {
        background-color: #1e293b; border: 1px solid #334155; border-radius: 12px;
    }

    .stButton > button[kind="primary"] {
        background-color: #10b981; border: none; border-radius: 10px; font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover { background-color: #059669; }
    .stDownloadButton > button {
        background-color: #1e293b; border: 1px solid #334155; border-radius: 10px;
    }

    .brand-text { font-size: 0.7rem; color: #475569; text-align: center; padding: 1rem 0; }
    .msg-actions { margin-top: 4px; }
    .msg-actions button {
        background: none; border: none; color: #64748b; cursor: pointer;
        font-size: 0.8rem; padding: 2px 8px; border-radius: 6px;
    }
    .msg-actions button:hover { background-color: #334155; color: #e2e8f0; }
    .file-chip {
        display: inline-flex; align-items: center;
        background-color: #1e293b; border: 1px solid #334155;
        border-radius: 8px; padding: 4px 10px; margin: 3px 0;
        font-size: 0.8rem; color: #cbd5e1;
    }
    .file-chip .icon { margin-right: 6px; }
    .ws-badge {
        display: inline-block; background: #10b981; color: #fff;
        border-radius: 6px; padding: 2px 10px; font-size: 0.75rem;
        font-weight: 600; margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ─────────────────────────────────────────────────────────
def listar_workspaces():
    if not os.path.isdir(WORKSPACES_DIR):
        return []
    return sorted([
        d for d in os.listdir(WORKSPACES_DIR)
        if os.path.isdir(os.path.join(WORKSPACES_DIR, d))
    ])


def listar_destilados(workspace_path):
    import glob
    return sorted(glob.glob(os.path.join(workspace_path, "*_distilled.md")))


def typewriter(text, speed=0.015):
    container = st.empty()
    displayed = ""
    words = text.split(" ")
    for i, word in enumerate(words):
        displayed += word + (" " if i < len(words) - 1 else "")
        container.markdown(displayed + "▌")
        time.sleep(speed)
    container.markdown(displayed)


# ── Inicialização de Estado ─────────────────────────────────────────
defaults = {
    "workspace_activo": None,
    "chat_session": None,
    "mensagens_chat": [],
    "codigo_latex": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── SIDEBAR ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 Inspection Agent")
    st.markdown("---")

    # ── Workspace selector ──
    st.markdown("### Workspace")
    workspaces = listar_workspaces()

    if workspaces:
        ws_selecionado = st.selectbox(
            "Selecionar workspace",
            workspaces,
            index=workspaces.index(st.session_state.workspace_activo)
                if st.session_state.workspace_activo in workspaces else 0,
        )
        if ws_selecionado != st.session_state.workspace_activo:
            st.session_state.workspace_activo = ws_selecionado
            st.session_state.chat_session = None
            st.session_state.mensagens_chat = []
            st.session_state.codigo_latex = None
    else:
        st.info("Nenhum workspace criado ainda.", icon="📁")
        ws_selecionado = None

    # Criar novo workspace
    with st.expander("➕ Criar novo workspace"):
        novo_ws = st.text_input("Nome do workspace", placeholder="ex: Navegação Go2")
        if st.button("Criar", use_container_width=True) and novo_ws.strip():
            nome_safe = novo_ws.strip().replace(" ", "_").replace("/", "_")
            ws_path = os.path.join(WORKSPACES_DIR, nome_safe)
            os.makedirs(ws_path, exist_ok=True)
            st.session_state.workspace_activo = nome_safe
            st.session_state.chat_session = None
            st.session_state.mensagens_chat = []
            st.session_state.codigo_latex = None
            st.rerun()

    st.markdown("---")

    # ── Upload & Destilação ──
    st.markdown("### Upload & Destilação")
    uploaded_files = st.file_uploader(
        "📎 Logs brutos",
        type=["pdf", "md", "txt"],
        accept_multiple_files=True,
        help="Ficheiros brutos que serão destilados pelo Gemini.",
    )

    ws_path_activo = (
        os.path.join(WORKSPACES_DIR, st.session_state.workspace_activo)
        if st.session_state.workspace_activo else None
    )

    if uploaded_files and ws_path_activo:
        if st.button("🧪 Processar e Destilar Conhecimento", type="primary", use_container_width=True):
            with st.status(
                f"🧪 A destilar {len(uploaded_files)} ficheiro(s)...", expanded=True
            ) as status:
                for uf in uploaded_files:
                    st.write(f"📤 **{uf.name}** — Preparando destilação...")
                    extensao = os.path.splitext(uf.name)[1]
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=extensao, prefix=uf.name.rsplit(".", 1)[0][:40] + "_"
                    ) as tmp_file:
                        tmp_file.write(uf.getvalue())
                        tmp_path = tmp_file.name

                    try:
                        caminho_destilado = destilar_log_bruto(
                            tmp_path, ws_path_activo,
                            callback=lambda msg: st.write(msg),
                        )
                        st.write(f"💾 **{uf.name}** → `{os.path.basename(caminho_destilado)}`")
                    except Exception as e:
                        st.error(f"❌ Erro ao destilar **{uf.name}**: {e}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

                st.session_state.chat_session = None
                st.session_state.mensagens_chat = []
                status.update(label="✅ Destilação completa!", state="complete")
    elif uploaded_files and not ws_path_activo:
        st.warning("Crie ou selecione um workspace primeiro.")

    # ── Ficheiros destilados no workspace ──
    st.markdown("---")
    if ws_path_activo:
        destilados = listar_destilados(ws_path_activo)
        if destilados:
            st.markdown(f"**{len(destilados)} doc(s) destilado(s):**")
            for d in destilados:
                nome = os.path.basename(d)
                st.markdown(
                    f'<div class="file-chip"><span class="icon">📗</span>{nome}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("Workspace vazio. Envie logs para destilar.", icon="📁")
    else:
        st.info("Nenhum workspace activo", icon="📁")

    st.markdown('<p class="brand-text">Powered by Gemini 3.1 Pro + Claude Sonnet 4</p>', unsafe_allow_html=True)


# ── HEADER ──────────────────────────────────────────────────────────
st.markdown("# 🔬 Autonomous Inspection Agent")
if st.session_state.workspace_activo:
    st.markdown(
        f'<span class="ws-badge">Workspace: {st.session_state.workspace_activo}</span>',
        unsafe_allow_html=True,
    )
st.markdown(
    '<span style="color:#64748b;font-size:0.95rem;">'
    "Destile conhecimento de logs robóticos, gere tutoriais LaTeX ou converse com o Oráculo.</span>",
    unsafe_allow_html=True,
)

# ── TABS ────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📚 Gerador LaTeX", "🔮 Chat com Oráculo"])

# ── TAB 1: GERADOR DE TUTORIAL LATEX ───────────────────────────────
with tab1:
    st.markdown("### Geração de Tutorial LaTeX")
    st.markdown(
        '<span style="color:#94a3b8;">Gera um tutorial completo a partir da base de conhecimento destilada.</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    if ws_path_activo and listar_destilados(ws_path_activo):
        if st.button("🚀 Gerar Tutorial LaTeX", type="primary", use_container_width=True):
            with st.status("🧠 Pipeline em execução...", expanded=True) as status:
                st.write("**Claude Sonnet 4** — Gerando LaTeX a partir do conhecimento destilado...")
                codigo_latex = gerar_latex(ws_path_activo)
                st.session_state.codigo_latex = codigo_latex
                status.update(label="✅ Tutorial gerado com sucesso!", state="complete")

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
            "<p>Selecione um workspace com conhecimento destilado para gerar o tutorial.</p></div>",
            unsafe_allow_html=True,
        )

# ── TAB 2: CHATBOT DO ORÁCULO ──────────────────────────────────────
with tab2:
    if ws_path_activo and listar_destilados(ws_path_activo):
        # Inicializa o chat se necessário
        if st.session_state.chat_session is None:
            try:
                st.session_state.chat_session = criar_sessao_oraculo(ws_path_activo)
            except ValueError as e:
                st.error(str(e))

        if st.session_state.chat_session is not None:
            destilados = listar_destilados(ws_path_activo)
            nomes = ", ".join(os.path.basename(d) for d in destilados)
            st.markdown(
                f'<div style="text-align:center;padding:8px;margin-bottom:1rem;'
                f'background:#1e293b;border-radius:12px;border:1px solid #334155;">'
                f'<span style="color:#94a3b8;font-size:0.85rem;">🔮 Oráculo activo — '
                f'<strong style="color:#10b981;">{len(destilados)}</strong> doc(s) destilado(s)</span></div>',
                unsafe_allow_html=True,
            )

            for msg in st.session_state.mensagens_chat:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant":
                        st.markdown(
                            '<div class="msg-actions">'
                            '<button title="Copiar" onclick="navigator.clipboard.writeText('
                            "this.closest('[data-testid]').querySelector('p')?.innerText || '')"
                            '">📋 Copiar</button></div>',
                            unsafe_allow_html=True,
                        )

            prompt = st.chat_input("Pergunte ao Oráculo sobre os seus registos...")

            if prompt:
                st.chat_message("user").markdown(prompt)
                st.session_state.mensagens_chat.append({"role": "user", "content": prompt})

                with st.chat_message("assistant"):
                    with st.status("🔮 A consultar a base de conhecimento...", expanded=False):
                        resposta = st.session_state.chat_session.send_message(prompt)
                    typewriter(resposta.text)
                    st.markdown(
                        '<div class="msg-actions">'
                        '<button title="Copiar" onclick="navigator.clipboard.writeText('
                        "this.closest('[data-testid]').querySelector('p')?.innerText || '')"
                        '">📋 Copiar</button></div>',
                        unsafe_allow_html=True,
                    )

                st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta.text})
    else:
        st.markdown(
            '<div style="text-align:center;padding:5rem 1rem;color:#64748b;">'
            '<p style="font-size:4rem;">🔮</p>'
            "<h3>Converse com os seus Registos</h3>"
            "<p>Selecione um workspace e destile logs para despertar o Oráculo.</p>"
            '<p style="font-size:0.85rem;color:#475569;margin-top:1rem;">'
            "O Oráculo responde com base na base de conhecimento destilada.</p></div>",
            unsafe_allow_html=True,
        )
