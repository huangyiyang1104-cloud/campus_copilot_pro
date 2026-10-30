# 压测脚本

三个脚本都使用 `httpx.AsyncClient`，不额外引入 locust/k6。每个脚本会：

1. 用管理员账号创建一个临时学生账号；
2. 用临时账号登录并执行并发请求；
3. 结束时删除测试资料/会话和临时账号。

临时账号前缀分别为 `load_api_`、`load_chat_`、`load_material_`，不会影响正式用户。

## 环境

- 后端已启动（默认 `http://127.0.0.1:8000`）
- MySQL / Redis 可用
- `material_load.py` 需要 OSS、Embedding、Milvus 可用
- `chat_load.py` 会真实调用 DeepSeek，注意 token 消耗

安装依赖：

```bash
cd backend
pip install -r requirements.txt
```

## 1. HTTP 读写压测

覆盖鉴权、课表、会话列表、学习计划、课表并发整表覆盖。

```bash
cd backend
python -m tests.load.api_load
```

可调参数：

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `LOAD_BASE_URL` | `http://127.0.0.1:8000` | 后端地址 |
| `LOAD_ADMIN_USERNAME` | `admin` | 管理员账号 |
| `LOAD_ADMIN_PASSWORD` | `admin123` | 管理员密码 |
| `LOAD_READ_REQUESTS` | `100` | 每个读接口请求数 |
| `LOAD_CONCURRENCY` | `20` | 读并发 |
| `LOAD_WRITE_REQUESTS` | `5` | 课表写请求数 |
| `LOAD_WRITE_CONCURRENCY` | `5` | 写并发 |

## 2. 流式对话压测

每个虚拟用户创建独立会话，统计首包耗时和总耗时。

```bash
cd backend
python -m tests.load.chat_load
```

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `CHAT_REQUESTS` | `3` | 对话请求数 |
| `CHAT_CONCURRENCY` | `3` | 并发数 |
| `CHAT_PROMPT` | `只回复两个字：收到` | 压测用问题 |

## 3. 资料上传/入库压测

并发上传 Markdown，轮询到 `status=2`，验证 OSS → 切片 → Embedding → Milvus 的完整链路。

```bash
cd backend
python -m tests.load.material_load
```

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `MATERIAL_UPLOADS` | `3` | 上传数量 |
| `MATERIAL_CONCURRENCY` | `3` | 上传并发 |
| `MATERIAL_TIMEOUT` | `120` | 等待入库超时（秒） |

该脚本使用 Markdown，不经过 MinerU，因此测的是 OSS、切片、Embedding 和 Milvus 写入；MinerU 解析链路需要单独用 PDF/Word 验证。

## 2026-10-30 实测结果

环境：Windows、本地后端（8001 测试实例）、MySQL、Redis SSH 隧道、Milvus Lite、OSS、DeepSeek、DashScope。以下是小样本功能/并发验证，不是容量上限测试。

### HTTP 读写

`LOAD_READ_REQUESTS=50`、`LOAD_CONCURRENCY=10`、`LOAD_WRITE_REQUESTS=5`、`LOAD_WRITE_CONCURRENCY=5`：

```text
final courses: 3 rows (expected 3)
scenario                       n    ok   err     rps   p50(ms)   p95(ms)   p99(ms)
----------------------------------------------------------------------------------
GET /api/auth/me              50    50     0    92.0      71.4     210.8     243.5
GET /api/courses              50    50     0    80.6      86.3     229.7     231.6
GET /api/conversations        50    50     0   123.2      67.6      93.9      95.2
GET /api/study-plans          50    50     0   103.4      83.4     101.2     133.4
PUT /api/courses               5     5     0    35.7     126.1     138.6     138.6
```

结论：

- 200 个读请求 + 5 个并发整表覆盖全部成功；
- 并发写后课表仍然是 3 行，没有出现半写/重复行；
- 读接口 p95 在 230ms 以内。

### 流式对话

`CHAT_REQUESTS=3`、`CHAT_CONCURRENCY=3`：

```text
success: 3/3  errors: 0  wall: 1.16s
first token: p50=787ms p95=1039ms
total:       p50=815ms p95=1047ms
```

结论：3 路 SSE 并发全部完成，首包 p95 约 1.0s，无错误事件。

### 资料并发入库

`MATERIAL_UPLOADS=3`、`MATERIAL_CONCURRENCY=3`：

```text
uploaded: 3/3  upload errors: 0  timed out: 0
upload latency: p50=752ms p95=755ms
ingest latency: p50=3967ms p95=3968ms
final states: [(19, 2, 2), (18, 2, 2), (20, 2, 2)]
```

结论：3 份资料并发上传全部到「已索引」，每份 2 个切片；Milvus Lite 的全局锁让入库阶段串行，因此端到端约 4s，但没有失败或状态卡死。

## 说明

- 脚本默认创建临时账号，API 删除用户后数据库里的课程/会话可能成为孤儿记录，正式压测后建议按用户名前缀清理；
- 本次结果已清理测试账号、资料和会话，仅保留正式用户数据；
- 这些数字用于证明链路可并发运行，不代表生产容量；生产部署应使用 Milvus Standalone、Celery 多 Worker，并补充限流和监控。
