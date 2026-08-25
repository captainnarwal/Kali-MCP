# Kali MCP Server

MCP server that runs on **Kali Linux** and exposes pentest/DAST tools over **Streamable HTTP**. There is **no LLM** in this package.

## Prerequisites

- Python 3.10+
- Kali (or a host with the tool binaries installed)
- Optional packages as needed, for example:

```bash
sudo apt update
sudo apt install -y nmap dirb gobuster nikto enum4linux wpscan sqlmap hydra john metasploit-framework
```

## Setup

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

| Variable | Meaning |
|----------|---------|
| `MCP_HOST` / `MCP_PORT` | Bind address (default `0.0.0.0:8000`) |
| `MCP_AUTH_TOKEN` | Shared secret; client sends `Authorization: Bearer …` |
| `MCP_ALLOWED_HOSTS` | Comma-separated Host values to accept (LAN/WSL IP). Empty + `MCP_HOST=0.0.0.0` disables DNS-rebinding Host checks |
| `ALLOW_RAW` | `true` to enable `run_command` |
| `DEFAULT_TIMEOUT` | Subprocess timeout seconds (default `300`) |
| `*_PATH` | Optional override for each binary |

## Run

```bash
python -m kali_mcp_server
```

Endpoint: `http://<host>:8000/mcp`

Startup logs list which tool binaries were found on `PATH`.

## MCP tools

| Tool | Description |
|------|-------------|
| `nmap_scan` | Nmap |
| `dirb_scan` | Dirb |
| `gobuster_scan` | Gobuster |
| `nikto_scan` | Nikto |
| `enum4linux_scan` | enum4linux |
| `wpscan_scan` | WPScan |
| `sqlmap_scan` | sqlmap |
| `hydra_attack` | Hydra |
| `john_crack` | John the Ripper |
| `metasploit_run` | msfconsole via temp resource script |
| `run_command` | Raw shell (requires `ALLOW_RAW=true`) |

## Authorized use

Only use against systems you are authorized to test. See the root README warning.
