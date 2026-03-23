from fastapi import APIRouter, Depends, BackgroundTasks, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.api import PasteImportRequest, PasteImportResponse, ImportJobOut
from app.models.models import ImportJob
from app.services.ingestion import process_paste_import

router = APIRouter(prefix="/imports", tags=["Imports"])

@router.post("/paste", response_model=PasteImportResponse)
async def import_paste(
    request: PasteImportRequest, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db)
):
    job = ImportJob(import_mode="paste", status="pending", notes=request.notes)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    background_tasks.add_task(process_background_import, job.id, request)
    return PasteImportResponse(job_id=job.id, status=job.status)

async def process_background_import(job_id, request):
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await process_paste_import(job_id, request, session)

@router.post("/file", response_model=PasteImportResponse)
async def import_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    job = ImportJob(import_mode="file", status="failed", notes="File upload fully not yet implemented for phase 1. Try paste. Got file: " + file.filename)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return PasteImportResponse(job_id=job.id, status=job.status)

@router.get("", response_model=list[ImportJobOut])
async def list_imports(db: AsyncSession = Depends(get_db), limit: int = 100):
    from sqlalchemy import select
    result = await db.execute(select(ImportJob).order_by(ImportJob.started_at.desc()).limit(limit))
    return list(result.scalars().all())
