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
    Mantido para compatibilidade com chamadas de arquivo único.
    """
    return extrair_solucao_multi([caminho_arquivo])


def extrair_solucao_multi(caminhos_arquivos: list[str]) -> str:
    """
    Aceita uma lista de caminhos de arquivos, faz upload de todos
    para o Gemini e extrai a solução consolidada.
    """
    try:
        gemini_files = []
        for caminho in caminhos_arquivos:
            gf = genai.upload_file(path=caminho)
            # Aguarda cada ficheiro ficar pronto
            while gf.state.name == "PROCESSING":
                time.sleep(2)
                gf = genai.get_file(gf.name)
            if gf.state.name == "FAILED":
                return f"Erro: Falha ao processar o arquivo '{caminho}' no servidor do Gemini."
            gemini_files.append(gf)

        model = genai.GenerativeModel('gemini-3.1-pro-preview')

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

        INSTRUCAO_CRITICA = """
        LEMBRE-SE (REGRA DE OURO): Isole APENAS a solução final validada.
        Você deve ignorar absolutamente todas as tentativas falhas, erros de compilação, imagens de robôs com pose errada e pacotes quebrados que ocorreram na linha do tempo. Extraia apenas a vitória.
        """

        # Prompt sanduíche: instrução + todos os ficheiros + reforço
        prompt_sanduiche = [LOG_SOLVER_PROMPT] + gemini_files + [INSTRUCAO_CRITICA]

        response = model.generate_content(prompt_sanduiche)

        # Limpa os ficheiros do servidor
        for gf in gemini_files:
            genai.delete_file(gf.name)

        return response.text

    except Exception as e:
        return f"Erro na camada de reasoning (Gemini): {e}"
