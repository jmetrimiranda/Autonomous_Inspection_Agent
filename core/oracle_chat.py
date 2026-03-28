import google.generativeai as genai
import os
import glob
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

NOME_MODELO = "gemini-3.1-pro-preview"

INSTRUCAO_SISTEMA = """
És o Oráculo de Robótica, um Engenheiro de Elite e Assistente de Investigação.
A tua ÚNICA fonte de conhecimento é a Base de Conhecimento Destilada fornecida abaixo.

REGRAS:
1. Responde EXCLUSIVAMENTE com base na informação da base de conhecimento.
2. Se o utilizador perguntar como fazer algo, lista SEMPRE os pré-requisitos antes de dar a solução.
3. Se a resposta não estiver na base de conhecimento, diz que não tens essa informação.
4. Sê conciso, técnico e directo.
"""


def _carregar_base_conhecimento(workspace_path: str) -> str:
    """Lê todos os ficheiros _distilled.md do workspace e concatena numa string."""
    ficheiros = sorted(glob.glob(os.path.join(workspace_path, "*_distilled.md")))
    if not ficheiros:
        return ""

    partes = []
    for f in ficheiros:
        nome = os.path.basename(f)
        with open(f, "r", encoding="utf-8") as fh:
            conteudo = fh.read()
        partes.append(f"---\n### Fonte: {nome}\n{conteudo}")

    return "\n\n".join(partes)


def criar_sessao_oraculo(workspace_path: str):
    """
    Cria uma sessão de chat com o Oráculo usando a base de conhecimento
    destilada do workspace (ficheiros _distilled.md leves em texto).

    Retorna o chat session.
    """
    base = _carregar_base_conhecimento(workspace_path)

    if not base:
        raise ValueError("Nenhum conhecimento destilado encontrado neste workspace. Processe ficheiros primeiro.")

    model = genai.GenerativeModel(
        model_name=NOME_MODELO,
        system_instruction=INSTRUCAO_SISTEMA,
    )

    chat = model.start_chat()

    # Injeta a base de conhecimento como primeira mensagem (texto leve)
    chat.send_message(
        f"BASE DE CONHECIMENTO DESTILADA:\n\n{base}\n\n"
        "Analisa esta base de conhecimento. A partir de agora, responde às minhas "
        "perguntas baseado exclusivamente nestas informações."
    )

    return chat
