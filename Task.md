Tarefa: Refatoração da Interface do Usuário para Padrão SOTA (State-of-the-Art)
Contexto do Projeto
Estamos construindo um Agente de Inspeção Autônomo que analisa logs de robótica. Atualmente, a lógica de backend (conexão com Gemini 3.1 Pro e Claude Sonnet 4-6) funciona perfeitamente, mas a interface do usuário Streamlit está rudimentar, pouco interativa e visualmente pobre.

Objetivo
Refatorar o arquivo app.py e criar arquivos de configuração de tema para transformar a aplicação numa plataforma visualmente comparável ao ChatGPT ou Claude.ai.

Requisitos Visuais & UX (SOTA)
Paleta de Cores Profissional (Dark Mode SOTA):

Adotar uma paleta inspirada em "Slate" ou "Zinc" (padrão Tailwind CSS).

Fundo Principal: Dark Gray/Blue (ex: Slate 950).

Cor de Destaque (Accent): Emerald ou Indigo para botões.

Crie o arquivo .streamlit/config.toml com as configurações de tema apropriadas.

Layout Moderno:

Sidebar: Usar a sidebar para o uploader de arquivo e um botão claro de "Limpar Chat / Novo Arquivo".

Área Principal: Manter os separadores (Tabs) "Gerador LaTeX" e "Chat com Oráculo".

Chat (Oráculo): O input do chat (st.chat_input) deve ficar fixo no rodapé da página.

Interatividade & Efeitos (O "Tcham" da IA):

Substitua st.spinner por st.status (containers de progresso animados) para as etapas de upload e conexão com a API.

Efeito Typewriter (Streaming Simulator): Quando o Oráculo responder, crie uma função no Python que simule a escrita (palavra por palavra com um pequeno time.sleep), para dar feedback visual de que a IA está "digitando", semelhante ao ChatGPT.

Código Base e Integração
Certifique-se de manter as importações vitais e as chamadas para o nosso backend atualizadas:

from core.gemini_reasoner import extrair_solucao

from core.claude_coder import gerar_latex

from core.oracle_chat import criar_sessao_oraculo

Manter a lógica de uso do genai.upload_file() e o laço de espera PROCESSING.