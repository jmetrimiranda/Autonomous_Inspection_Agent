import os
import glob
import anthropic
from dotenv import load_dotenv

load_dotenv()


def _carregar_base_conhecimento(workspace_path: str) -> str:
    """Lê todos os ficheiros _distilled.md do workspace e concatena."""
    ficheiros = sorted(glob.glob(os.path.join(workspace_path, "*_distilled.md")))
    if not ficheiros:
        return ""

    partes = []
    for f in ficheiros:
        with open(f, "r", encoding="utf-8") as fh:
            partes.append(fh.read())

    return "\n\n---\n\n".join(partes)


def gerar_latex(workspace_path: str) -> str:
    """
    Lê a base de conhecimento destilada do workspace e gera
    um tutorial LaTeX formatado usando Claude Sonnet 4.
    """
    try:
        base = _carregar_base_conhecimento(workspace_path)
        if not base:
            return "% Erro: Nenhum conhecimento destilado encontrado no workspace."

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        system_prompt = r"""
        Você é um autor técnico acadêmico e um mestre em formatação LaTeX.
        Sua tarefa é receber uma base de conhecimento destilada sobre depuração de robótica (ROS 2)
        e transformá-la em um tutorial estruturado em LaTeX.

        REGRAS ESTRITAS:
        1. Gere APENAS código LaTeX válido. Não inclua conversas, introduções ou explicações fora do código LaTeX.
        2. Comece com \documentclass{article} e inclua pacotes essenciais (listings, xcolor, hyperref, geometry).
        3. Estruture o documento com \section, \subsection e \textbf.
        4. Inclua uma seção de Pré-requisitos ANTES da seção de solução.
        5. Todos os comandos de terminal e códigos devem estar dentro de blocos \begin{lstlisting}[language=bash] ou python.
        6. Certifique-se de que o documento fecha com \end{document}.
        """

        user_prompt = (
            "Transforme a seguinte base de conhecimento destilada no tutorial LaTeX completo:\n\n"
            f"{base}"
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    except Exception as e:
        return f"% Erro na camada de geracao (Claude): {e}"
