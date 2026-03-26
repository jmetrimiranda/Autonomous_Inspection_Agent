import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extrair_solucao(caminho_arquivo_md: str) -> str:
    """
    Lê o arquivo Markdown gigante e extrai a solução final validada.
    """
    try:
        with open(caminho_arquivo_md, 'r', encoding='utf-8') as f:
            documento = f.read()
            
        # Utilizamos o Gemini 1.5 Pro devido à janela de contexto massiva
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        prompt = f"""
        Você é um Engenheiro de Robótica Sênior analisando um extenso log de depuração.
        Sua tarefa é ler a transcrição abaixo e isolar APENAS a solução final que funcionou.
        
        REGRAS:
        1. Acompanhe a linha do tempo cronológica.
        2. Ignore todos os erros de compilação, pacotes quebrados e abordagens que foram abandonadas durante a conversa.
        3. Extraia o passo a passo definitivo, comandos de terminal validados e configurações (como ajustes de odometria ou AMCL) que resolveram o problema.
        4. Entregue um resumo técnico detalhado, direto ao ponto, em português.
        
        Transição de log para análise:
        {documento}
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Erro na camada de reasoning (Gemini): {e}"
