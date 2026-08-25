# Kali MCP Server

MCP server for **Kali Linux** — exposes pentest/DAST tools over **Streamable HTTP**. No LLM in this package.

**Package:** `kali-mcp-server` · **CLI:** `kali-mcp-server` · **Contact:** [neerajnarwal2000@gmail.com](mailto:neerajnarwal2000@gmail.com)

## Prerequisites

- Kali Linux (or Debian-based host with the tool binaries)
- Python 3.10+
- `git`, `python3-venv`, and `sudo` for package installs

## Setup from scratch

### 1. Clone the repo

```bash
git clone https://github.com/captainnarwal/Kali-MCP.git
cd Kali-MCP/server
```

### 2. Install Kali tool binaries

The server wraps system tools; it does not ship them.

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip git \
  nmap dirb gobuster nikto enum4linux wpscan \
  sqlmap hydra john metasploit-framework
```

```bash
which nmap gobuster nikto sqlmap
```

### 3. Install the Python package

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

This installs dependencies from `pyproject.toml` and registers the `kali-mcp-server` console script.

### 4. Configure environment

```bash
cp .env.example .env
nano .env   # or vim / code
```

| Variable | Meaning |
|----------|---------|
| `MCP_HOST` / `MCP_PORT` | Bind address (default `0.0.0.0:8000`) |
| `MCP_AUTH_TOKEN` | Shared secret; client sends `Authorization: Bearer …` |
| `MCP_ALLOWED_HOSTS` | Comma-separated Host values (LAN/WSL IP). Empty + `MCP_HOST=0.0.0.0` disables Host checks |
| `ALLOW_RAW` | `true` to enable `run_command` (default `false`) |
| `DEFAULT_TIMEOUT` | Subprocess timeout seconds (default `300`) |
| `LOG_DIR` / `LOG_LEVEL` / `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT` | Rotating logs → `server/logs/server.log` |
| `*_PATH` | Optional binary overrides (e.g. `NMAP_PATH`) |

**WSL / Windows client tip:** find the Kali/WSL IP with `hostname -I`, leave `MCP_ALLOWED_HOSTS` empty when binding `0.0.0.0` (or set it to that IP), and point the client at `http://<ip>:8000/mcp`.

### 5. Run

```bash
kali-mcp-server
# or: python -m kali_mcp_server
```

Endpoint: `http://<host>:8000/mcp`

```bash
curl -sS -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  http://<host>:8000/mcp
```

## MCP tools

| Tool | Description |
|------|-------------|
| `server_status` | Installed binaries + `ALLOW_RAW` |
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

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Binary 'nmap' not found` | `sudo apt install nmap` (or set `NMAP_PATH`) |
| `TOOL ERROR: … ALLOW_RAW` | Set `ALLOW_RAW=true` in `.env` and restart |
| HTTP 421 / Invalid Host header | Set `MCP_ALLOWED_HOSTS` or leave empty with `MCP_HOST=0.0.0.0` |
| HTTP 401 | Client `MCP_AUTH_TOKEN` must match server |

## Authorized use

Only against systems you are authorized to test. See the [root README](../README.md) and [SECURITY.md](../SECURITY.md).
