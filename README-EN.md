<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

<em>A Simple and Universal Swarm Intelligence Engine, Predicting Anything</em>

[English](./README-EN.md) | [한국어](./README.md)

</div>

## Overview

**MiroFish** is a next-generation AI prediction engine powered by multi-agent technology. By extracting seed information from the real world (such as breaking news, policy drafts, or financial signals), it automatically constructs a high-fidelity parallel digital world. Within this space, thousands of intelligent agents with independent personalities, long-term memory, and behavioral logic freely interact and undergo social evolution.

> You only need to: Upload seed materials and describe your prediction requirements in natural language.
> MiroFish will return: A detailed prediction report and a deeply interactive high-fidelity digital world.

This fork includes the following enhancements:
- **Bilingual UI (English / Korean)** with language switcher
- **All prompts translated to English** (removed Chinese-only dependencies)
- **Local LLM support via vLLM** (tested with Qwen3-32B on NVIDIA H100)
- **Language-aware LLM prompts** — personas, reports, and conversations adapt to selected language

## Workflow

1. **Graph Building**: Seed extraction & GraphRAG construction via Zep Cloud
2. **Environment Setup**: Entity extraction & Persona generation & Agent configuration
3. **Simulation**: Dual-platform parallel simulation (Twitter + Reddit)
4. **Report Generation**: ReportAgent with rich toolset for deep analysis
5. **Deep Interaction**: Chat with any agent in the simulated world

## Quick Start

### Prerequisites

| Tool | Version | Description | Check |
|------|---------|-------------|-------|
| **Node.js** | 18+ | Frontend runtime | `node -v` |
| **Python** | 3.11~3.12 | Backend runtime | `python --version` |
| **uv** | Latest | Python package manager | `uv --version` |

### 1. Configure Environment Variables

```bash
cp .env.example .env
```

**Required:**

```env
# LLM API Configuration (OpenAI-compatible format)
# Option A: Cloud API (e.g., Alibaba Qwen-plus)
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Option B: Local vLLM server (e.g., Qwen3-32B)
LLM_API_KEY=dummy
LLM_BASE_URL=http://<gpu-server-ip>:8001/v1
LLM_MODEL_NAME=Qwen/Qwen3-32B

# Zep Cloud (free tier available)
ZEP_API_KEY=your_zep_api_key
```

### 2. Install Dependencies

```bash
npm run setup:all
```

### 3. Start Services

```bash
npm run dev
```

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

### 4. (Optional) Local LLM with vLLM

For running Qwen3-32B locally on NVIDIA H100:

```bash
# Install vLLM in a virtual environment
python3 -m venv ~/vllm-env
~/vllm-env/bin/pip install vllm

# Start serving (single GPU, BF16)
~/vllm-env/bin/python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-32B \
  --port 8001 \
  --host 0.0.0.0
```

Then set `LLM_BASE_URL=http://<gpu-server-ip>:8001/v1` in `.env`.

### Docker Deployment

```bash
cp .env.example .env
docker compose up -d
```

## Bilingual Support (i18n)

This fork supports **English** and **Korean** with a single click:

- Click **EN | KO** toggle in the navigation bar
- UI labels, status messages, and all text switch instantly
- LLM-generated content (personas, conversations, reports) follows the selected language
- Language preference is persisted in browser localStorage

See [docs/I18N_PLAN.md](docs/I18N_PLAN.md) for implementation details.

## Project Documentation

| Document | Description |
|----------|-------------|
| [docs/ANALYSIS.md](docs/ANALYSIS.md) | Source code analysis (backend + frontend) |
| [docs/I18N_PLAN.md](docs/I18N_PLAN.md) | Internationalization implementation plan |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3, Vite, D3.js, Axios |
| Backend | Flask, Python 3.12 |
| LLM | OpenAI-compatible API (vLLM / Qwen / etc.) |
| Knowledge Graph | Zep Cloud |
| Simulation Engine | OASIS (CAMEL-AI) |

## Acknowledgments

- **[MiroFish](https://github.com/666ghj/MiroFish)** — Original project by Guo Hangjiang
- **[OASIS](https://github.com/camel-ai/oasis)** — Simulation engine by CAMEL-AI
- **[Zep](https://www.getzep.com/)** — Memory and knowledge graph platform

## License

AGPL-3.0
