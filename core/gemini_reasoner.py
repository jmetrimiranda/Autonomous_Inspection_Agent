import google.generativeai as genai
import os
import time
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extrair_solucao(caminho_arquivo: str) -> str:
    """
    Faz o upload do arquivo para o Gemini e extrai a solução usando
    técnicas de Prompt Sanduíche e ARC-style reasoning (Roleplay + CoT).
    """
    try:
        # SOTA: Usa a File API do Gemini (Aceita PDFs massivos e lê as imagens/textos nativamente)
        gemini_file = genai.upload_file(path=caminho_arquivo)
        
        # Aguarda o modelo processar o documento (importante para PDFs muito grandes)
        while gemini_file.state.name == "PROCESSING":
            time.sleep(2)
            gemini_file = genai.get_file(gemini_file.name)
            
        if gemini_file.state.name == "FAILED":
            return "Erro: Falha ao processar o arquivo no servidor do Gemini."

        # Instancia o modelo de contexto massivo
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # O Pão de Cima: Instrução ARC-Style (Roleplay e Passos Lógicos)
        LOG_SOLVER_PROMPT = """
        Você é um Engenheiro Sênior de Robótica e especialista em depuração de sistemas ROS 2 (Navigation2, AMCL, Odometria). 
        Sua tarefa é analisar logs de terminal brutos, históricos de conversa iterativos e imagens associadas para extrair estritamente a *solução final validada* que resolveu o problema do robô.

        Siga este processo iterativo:

        **1. Analise a Linha do Tempo (Timeline Analysis):**
          * Identifique o problema central que o usuário está tentando resolver no início do log.
          * Mapeie cronologicamente as tentativas feitas. Identifique erros de compilação, pacotes ausentes ou configurações que falharam.
          * Encontre o ponto de inflexão: o momento exato no log onde a solução deu certo.

        **2. Formule a Solução Definitiva (Hypothesis Extraction):**
          * Isole apenas os passos, comandos de terminal e blocos de código que fazem parte da tentativa bem-sucedida.
          * Descarte ABSOLUTAMENTE tudo o que foi tentado e falhou antes desse ponto.

        **3. Formatação da Saída (Output Requirements):**
          * Forneça uma breve explicação da solução final encontrada.
          * Liste o passo a passo definitivo de forma clara.
          * Inclua scripts ou comandos essenciais em blocos de código Markdown.
        """

        # O Pão de Baixo: Reforço da Regra Crítica para evitar o "Lost in the Middle"
        INSTRUCAO_CRITICA = """
        LEMBRE-SE (REGRA DE OURO): Isole APENAS a solução final validada. 
        Você deve ignorar absolutamente todas as tentativas falhas, erros de compilação, imagens de robôs com pose errada e pacotes quebrados que ocorreram na linha do tempo. Extraia apenas a vitória.
        """
        
        # Montagem do Prompt Sanduíche (Passamos a lista de conteúdos para o modelo)
        prompt_sanduiche = [
            LOG_SOLVER_PROMPT,
            gemini_file, # O arquivo (PDF/MD) entra como o 'recheio' da requisição
            INSTRUCAO_CRITICA
        ]
        
        # Geração da resposta
        response = model.generate_content(prompt_sanduiche)
        
        # Boas práticas: deletar o arquivo do servidor do Google após o uso
        genai.delete_file(gemini_file.name)
        
        return response.text
        
    except Exception as e:
        return f"Erro na camada de reasoning (Gemini): {e}"