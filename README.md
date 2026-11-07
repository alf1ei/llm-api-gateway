# LLM API Gateway

[简体中文](#简体中文) · [English](#english)

A self-hosted, OpenAI-compatible gateway for routing chat-completion requests to multiple configured model providers. One client key, server-side provider credentials, model allowlists, and SQLite usage records.

## 简体中文

### 当前能力
- 统一接口：`POST /v1/chat/completions`，兼容 OpenAI Chat Completions 请求结构
- 模型发现：`GET /v1/models`，使用 `provider:model` 指定上游
- 多供应商：DeepSeek、OpenAI 及其他兼容 OpenAI API 的服务
- 网关 Bearer Key 鉴权，恒定时间比较；未配置强密钥时拒绝服务
- Provider 模型白名单，避免客户端任意请求未配置模型
- 上游超时、网络错误和非 JSON 响应的安全处理
- 复用异步 HTTP 连接池；记录状态码、Token 用量和延迟
- SQLite 使用记录：`GET /admin/usage?limit=100`
- Docker Compose、OpenAPI 文档、Python 3.11–3.13 CI

### 快速开始
要求 Python 3.11+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

编辑 `.env`，设置随机网关密钥和上游凭据：

```dotenv
GATEWAY_API_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:///./gateway.db
REQUEST_TIMEOUT=60
PROVIDERS_JSON={"default_provider":"deepseek","deepseek":{"base_url":"https://api.deepseek.com/v1","api_key":"YOUR_DEEPSEEK_KEY","models":["deepseek-chat"]}}
```

启动：`uvicorn app.main:app --host 127.0.0.1 --port 8000`

- 健康检查：`GET /health`
- API 文档：`/docs`

### 请求示例
```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek:deepseek-chat","messages":[{"role":"user","content":"你好"}]}'
```

不带 `provider:` 前缀时使用 `default_provider`。Provider 配置了 `models` 白名单时，只允许调用白名单内的模型。

### API
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | 健康检查 |
| GET | `/v1/models` | Yes | 已配置模型列表 |
| POST | `/v1/chat/completions` | Yes | 转发聊天请求 |
| GET | `/admin/usage?limit=100` | Yes | 最近用量记录，limit 为 1–1000 |
| GET | `/docs` | No | OpenAPI / Swagger UI |

### Docker 部署
```bash
cp .env.example .env
# 编辑 .env 后
docker compose up --build -d
```

默认监听 8000，数据库持久化到 Docker volume。建议将服务放在 HTTPS 反向代理之后，不要直接将管理接口暴露到公网。

### 安全边界与限制
- Provider URL 只能来自服务端配置；仅允许 HTTPS（本机回环地址可使用 HTTP），并拒绝私有/保留 IP，降低 SSRF 风险。
- 不要提交 `.env`、上游密钥或真实用户请求日志。
- 当前是单网关密钥、单实例 MVP；尚无多租户、用户配额、计费、流式 SSE、自动故障切换或完整管理 UI。
- SQLite 适用于单实例和轻量使用；高并发/多副本部署应迁移到 PostgreSQL，并补充分布式限流与租户隔离。
- 模型输出和上游错误仍应由调用方按业务需要校验。

### 测试
```bash
pytest -q
python -m compileall -q app tests
```

## English

### Features
- OpenAI-compatible `POST /v1/chat/completions` and authenticated `GET /v1/models`
- Multiple configured upstream providers selected with `provider:model`
- Gateway Bearer authentication with constant-time key comparison
- Optional per-provider model allowlists
- Reused async HTTP connection pool and configurable timeout
- Safe upstream timeout/network/non-JSON error handling
- SQLite usage tracking for status, token counts, and latency
- Docker Compose, OpenAPI docs, and CI across Python 3.11–3.13

### Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Set GATEWAY_API_KEY and PROVIDERS_JSON in .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### API
- `GET /health` — health check
- `GET /v1/models` — configured models (Bearer auth)
- `POST /v1/chat/completions` — chat completion proxy (Bearer auth)
- `GET /admin/usage?limit=100` — usage records (Bearer auth)
- `GET /docs` — interactive OpenAPI documentation

### Security notes
Keep provider credentials in server-side environment configuration. Only HTTPS provider URLs are accepted, except HTTP loopback for local development. Add TLS termination, rate limiting, tenant isolation, and a stronger persistent database before public or multi-user deployment.
