from fastapi import FastAPI
from app.api.routes_health import router as health_router
from app.api.routes_query import router as query_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
)

# Include API routes
app.include_router(health_router, tags=["health"])
app.include_router(query_router, tags=["query"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)