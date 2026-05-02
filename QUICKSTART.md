# Dark Factory V3 - 快速启动指南

## 环境要求

- Python 3.11+
- pip
- Node.js 18+ 和 pnpm，用于运行 bridge plugin 验证

安装 Python 依赖：

```bash
cd /home/siyuah/workspace/123

python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pyyaml httpx
```

## 启动内部预览服务

```bash
cd /home/siyuah/workspace/123
source .venv/bin/activate

export DF_API_KEY="$(python3 -c 'import uuid; print(uuid.uuid4())')"
echo "Your API Key: $DF_API_KEY"
echo "请保存此 key，后续 API 请求需要使用相同的 key。"

mkdir -p ./journal_data
python3 server.py --port 9701 --journal ./journal_data/preview.jsonl
```

如果需要从文件读取 API key：

```bash
mkdir -p ./secrets
printf "%s" "$DF_API_KEY" > ./secrets/df_api_key
chmod 600 ./secrets/df_api_key

DF_API_KEY_FILE=./secrets/df_api_key \
  python3 server.py --port 9701 --journal ./journal_data/preview.jsonl
```

## 健康检查

健康检查不需要 API key：

```bash
curl -sf http://localhost:9701/api/health | python3 -m json.tool
```

## 创建测试 Run

```bash
curl -sf -X POST http://localhost:9701/api/external-runs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $DF_API_KEY" \
  -H "X-Protocol-Release-Tag: v3.0-agent-control-r1" \
  -d '{
    "protocolReleaseTag": "v3.0-agent-control-r1",
    "requestedBy": "internal-preview-test",
    "workloadClass": "code",
    "inputRef": "preview-test-001",
    "traceId": "trace-preview-001"
  }' | python3 -m json.tool
```

## 查询状态

```bash
RUN_ID="<创建 Run 返回的 runId>"

curl -sf "http://localhost:9701/api/external-runs/$RUN_ID" \
  -H "X-API-Key: $DF_API_KEY" \
  | python3 -m json.tool

curl -sf http://localhost:9701/api/projection \
  -H "X-API-Key: $DF_API_KEY" \
  | python3 -m json.tool
```

## Journal 运维

```bash
cd /home/siyuah/workspace/123
source .venv/bin/activate

python3 tools/journal_admin.py backup \
  --journal ./journal_data/preview.jsonl \
  --backup-dir ./backups/preview

python3 tools/journal_admin.py retain \
  --backup-dir ./backups/preview \
  --keep-last 10 \
  --max-age-days 14
```

快速检查 JSONL 行数：

```bash
wc -l ./journal_data/preview.jsonl
```

## Bridge Plugin 验证

bridge plugin 的 HTTP 集成测试会启动一个临时 Dark Factory server，并验证 probe、lease、park、rehydrate、resume 的真实 HTTP 调用：

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm test
```

预期结果：

```text
Test Files  7 passed (7)
Tests       58 passed (58)
```

## 安全提示

- `GET /api/health` 免认证，用于健康检查。
- 其他 API 请求必须携带 `X-API-Key`。
- 不要把 API key 提交到 Git。
- 内部预览可以直接使用 HTTP；需要 TLS 时使用仓库内的 `Caddyfile` 作为反向代理方案。
