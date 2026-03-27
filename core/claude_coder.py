import os
import anthropic
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (.env)
load_dotenv()

def gerar_latex(resumo_extraido: str) -> str:
    """
    Recebe o resumo estruturado pelo Gemini e utiliza o Claude 3.5 Sonnet
    para gerar o código LaTeX correspondente.
    """
    try:
        # Inicializa o cliente da Anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        system_prompt = r"""
        Você é um autor técnico acadêmico e um mestre em formatação LaTeX.
        Sua tarefa é receber um resumo de passos de depuração de robótica (ROS 2) 
        e transformá-lo em um tutorial estruturado em LaTeX.
        
        REGRAS ESTritas:
        1. Gere APENAS código LaTeX válido. Não inclua conversas, introduções ou explicações fora do código LaTeX.
        2. Comece com \documentclass{article} e inclua pacotes essenciais (ex: listings, xcolor, hyperref, geometry).
        3. Estruture o documento com \section, \subsection e \textbf.
        4. Todos os comandos de terminal e códigos devem estar dentro de blocos \begin{lstlisting}[language=bash] ou python.
        5. Certifique-se de que o documento fecha com \end{document}.
        """
        
        user_prompt = f"Transforme o seguinte roteiro de solução no tutorial LaTeX completo:\n\n{resumo_extraido}"
        
        # Chamada ao Claude 3.5 Sonnet (SOTA para código e formatação)
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4000,
            temperature=0.2, # Baixa temperatura para manter a precisão do código
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Retorna apenas o texto gerado
        return response.content[0].text
        
    except Exception as e:
        return f"% Erro na camada de geracao (Claude): {e}"
