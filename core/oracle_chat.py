import google.generativeai as genai
from google.generativeai import caching
import datetime
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

NOME_MODELO = "models/gemini-3.1-pro-preview"

INSTRUCAO_SISTEMA = """
És o 'Oráculo', um Engenheiro Robótico de Elite e Assistente de Investigação.
A sua ÚNICA fonte de conhecimento para esta conversa são os documentos de registo/conversa fornecidos.

REGRA DE OURO: Quando o utilizador fizer uma pergunta, deves procurar nos documentos a solução que FUNCIONOU.
Ignora absolutamente todas as tentativas falhadas, erros de compilação, ou caminhos que não deram em nada.
Se a resposta não estiver nos documentos, diz simplesmente que não tens essa informação no contexto fornecido.
"""


def criar_sessao_oraculo(gemini_files):
    """
    Cria uma sessão de chat com o Oráculo usando Context Caching.

    Os ficheiros massivos são armazenados no cache server-side do Gemini,
    permitindo que TODO o contexto (PDF + MD + TXT) esteja disponível
    simultaneamente sem estourar o limite de tokens na requisição de chat.

    Retorna (chat, cache) — o cache pode ser deletado quando a sessão acabar.
    """
    if not isinstance(gemini_files, list):
        gemini_files = [gemini_files]

    # Cria o cache server-side com todos os documentos
    cache = caching.CachedContent.create(
        model=NOME_MODELO,
        system_instruction=INSTRUCAO_SISTEMA,
        contents=gemini_files,
        ttl=datetime.timedelta(minutes=60),
    )

    # Instancia o modelo apontando para o cache (contexto pré-carregado)
    model = genai.GenerativeModel.from_cached_content(cached_content=cache)

    # O chat inicia limpo — os documentos já estão no cache, não na mensagem
    chat = model.start_chat()

    return chat, cache


def deletar_cache(cache):
    """Remove o cache do servidor para liberar recursos."""
    try:
        caching.CachedContent.delete(cache.name)
    except Exception:
        pass
