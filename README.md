# 🤖 Log2Tex: Agentic LLM Pipeline for SOTA Debug-to-Tutorial Conversion

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![Gemini Pro](https://img.shields.io/badge/Gemini-1.5_Pro-orange)
![Claude Sonnet](https://img.shields.io/badge/Claude-3.5_Sonnet-purple)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B)
![License](https://img.shields.io/badge/license-MIT-green)

![Log2Tex Banner Image](docs/images/banner_placeholder.png)

**Log2Tex** is a state-of-the-art, dual-LLM agentic pipeline designed to process massive, noisy debugging logs and autonomously generate beautifully formatted academic tutorials in LaTeX. 

By leveraging **LLM Chaining**, this tool combines the massive context-window reasoning capabilities of **Google Gemini 1.5 Pro** with the superior coding and syntax generation skills of **Anthropic Claude 3.5 Sonnet**.

---

## ✨ Key Features

* 🧠 **Massive Context Reasoning:** Processes up to 1M+ tokens of raw chat history and debug logs in a single shot using Gemini 1.5 Pro. It understands chronological timelines, filtering out dead-ends, failed compilations, and irrelevant tangents.
* ✍️ **Flawless LaTeX Generation:** Offloads the structured formatting task to Claude 3.5 Sonnet, known for its SOTA coding capabilities, ensuring the final `.tex` output compiles perfectly with `\section`, `\begin{lstlisting}`, and academic formatting.
* 🎯 **Agentic Filtering:** Extracts *only* the final, validated solution from complex iterative debugging sessions.
* 🖥️ **Interactive UI:** A clean, responsive Streamlit interface for uploading `.md` files, visualizing the reasoning process, and downloading the final LaTeX code.

---

## 🏗️ Architecture

![Architecture Diagram](docs/images/architecture_diagram.png)

1.  **Input:** User uploads a raw Markdown file containing the entire debugging session (e.g., terminal outputs, iterative code fixes).
2.  **Reasoning Node (Gemini):** Analyzes the timeline. Identifies the core problem, maps the failed attempts, and extracts the definitive working solution into a concise text summary.
3.  **Formatting Node (Claude):** Takes the distilled solution and writes a comprehensive, textbook-style tutorial strictly using LaTeX syntax.
4.  **Output:** Rendered LaTeX code ready for Overleaf or local compilation.

---

## 🚀 Ideal Use Case (Robotics & AI)

Perfect for researchers and engineers dealing with extensive hardware or software troubleshooting. 

**Example Scenario:** You spend days debugging autonomous navigation, AMCL configurations, and odometry issues on a **Unitree Go2** robot using ROS 2. You end up with a 1200-page debugging log. Instead of manually writing your documentation, Log2Tex ingests the entire history, ignores the failed package builds, extracts the exact working configuration, and outputs a ready-to-publish academic tutorial.

---

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/log2tex-agent.git](https://github.com/yourusername/log2tex-agent.git)
cd log2tex-agent
