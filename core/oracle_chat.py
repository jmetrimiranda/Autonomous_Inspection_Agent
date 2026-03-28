import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def criar_sessao_oraculo(gemini_files):
    """
    Cria uma sessão de chat com o Oráculo.
    Aceita um único gemini_file ou uma lista de gemini_files.
    """
    if not isinstance(gemini_files, list):
        gemini_files = [gemini_files]

    instrucao_sistema = """
    És o 'Oráculo', um Engenheiro Robótico de Elite e Assistente de Investigação.
    A sua ÚNICA fonte de conhecimento para esta conversa são os documentos de registo/conversa fornecidos.

    REGRA DE OURO: Quando o utilizador fizer uma pergunta, deves procurar nos documentos a solução que FUNCIONOU.
    Ignora absolutamente todas as tentativas falhadas, erros de compilação, ou caminhos que não deram em nada.
    Se a resposta não estiver nos documentos, diz simplesmente que não tens essa informação no contexto fornecido.
    """

    model = genai.GenerativeModel(
        model_name='gemini-3.1-pro-preview',
        system_instruction=instrucao_sistema
    )

    chat = model.start_chat()

    # Envia todos os ficheiros + instrução como primeira mensagem
    primeira_mensagem = gemini_files + [
        "Analisa estes documentos. A partir de agora, responde às minhas perguntas "
        "baseado apenas nas soluções de sucesso presentes aqui."
    ]
    chat.send_message(primeira_mensagem)

    return chat
