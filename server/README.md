# Kali MCP Server

MCP server that runs on **Kali Linux** and exposes pentest/DAST tools over **Streamable HTTP**. There is **no LLM** in this package.

## Prerequisites

- Kali Linux (or a Debian-based host with the tool binaries)
- Python 3.10+
- `git`, `python3-venv`, and `sudo` for package installs

## Setup from scratch

### 1. Clone the repo

```bash
git clone https://github.com/captainnarwal/Kali-MCP.git
cd Kali-MCP
git checkout dev   # optional: use the development branch
```

### 2. Install Kali tool binaries

The server wraps system tools; it does not ship them. Install what you need:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip git \
  nmap dirb gobuster nikto enum4linux wpscan \
  sqlmap hydra john metasploit-framework
```

Confirm binaries are on `PATH` (example):

```bash
which nmap gobuster nikto sqlmap
```

### 3. Create the Python environment

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
nano .env   # or vim / code
```

Set at least:

| Variable | Meaning |
|----------|---------|
| `MCP_HOST` / `MCP_PORT` | Bind address (default `0.0.0.0:8000`) |
| `MCP_AUTH_TOKEN` | Shared secret; client sends `Authorization: Bearer …` |
| `MCP_ALLOWED_HOSTS` | Comma-separated Host values to accept (LAN/WSL IP). Empty + `MCP_HOST=0.0.0.0` disables DNS-rebinding Host checks |
| `ALLOW_RAW` | `true` to enable `run_command` (default `false`) |
| `DEFAULT_TIMEOUT` | Subprocess timeout seconds (default `300`) |
| `LOG_DIR` / `LOG_LEVEL` / `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT` | Rotating file logs under `server/logs/server.log` by default |
| `*_PATH` | Optional override for each binary (e.g. `NMAP_PATH`) |

**WSL / Windows client tip:** find your Kali/WSL IP with `hostname -I` or `ip addr`, then either leave `MCP_ALLOWED_HOSTS` empty when binding `0.0.0.0`, or set it to that IP. Point the client `MCP_SERVER_URL` at `http://<that-ip>:8000/mcp`.

### 5. Run the server

```bash
source .venv/bin/activate
python -m kali_mcp_server
```

Endpoint: `http://<host>:8000/mcp`

On startup the server logs which tool binaries were found and writes rotating logs to `server/logs/server.log`.

Quick health check from another machine (replace token and host):

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
| HTTP 421 / Invalid Host header | Set `MCP_ALLOWED_HOSTS` to the client-facing IP, or leave empty with `MCP_HOST=0.0.0.0` |
| HTTP 401 | Client `MCP_AUTH_TOKEN` must match server |

## Authorized use

Only use against systems you are authorized to test. See the root README warning.
