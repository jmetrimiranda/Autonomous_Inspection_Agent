import google.generativeai as genai
import os
import time
import re
import tempfile
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

NOME_MODELO = "gemini-3.1-pro-preview"

# Limiar para activar chunking (3M caracteres ≈ 750k tokens)
LIMIAR_CHUNKING = 3_000_000
TAMANHO_CHUNK = 2_500_000
OVERLAP = 200_000

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

PROMPT_FUSAO = """
Abaixo estão partes destiladas cronologicamente de uma longa sessão de depuração robótica.
Devido à divisão do ficheiro original em blocos com sobreposição, pode haver passos
duplicados ou informação repetida nas emendas entre partes.

A sua tarefa é atuar como um Reconstrutor de Knowledge Graph: funda todas estas partes
num ÚNICO tutorial coerente em Markdown.

Regras ESTRITAS:
1. Agrupe TODOS os pré-requisitos de sistema encontrados num único bloco no topo.
2. Remova passos duplicados (que aparecem por causa do overlap entre chunks).
3. Mantenha a ordem cronológica estrita do Golden Path (comandos que deram sucesso).
4. Explique as dependências entre os passos, se houver.
5. O documento final DEVE seguir EXATAMENTE esta estrutura:
   ## Resumo do Problema
   ## Condições e Pré-requisitos Obrigatórios
   ## Golden Path — Passo a Passo da Solução Validada
   ## Notas e Observações

PARTES DESTILADAS:
"""


def _nome_destilado(caminho_arquivo_temporario: str, workspace_path: str) -> str:
    """Gera o caminho do ficheiro destilado a partir do nome original."""
    nome_original = os.path.basename(caminho_arquivo_temporario)
    nome_base = os.path.splitext(nome_original)[0]
    nome_safe = re.sub(r'[^\w\-.]', '_', nome_base)[:80]
    return os.path.join(workspace_path, f"{nome_safe}_distilled.md")


def _upload_e_destilar(caminho_ficheiro: str) -> str:
    """Upload para File API + destilação com prompt sanduíche. Retorna texto destilado."""
    gemini_file = genai.upload_file(path=caminho_ficheiro)

    while gemini_file.state.name == "PROCESSING":
        time.sleep(2)
        gemini_file = genai.get_file(gemini_file.name)

    if gemini_file.state.name == "FAILED":
        raise RuntimeError("Falha ao processar o ficheiro no servidor do Gemini.")

    model = genai.GenerativeModel(NOME_MODELO)
    response = model.generate_content([PROMPT_DESTILACAO, gemini_file, INSTRUCAO_CRITICA])

    genai.delete_file(gemini_file.name)
    return response.text


def _precisa_chunking(caminho: str) -> bool:
    """Verifica se o ficheiro de texto excede o limiar para chunking."""
    ext = os.path.splitext(caminho)[1].lower()
    if ext not in (".md", ".txt"):
        return False
    return os.path.getsize(caminho) > LIMIAR_CHUNKING


def _dividir_em_chunks(texto: str) -> list[str]:
    """Divide o texto em chunks com overlap (janela deslizante)."""
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fim = inicio + TAMANHO_CHUNK
        chunks.append(texto[inicio:fim])
        # Avança com overlap
        inicio = fim - OVERLAP
        # Se o que sobra for menor que o overlap, já foi capturado
        if inicio + OVERLAP >= len(texto):
            break
    return chunks


def _fusao_reduce(resumos_parciais: list[str]) -> str:
    """Fase Reduce: funde resumos parciais num único documento coerente."""
    texto_parciais = ""
    for i, resumo in enumerate(resumos_parciais, 1):
        texto_parciais += f"\n\n--- PARTE {i} DE {len(resumos_parciais)} ---\n\n{resumo}"

    model = genai.GenerativeModel(NOME_MODELO)
    response = model.generate_content(PROMPT_FUSAO + texto_parciais)
    return response.text


def destilar_log_bruto(caminho_arquivo_temporario: str, workspace_path: str,
                       callback=None) -> str:
    """
    Destila um log bruto para Golden Path.

    Para ficheiros de texto gigantes (>3M chars), usa Map-Reduce:
    1. Divide em chunks com overlap
    2. Destila cada chunk individualmente (Map)
    3. Funde os resumos num documento coerente (Reduce)

    Para ficheiros normais ou PDFs, usa destilação directa via File API.

    callback: função opcional callback(msg: str) para reportar progresso.
    Retorna o caminho do ficheiro destilado salvo.
    """
    def _log(msg):
        if callback:
            callback(msg)

    os.makedirs(workspace_path, exist_ok=True)
    caminho_destilado = _nome_destilado(caminho_arquivo_temporario, workspace_path)

    # ── Verifica se precisa de chunking ──
    if _precisa_chunking(caminho_arquivo_temporario):
        _log("📊 Ficheiro gigante detetado. Iniciando destilação recursiva (Map-Reduce)...")

        with open(caminho_arquivo_temporario, "r", encoding="utf-8", errors="replace") as f:
            texto_completo = f.read()

        chunks = _dividir_em_chunks(texto_completo)
        _log(f"✂️ Dividido em {len(chunks)} chunk(s) com overlap de {OVERLAP // 1000}k caracteres.")

        # ── Fase Map: destilar cada chunk ──
        resumos_parciais = []
        chunks_falhados = []

        for i, chunk in enumerate(chunks, 1):
            _log(f"🧠 Map {i}/{len(chunks)} — Destilando chunk ({len(chunk):,} chars)...")

            # Salva chunk como ficheiro temporário
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".md", encoding="utf-8"
            ) as tmp:
                tmp.write(chunk)
                tmp_chunk_path = tmp.name

            try:
                resumo = _upload_e_destilar(tmp_chunk_path)
                resumos_parciais.append(resumo)
                _log(f"✅ Map {i}/{len(chunks)} — Chunk destilado com sucesso.")
            except Exception as e:
                chunks_falhados.append(i)
                _log(f"⚠️ Map {i}/{len(chunks)} — Falha: {e}")
            finally:
                if os.path.exists(tmp_chunk_path):
                    os.remove(tmp_chunk_path)

        if not resumos_parciais:
            raise RuntimeError(
                f"Todos os {len(chunks)} chunks falharam na destilação. "
                "Verifique a conectividade com a API do Gemini."
            )

        if chunks_falhados:
            _log(f"⚠️ {len(chunks_falhados)} chunk(s) falharam: {chunks_falhados}. "
                 "O resultado pode estar incompleto.")

        # ── Fase Reduce: fundir resumos ──
        if len(resumos_parciais) == 1:
            texto_final = resumos_parciais[0]
        else:
            _log(f"🔗 Reduce — Fundindo {len(resumos_parciais)} resumos parciais...")
            texto_final = _fusao_reduce(resumos_parciais)
            _log("✅ Fusão completa.")

    else:
        # ── Destilação directa (ficheiro normal / PDF) ──
        _log("🧠 Destilando via File API (ficheiro directo)...")
        texto_final = _upload_e_destilar(caminho_arquivo_temporario)

    # ── Persistência ──
    with open(caminho_destilado, "w", encoding="utf-8") as f:
        f.write(texto_final)

    return caminho_destilado
