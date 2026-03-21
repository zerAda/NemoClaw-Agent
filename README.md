# NemoClaw-Agent 🦀

### Standalone AI Agentic Router
NemoClaw is a high-performance AI agentic router designed for autonomous customer interaction, leveraging **NVIDIA NIM** cloud inference and local sandboxed execution.

---

## 🚀 Key Features
- **Omnichannel Routing**: Seamlessly handles Telegram, WhatsApp, and> [!IMPORTANT]
> - **NVIDIA NIM Model**: We will use `meta/llama-3.3-70b-instruct` (latest high-performance engine).
> - **Standalone Mode**: Confirmed that NemoClaw has NO dependency on the Ralphé ecosystem.
- **OpenShell Sandbox**: Safely executes dynamic tool-calling and code generation.
- **Green-Ops CI/CD**: Standalone GitHub Actions for continuous linting, security scanning (`bandit`), and zero-downtime VPS deployment.

## 🛠 Tech Stack
- **Engine**: Python 3.11+
- **Inference**: NVIDIA NIM (Llama-3 / Mixtral)
- **Infrastructure**: Docker Compose, Traefik
- **Communication**: Telegram Bot API

## 📦 Deployment
NemoClaw is containerized and deploys automatically to the target VPS via the `CD - Deploy to VPS` workflow.

```bash
# Local development
docker compose up -d
```

## 🛡 Security & Quality
- **Linter**: Flake8
- **SAST**: Bandit
- **Registry**: GitHub Container Registry (GHCR)

---
*Part of the Resto-Bot Ecosystem • Managed by GSD Method.*
