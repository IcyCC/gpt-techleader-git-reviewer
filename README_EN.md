# GPT TECH LEADER GIT REVIEWER

[中文版](README.md)

An AI-powered code review assistant that automatically provides code reviews and suggestions for GitHub Pull Requests.

## Features

> [!NOTE]  
> You can submit a PR to this repo to experience the functionality. Sample PR: https://github.com/IcyCC/gpt-techleader-git-reviewer/pull/19

- Automated Code Review: Automatically triggered when PRs are created or updated, reviewing code style and business logic
- Smart Comment Replies: Intelligent responses to developer comments
- GitHub and GitLab Support

> Code developed by Cursor, freeing up productivity

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
# Using Python
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

4. Configure repository

## Configuration

### Environment Variables

Create a `.env` file and configure the following environment variables:

```env
# GitHub Configuration
GITHUB_TOKEN=github_pat_xxxxx # GitHub Personal Access Token
GITHUB_WEBHOOK_SECRET=your_webhook_secret # GitHub Webhook Secret
GITHUB_REPOS=owner/repository # Format: username/repository

# GPT Configuration
GPT_API_KEY=sk-xxxxxx # GPT API Key
GPT_API_URL=https://api.example.com/v1 # GPT API URL
GPT_MODEL=claude-3-5-sonnet-20240620 # GPT Model Version
GPT_LANGUAGE=english # AI Response Language
GPT_TIMEOUT=1200 # API Timeout (seconds)

# AI Response Cache Configuration
USE_AI_DEBUG_CACHE=false # Whether to use AI debug cache
AI_CACHE_DIR=app/infra/cache/mock_responses # AI Response Cache Directory

# Application Configuration
DEBUG=true # Debug Mode
ENVIRONMENT=development # Environment Setting

# Rate Limiting Configuration
MAX_MR_REVIEWS_PER_HOUR=5 # Maximum PR reviews per hour
MAX_AI_REQUESTS_PER_HOUR=100 # Maximum AI requests per hour
MAX_TOKENS=200000 # Maximum tokens

# Redis Configuration
REDIS_URL=redis://localhost:6379 # Redis Connection URL
REDIS_CHAT_TTL=3600 # Redis Chat History TTL (seconds)
```

### Repository Configuration
Configure GitHub webhook with the following URL:
```
http://<host>:<port>/api/v1/webhook/github
```

Enable the following events in "Which events would you like to trigger this webhook?":
- Pull request reviews
- Pull requests
- Pull request review threads
- Pull request review comments

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

2. Documentation
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