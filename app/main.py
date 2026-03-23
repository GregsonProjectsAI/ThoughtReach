from fastapi import FastAPI
from app.api.routes import imports, search, conversations
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(imports.router)
app.include_router(search.router)
app.include_router(conversations.router)

@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
