# Kali MCP Client

Network MCP **client** with an **LLM-powered agent**. Talk to the agent in a REPL; it calls tools on the Kali MCP server over Streamable HTTP.

## Prerequisites

- Python 3.10+
- Reachable Kali MCP server (`MCP_SERVER_URL`)
- One LLM backend:
  - **anthropic** — `ANTHROPIC_API_KEY`
  - **openai** — `OPENAI_API_KEY`
  - **gemini** — `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)
  - **mistral** — `MISTRAL_API_KEY`
  - **ollama** — local Ollama (`OLLAMA_HOST`, model pulled)

## Setup

```bash
cd client
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

| Variable | Meaning |
|----------|---------|
| `MCP_SERVER_URL` | e.g. `http://kali-host:8000/mcp` |
| `MCP_AUTH_TOKEN` | Must match server token |
| `LLM_PROVIDER` | `anthropic` \| `openai` \| `gemini` \| `mistral` \| `ollama` |
| `LLM_MODEL` | Model id for that provider |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` / `MISTRAL_API_KEY` | As needed |
| `OLLAMA_HOST` | Default `http://127.0.0.1:11434` |
| `MAX_AGENT_TURNS` | Max tool-calling loops per user message |

## Run

```bash
python -m kali_mcp_client
# or
python -m kali_mcp_client --server http://192.168.1.50:8000/mcp
```

### REPL commands

| Command | Action |
|---------|--------|
| `/tools` | Refresh and list MCP tools |
| `/reset` | Clear conversation history |
| `/quit` | Exit |

## How it works

1. Connect to the server and load tool schemas.
2. Send your message + tools to the configured LLM.
3. If the model requests tool calls, invoke them via MCP and feed results back.
4. Repeat until the model returns a final natural-language answer.

## Authorized use

The agent is instructed to refuse unauthorized targets, but **you** remain responsible for scope and legality.
