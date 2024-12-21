from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infra.config.settings import get_settings
from app.api.endpoints import webhook, review

settings = get_settings()

app = FastAPI(
    title="AI Code Reviewer",
    description="AI 驱动的代码审查助手",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(webhook.router, prefix=f"{settings.API_V1_STR}/webhook", tags=["webhook"])
app.include_router(review.router, prefix=f"{settings.API_V1_STR}", tags=["review"])

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}
  