import google.generativeai as genai
import os
from dotenv import load_dotenv
from google.api_core.exceptions import InvalidArgument

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

INSTRUCAO_SISTEMA = """
    És o 'Oráculo', um Engenheiro Robótico de Elite e Assistente de Investigação.
    A sua ÚNICA fonte de conhecimento para esta conversa são os documentos de registo/conversa fornecidos.

    REGRA DE OURO: Quando o utilizador fizer uma pergunta, deves procurar nos documentos a solução que FUNCIONOU.
    Ignora absolutamente todas as tentativas falhadas, erros de compilação, ou caminhos que não deram em nada.
    Se a resposta não estiver nos documentos, diz simplesmente que não tens essa informação no contexto fornecido.
"""


def _criar_modelo():
    return genai.GenerativeModel(
        model_name='gemini-3.1-pro-preview',
        system_instruction=INSTRUCAO_SISTEMA
    )


def criar_sessao_oraculo(gemini_files):
    """
    Cria uma sessão de chat com o Oráculo.
    Aceita um único gemini_file ou uma lista de gemini_files.

    Se o total de tokens exceder o limite (1M), tenta enviar os ficheiros
    um por um até encontrar o subconjunto que cabe na janela de contexto.
    Retorna (chat, ficheiros_carregados, ficheiros_excluidos).
    """
    if not isinstance(gemini_files, list):
        gemini_files = [gemini_files]

    model = _criar_modelo()

    # Tentativa 1: enviar todos de uma vez
    instrucao = (
        "Analisa estes documentos. A partir de agora, responde às minhas perguntas "
        "baseado apenas nas soluções de sucesso presentes aqui."
    )

    try:
        chat = model.start_chat()
        chat.send_message(gemini_files + [instrucao])
        return chat, list(range(len(gemini_files))), []
    except InvalidArgument:
        pass

    # Tentativa 2: enviar ficheiros um a um (cumulativo)
    chat = model.start_chat()
    carregados = []
    excluidos = []

    for i, gf in enumerate(gemini_files):
        try:
            if not carregados:
                # Primeiro ficheiro: envia com instrução
                chat.send_message([gf, instrucao])
            else:
                # Ficheiros adicionais: envia como contexto extra
                chat.send_message([gf, "Documento adicional para consulta."])
            carregados.append(i)
        except InvalidArgument:
            excluidos.append(i)

    if not carregados:
        raise ValueError(
            "Nenhum ficheiro cabe na janela de contexto do modelo (1M tokens). "
            "Tente ficheiros menores."
        )

    return chat, carregados, excluidos
