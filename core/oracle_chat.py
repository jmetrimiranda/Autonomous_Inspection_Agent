import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def criar_sessao_oraculo(gemini_file):
    instrucao_sistema = """
    És o 'Oráculo', um Engenheiro Robótico de Elite e Assistente de Investigação.
    A sua ÚNICA fonte de conhecimento para esta conversa é o documento de registo/conversa fornecido.
    
    REGRA DE OURO: Quando o utilizador fizer uma pergunta, deves procurar no documento a solução que FUNCIONOU. 
    Ignora absolutamente todas as tentativas falhadas, erros de compilação, ou caminhos que não deram em nada.
    Se a resposta não estiver no documento, diz simplesmente que não tens essa informação no contexto fornecido.
    """
    
    model = genai.GenerativeModel(
        model_name='gemini-3.1-pro-preview',
        system_instruction=instrucao_sistema
    )
    
    # Inicia o chat de forma segura (vazio)
    chat = model.start_chat()
    
    # Envia o arquivo e o comando como a primeira mensagem invisível
    chat.send_message([gemini_file, "Analisa este documento. A partir de agora, responde às minhas perguntas baseado apenas nas soluções de sucesso presentes aqui."])
    
    return chat
