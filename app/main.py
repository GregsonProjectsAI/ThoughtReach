from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import imports, search, conversations, categories, tags, ingest, library
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(imports.router)
app.include_router(search.router)
app.include_router(conversations.router)
app.include_router(categories.router)
app.include_router(tags.router)
app.include_router(ingest.router)
app.include_router(library.router)

app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
