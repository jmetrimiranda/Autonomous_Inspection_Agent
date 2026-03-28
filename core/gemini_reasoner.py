import google.generativeai as genai
import os
import time
import re
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

NOME_MODELO = "gemini-3.1-pro-preview"

PROMPT_DESTILACAO = """
Você é um Engenheiro de Dados Robóticos de elite.
Sua tarefa é ler este log bruto e caótico de depuração (pode conter conversas iterativas,
erros de compilação, tentativas falhas e ruído) e produzir um documento de conhecimento
destilado em Markdown com APENAS o que funcionou.

O documento de saída DEVE conter EXATAMENTE estas seções, nesta ordem:

## Resumo do Problema
Descreva em 2-3 frases o problema central que estava sendo resolvido.

## Condições e Pré-requisitos Obrigatórios
Liste TODAS as condições que precisam estar satisfeitas ANTES de aplicar a solução:
- Sistema operacional e versão (ex: Ubuntu 20.04)
- Distribuição ROS e versão (ex: ROS 2 Foxy)
- Pacotes/dependências específicos necessários
- Configurações de hardware (se mencionadas)
- Variáveis de ambiente ou sourcings necessários
Se alguma informação não estiver explícita no log, DEDUZA a partir dos comandos e erros observados.

## Golden Path — Passo a Passo da Solução Validada
Liste APENAS os passos, comandos de terminal e scripts que fazem parte da solução
que FUNCIONOU no final. Use blocos de código Markdown para cada comando.
Ignore ABSOLUTAMENTE tudo o que foi tentado e falhou.

## Notas e Observações
Qualquer detalhe adicional relevante que possa ajudar na replicação futura.
"""

INSTRUCAO_CRITICA = """
REGRA DE OURO: Extraia APENAS a vitória. Descarte todo o ruído, tentativas falhas,
erros de compilação e caminhos sem saída. O objetivo é criar um documento limpo
que qualquer engenheiro possa seguir do zero para replicar a solução.
"""


def destilar_log_bruto(caminho_arquivo_temporario: str, workspace_path: str) -> str:
    """
    Faz upload do arquivo bruto para a File API do Google, usa o Gemini
    para destilar o Golden Path, e salva o resultado como _distilled.md
    na pasta do workspace.

    Retorna o caminho do ficheiro destilado salvo.
    """
    # Upload para a File API
    gemini_file = genai.upload_file(path=caminho_arquivo_temporario)

    # Aguarda processamento
    while gemini_file.state.name == "PROCESSING":
        time.sleep(2)
        gemini_file = genai.get_file(gemini_file.name)

    if gemini_file.state.name == "FAILED":
        raise RuntimeError(f"Falha ao processar o arquivo no servidor do Gemini.")

    model = genai.GenerativeModel(NOME_MODELO)

    # Prompt sanduíche: instrução + ficheiro + reforço
    response = model.generate_content([PROMPT_DESTILACAO, gemini_file, INSTRUCAO_CRITICA])

    # Limpa o ficheiro do servidor do Google
    genai.delete_file(gemini_file.name)

    # Gera nome do ficheiro destilado
    nome_original = os.path.basename(caminho_arquivo_temporario)
    nome_base = os.path.splitext(nome_original)[0]
    # Sanitiza o nome para filesystem
    nome_safe = re.sub(r'[^\w\-.]', '_', nome_base)[:80]
    nome_destilado = f"{nome_safe}_distilled.md"
    caminho_destilado = os.path.join(workspace_path, nome_destilado)

    os.makedirs(workspace_path, exist_ok=True)
    with open(caminho_destilado, "w", encoding="utf-8") as f:
        f.write(response.text)

    return caminho_destilado
