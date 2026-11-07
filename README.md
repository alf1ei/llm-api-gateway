# LLM API Gateway

[简体中文](#简体中文) | [English](#english)

## 简体中文

一个轻量级、多模型统一 API 网关。客户端使用统一的 OpenAI-compatible 接口，通过 `provider:model` 选择上游模型；网关负责鉴权、转发和记录基础用量。

### 功能
- OpenAI-compatible `POST /v1/chat/completions`
- `GET /v1/models` 列出已配置模型
- 多 Provider 配置：DeepSeek、OpenAI 或其他兼容接口
- 网关 Bearer Key 鉴权，上游密钥仅保存在服务端
- SQLite 请求记录：状态码、Token 用量、延迟
- Docker 与 GitHub Actions 测试工作流

### 快速开始
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env：设置 GATEWAY_API_KEY 和 PROVIDERS_JSON 中的上游密钥
uvicorn app.main:app --reload
```

访问 `http://localhost:8000/docs` 查看 API 文档。

### 调用示例
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer replace-with-a-long-random-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek:deepseek-chat",
    "messages": [{"role": "user", "content": "Explain API gateways briefly."}]
  }'
```

### 配置 Provider
`PROVIDERS_JSON` 是 JSON 对象。每个 Provider 至少需要 `base_url`、`api_key`，可选 `models`。模型名格式为 `provider:model-name`。不带前缀时使用 `default_provider`。

### 测试
```bash
pytest -q
```

### 部署
```bash
cp .env.example .env
# 编辑 .env 后：
docker compose up --build -d
```

生产环境请使用强随机网关密钥、HTTPS、反向代理和受限网络策略。当前版本是单实例 MVP，不包含用户/团队配额、流式转发、复杂计费或管理后台。

### 安全说明
- 不要提交 `.env` 或真实 API Key。
- 仅配置可信上游地址；不要把 Provider URL 暴露给不可信用户控制。
- 建议在公网部署前增加速率限制、IP allowlist、审计与密钥轮换。

## English

A lightweight multi-provider gateway exposing an OpenAI-compatible chat completions endpoint. Clients authenticate once against the gateway and select an upstream model with `provider:model`.

### Features
- OpenAI-compatible `POST /v1/chat/completions`
- Configured model discovery via `GET /v1/models`
- Multiple OpenAI-compatible upstream providers
- Gateway Bearer authentication; upstream keys remain server-side
- SQLite usage records for status, token counts, and latency
- Docker packaging and GitHub Actions CI

### Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set GATEWAY_API_KEY and upstream credentials in PROVIDERS_JSON
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`.

### Test and deploy
```bash
pytest -q
docker compose up --build -d
```

This is an MVP intended for trusted/private deployments. Streaming, quotas, billing, rate limiting, and a full admin UI are out of scope for this iteration.
