# GPT TECH LEADER GIT REVIEWER

[English Version](README_EN.md)

AI 驱动的代码审查助手，自动为 GitHub Pull Requests 提供代码审查和建议。


## 功能特点

> [!NOTE]  
> 可以在本repo提MR, 体验功能, 样例MR(MR: https://github.com/IcyCC/gpt-techleader-git-reviewer/pull/19)

- 自动代码审查：当 PR 创建或更新时自动触发, 对代码风格和业务逻辑进行审查
- 智能评论回复：对开发者的评论进行智能回复
- 支持github

> 代码由Cursor开发, 解放生产力

## 快速开始

1. 克隆仓库：
```bash
git clone https://github.com/IcyCC/gpt-techleader-git-reviewer.git
cd gpt-techleader-git-reviewer
```

2. 配置环境：
```bash
vim .env
# 编辑 .env 文件填写配置
```

3. 启动服务：
```bash
# 使用 Docker
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

或者使用docker
```bash
docker-compose up -d --build
```

4. 配置repo的

## 配置说明

### 环境变量配置

创建 `.env` 文件并配置以下环境变量：

```env
# GitHub配置
GITHUB_TOKEN=github_pat_xxxxx # GitHub Personal Access Token
GITHUB_WEBHOOK_SECRET=your_webhook_secret # GitHub Webhook 密钥
GITHUB_REPOS=owner/repository # 格式：用户名/仓库名

# GPT配置
GPT_API_KEY=sk-xxxxxx # GPT API密钥
GPT_API_URL=https://api.example.com/v1 # GPT API地址
GPT_MODEL=claude-3-5-sonnet-20240620 # GPT模型版本
GPT_LANGUAGE=中文 # AI响应语言
GPT_TIMEOUT=1200 # API超时时间(秒)

# AI响应缓存配置
USE_AI_DEBUG_CACHE=false # 是否使用AI调试缓存
AI_CACHE_DIR=app/infra/cache/mock_responses # AI响应缓存目录

# 应用配置
DEBUG=true # 调试模式
ENVIRONMENT=development # 环境设置

# 限流配置
MAX_MR_REVIEWS_PER_HOUR=5 # 每小时最大PR审查次数
MAX_AI_REQUESTS_PER_HOUR=100 # 每小时最大AI请求次数
MAX_TOKENS=200000 # 最大token数

# Redis配置
REDIS_URL=redis://localhost:6379 # Redis连接URL
REDIS_CHAT_TTL=3600 # Redis 聊天记录过期时间(秒)
```

### 配置repo
配置github的webhook, 需要配置webhook的url, 
```
http://<host>:<port>/api/v1/webhook/github
```

开启接受 Which events would you like to trigger this webhook?:
- Pull request reviews
- Pull requests
- Pull request review threads
- Pull request review comments


## 参与贡献

我们欢迎任何形式的贡献！如果你想要参与项目开发：

1. Fork 本仓库
2. 创建你的特性分支：`git checkout -b feature/AmazingFeature`
3. 提交你的改动：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 创建一个 Pull Request

### 开发指南

1. 代码风格
   - 使用 `black` 格式化代码：`black .`
   - 使用 `isort` 排序导入：`isort .`
   - 遵循 PEP 8 规范

3. 文档
   - 更新 API 文档
   - 添加代码注释
   - 更新 README

### 提交 PR 注意事项

1. PR 标题格式：`[类型] 简短描述`
   - 类型：feat/fix/docs/style/refactor/test/chore
2. 详细的 PR 描述
3. 确保所有测试通过
4. 添加必要的文档更新

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系我们

微信群
![微信群](./docs/wx.png)
