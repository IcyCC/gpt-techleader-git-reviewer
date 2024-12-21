# GPT TECH LEADER GIT REVIEWER

[中文版](README.md)

An AI-powered code review assistant that automatically provides code reviews and suggestions for GitHub Pull Requests.

## Features

> [!NOTE]  
> You can submit a PR to this repo to experience the functionality. Sample PR: https://github.com/IcyCC/gpt-techleader-git-reviewer/pull/19

- Automated Code Review: Automatically triggered when PRs are created or updated
- Smart Comment Replies: Intelligent responses to developer comments
- GitHub Support

> Code developed by Cursor, freeing up production capacity

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/IcyCC/gpt-techleader-git-reviewer.git
cd gpt-techleader-git-reviewer
```

2. Configure environment:
```bash
vim .env
# Edit .env file with your configurations
```

3. Start the service:
```bash
# Using Docker
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## Configuration

### Environment Variables

Create a `.env` file and configure the following environment variables:

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_token            # GitHub Personal Access Token
GITHUB_WEBHOOK_SECRET=your_webhook_secret # Webhook Secret
GITHUB_API_URL=https://api.github.com     # GitHub API URL (may differ for enterprise)

# GPT Configuration
GPT_API_KEY=your_gpt_api_key             # OpenAI API Key
GPT_API_URL=https://api.openai.com/v1    # OpenAI API URL
GPT_MODEL=gpt-4                          # Model to use, supports openai model
GPT_LANGUAGE=english                     # Response language

# Application Configuration
DEBUG=true                               # Debug mode
ENVIRONMENT=development                  # Environment: development/production

# Redis Configuration
REDIS_URL=redis://localhost:6379         # Redis connection URL
REDIS_CHAT_TTL=3600                     # Chat history TTL (seconds)

# Rate Limiting Configuration
RATE_LIMIT_EXPIRE=3600                  # Rate limit expiration (seconds)
MAX_AI_REQUESTS=100                     # Maximum AI requests per hour
MAX_MR_REVIEWS=20                       # Maximum PR reviews per hour
MAX_COMMENT_REPLIES=5                   # Maximum replies per comment
```

## Contributing

We welcome all forms of contributions! If you want to participate in project development:

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/AmazingFeature`
3. Commit your changes: `git commit -m 'Add some AmazingFeature'`
4. Push to the branch: `git push origin feature/AmazingFeature`
5. Create a Pull Request

### Development Guidelines

1. Code Style
   - Use `black` for formatting: `black .`
   - Use `isort` for import sorting: `isort .`
   - Follow PEP 8 guidelines

3. Documentation
   - Update API documentation
   - Add code comments
   - Update README

### PR Submission Guidelines

1. PR title format: `[type] brief description`
   - Type: feat/fix/docs/style/refactor/test/chore
2. Detailed PR description
3. Ensure all tests pass
4. Add necessary documentation updates

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Contact Us

WeChat Group
![WeChat Group](./docs/wx.png)