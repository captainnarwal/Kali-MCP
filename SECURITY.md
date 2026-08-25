# Security Policy

## Authorized use

Kali-MCP is for **authorized** penetration testing and DAST only. Use it only against systems you own or have explicit written permission to test.

## Reporting a vulnerability

If you find a security issue in this project (auth bypass, unsafe defaults, injection in tool wrappers, etc.), please email:

**neerajnarwal2000@gmail.com**

Please include:

- A short description of the issue
- Steps to reproduce (or a proof of concept)
- Affected component (`server` / `client`) and version / commit if known

Do **not** open a public GitHub issue for undisclosed vulnerabilities.

## Hardening checklist (operators)

- Set a strong `MCP_AUTH_TOKEN` on both server and client
- Keep `ALLOW_RAW=false` unless you truly need `run_command`
- Prefer VPN or TLS reverse proxy in front of the MCP HTTP endpoint
- Run the server on a dedicated Kali host with least privilege where practical
- Rotate tokens if they may have leaked
