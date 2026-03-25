from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routes import imports, search, conversations, categories, tags, ingest
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(imports.router)
app.include_router(search.router)
app.include_router(conversations.router)
app.include_router(categories.router)
app.include_router(tags.router)
app.include_router(ingest.router)

app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
