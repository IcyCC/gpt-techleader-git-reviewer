# GPT TECH LEADER GIT REVIEWER

[English Version](README_EN.md)

AI 驱动的代码审查助手，自动为 GitHub Pull Requests 提供代码审查和建议。


## 功能特点

> [!NOTE]  
> 可以在本repo提MR, 体验功能, 样例MR(MR: https://github.com/IcyCC/gpt-techleader-git-reviewer/pull/5)

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
uvicorn app.main:app --reload
```

## 配置说明

### 环境变量配置

创建 `.env` 文件并配置以下环境变量：

```env
# GitHub 配置
GITHUB_TOKEN=your_github_token            # GitHub Personal Access Token
GITHUB_WEBHOOK_SECRET=your_webhook_secret # Webhook 密钥
GITHUB_API_URL=https://api.github.com     # GitHub API 地址（企业版可能不同）

# GPT 配置
GPT_API_KEY=your_gpt_api_key             # OpenAI API 密钥
GPT_API_URL=https://api.openai.com/v1    # OpenAI API 地址
GPT_MODEL=gpt-4                          # 使用的模型，支持openai模型
GPT_LANGUAGE=中文                         # 回复语言

# 应用配置
DEBUG=true                               # 调试模式
ENVIRONMENT=development                  # 环境：development/production

# Redis 配置
REDIS_URL=redis://localhost:6379         # Redis 连接地址
REDIS_CHAT_TTL=3600                     # 聊天记录保存时间（秒）

# 速率限制配置
RATE_LIMIT_EXPIRE=3600                  # 速率限制过期时间（秒）
MAX_AI_REQUESTS=100                     # 每小时最大 AI 请求次数
MAX_MR_REVIEWS=20                       # 每小时最大审查 PR 次数
MAX_COMMENT_REPLIES=5                   # 每条评论最大回复次数
```

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
