# KnowAct Simulator Test 独立前端

[English](README.md)

这是面向实验参与者的独立 React/Vite 应用。它不包含 Knowledge Graph authoring、
Episodes、Run Queue、agent scoring 或内部结果浏览入口。

## 参与者流程

```text
输入并确认 Profile
  -> 逐节点确认个人 Knowledge Map
  -> 从后端提供的双语题库抽取 20 题
  -> 每题先提交本人回答，再显示 Simulator 回答
  -> 完成五项个人一致性自评
  -> 保存或使用恢复码继续
```

应用启动时直接读取后端提供的 domain、reviewed graph 和双语题库，并自动选择第一组
题数不少于 20 的兼容材料。实际选中的材料 identity 由后端写入 session。应用不会请求
全体 session 列表；恢复只使用浏览器保存或参与者手工输入的随机 `session_id`。

## 本地运行

从仓库根目录运行：

```bash
make simulator-test
```

应用默认监听 `http://127.0.0.1:5174`，开发代理把 `/api` 转发到
`http://127.0.0.1:8000`。同源本地开发不需要创建前端环境文件；只有需要覆盖公网 API
地址、实验标题、provider 或默认语言时，才需要把 `.env.example` 复制为 `.env.local`。

## 独立构建

```bash
npm --prefix simulator-test-frontend ci
npm --prefix simulator-test-frontend run build
```

静态产物位于 `simulator-test-frontend/dist/`。该目录可以单独部署到静态服务器。

也可以使用随附 Dockerfile：

```bash
docker build \
  --build-arg VITE_API_BASE_URL=https://api.example.org \
  --build-arg VITE_SIMULATOR_PROVIDER=openai \
  -t knowact-simulator-test \
  simulator-test-frontend
```

`VITE_*` 值会进入浏览器 bundle，不能放 API key 或其他密钥。

## 后端连接

同源部署时保持 `VITE_API_BASE_URL` 为空，并由反向代理把 `/api` 转发到 KnowAct
backend。

跨域部署时：

```dotenv
# simulator-test-frontend/.env.local
VITE_API_BASE_URL=https://api.example.org

# repository root .env
KNOWACT_CORS_ORIGINS=https://study.example.org
```

后端只接受显式 `http(s)` origin，不允许通配符。CORS 不是身份认证；把 backend
暴露到公网时，还应在 API gateway 或 reverse proxy 层限制参与者域名只能访问本应用
所需的路由。建议拒绝：

- `/api/runtime/*`
- `/api/tested-agents/*`
- candidate graph generation/promotion；
- session collection route `GET /api/experiments/simulator-tests/sessions`。

当前参与者应用需要 Profile/Map 的窄 authoring routes，以及
`/api/experiments/simulator-tests/*` 的单 session routes。正式部署前应在 gateway
access log 中验证 allowlist。

## 数据边界

- API key 只保存在 backend `.env`，不会下发浏览器；
- participant code、Profile、Map、回答和自评属于受限实验数据；
- session 和 Map revision 写入
  `experiments/02_simulator_human_validity/results/private/`；
- 浏览器仅保存随机 session 恢复码，不保存完整回答副本；
- 专家盲评仍是后续独立阶段。
