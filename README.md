# AI Code Reviewer

AI 驱动的代码审查助手，自动为 GitHub Pull Requests 提供代码审查和建议。

## 功能特点

- 自动代码审查：当 PR 创建或更新时自动触发审查
- 智能评论回复：对开发者的评论进行智能回复
- 代码质量分析：检查代码风格、潜在问题和改进建议
- 完整的讨论支持：支持评论追踪和问题解决

## 快速开始

### 环境要求

- Python 3.8+
- Redis
- GitHub 账号和 Personal Access Token

### 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/your-username/ai-code-reviewer.git
cd ai-code-reviewer
```

2. 创建并激活虚拟环境：
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量：
创建 `.env` 文件并填写以下配置：
```env
# GitHub配置
GITHUB_TOKEN=your_github_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=your_repo_name

# GPT配置
GPT_API_KEY=your_gpt_api_key
GPT_API_URL=https://api.openai.com/v1
GPT_MODEL=gpt-4
GPT_LANGUAGE=中文

# 应用配置
DEBUG=true
ENVIRONMENT=development

# Redis配置
REDIS_URL=redis://localhost:6379
REDIS_CHAT_TTL=3600
```

5. 启动应用：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### GitHub Webhook 配置

1. 在 GitHub 仓库设置中添加 webhook：
   - Payload URL: `http://your-domain/api/v1/webhook/github`
   - Content type: `application/json`
   - Secret: 与 `GITHUB_WEBHOOK_SECRET` 保持一致
   - 选择事件：`Pull requests` 和 `Pull request reviews`

2. 确保 GitHub Token 具有以下权限：
   - `repo` 完整权限
   - `pull_requests` 读写权限
   - `contents` 读取权限

## API 接口

### 1. Webhook 接收
```
POST /api/v1/webhook/github
```
接收 GitHub webhook 事件，自动触发代码审查。

### 2. 手动触发审查
```
POST /api/v1/pulls/{owner}/{repo}/{mr_id}/review
```
手动触发对指定 PR 的代码审查。

### 3. 回复评论
```
POST /api/v1/pulls/{owner}/{repo}/{mr_id}/comments/{comment_id}/reply
```
对 PR 中的特定评论进行回复。

### 4. 获取讨论列表
```
GET /api/v1/pulls/{owner}/{repo}/{mr_id}/discussions
```
获取 PR 中的所有讨论记录。

## 生产环境部署

### Docker 部署

1. 构建镜像：
```bash
docker build -t ai-code-reviewer .
```

2. 运行容器：
```bash
docker run -d \
  --name ai-code-reviewer \
  -p 8000:8000 \
  --env-file .env \
  ai-code-reviewer
```

### 使用 Docker Compose

1. 创建 `docker-compose.yml`：
```yaml
version: '3'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - redis
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

2. 启动服务：
```bash
docker-compose up -d
```

## 安全建议

1. 在生产环境中使用 HTTPS
2. 设置强密码的 webhook secret
3. 定期轮换 GitHub Token 和 API 密钥
4. 配置适当的 CORS 策略
5. 使用环境变量管理敏感信息

## 常见问题

1. Webhook 未触发？
   - 检查 webhook 配置和密钥是否正确
   - 确认服务器可以被 GitHub 访问
   - 查看 webhook 发送历史和响应状态

2. 评论回复失败？
   - 验证 GitHub Token 权限
   - 检查评论 ID 是否正确
   - 查看应用日志获取详细错误信息

3. Redis 连接问题？
   - 确认 Redis 服务是否运行
   - 检查连接 URL 格式
   - 验证网络连接和防火墙设置

## 贡献指南

欢迎提交 Pull Request 和 Issue！在提交之前，请：

1. Fork 本仓库
2. 创建功能分支
3. 提交变更
4. 确保测试通过
5. 推送到���的分支
6. 创建 Pull Request

## 许可证

MIT License 