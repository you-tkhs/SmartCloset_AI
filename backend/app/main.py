import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from ultralytics import YOLO

from app.config import settings
from app.database import create_session, init_db
from app.routers import health, items, suggest, upload, weather
from app.services import storage_service
from app.services.pipeline_service import recover_stale_processing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage_service.init_storage()
    init_db()

    model_path = Path(settings.MODEL_PATH)
    if not model_path.exists():
        raise RuntimeError("YOLO model weights not found at MODEL_PATH")

    app.state.yolo_model = YOLO(str(model_path))

    if settings.OPENAI_API_KEY:
        try:
            app.state.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception:
            # design.md 13.4節: 外部APIクライアント初期化エラーはメッセージを固定文字列に差し替えて記録する
            logger.error("failed to initialize OpenAI client")
            app.state.openai_client = None
    else:
        app.state.openai_client = None
        logger.warning("OPENAI_API_KEY is not set; OpenAI client disabled")

    db = create_session()
    try:
        recover_stale_processing(db)
    finally:
        db.close()

    tmp_dir = Path(settings.STORAGE_DIR) / "tmp"
    for path in tmp_dir.glob("*"):
        if path.is_file():
            storage_service.delete_tmp(path)

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/images/originals",
    StaticFiles(directory=Path(settings.STORAGE_DIR) / "originals", check_dir=False),
    name="originals",
)
app.mount(
    "/images/transparent",
    StaticFiles(directory=Path(settings.STORAGE_DIR) / "transparent", check_dir=False),
    name="transparent",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        payload = exc.detail
    else:
        payload = {"detail": str(exc.detail), "error_code": "internal_error", "retryable": True}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "入力内容を確認してください。", "error_code": "validation_error", "retryable": False},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "サーバーエラーが発生しました。再度お試しください。",
            "error_code": "internal_error",
            "retryable": True,
        },
    )


app.include_router(health.router)
app.include_router(upload.router)
app.include_router(items.router)
app.include_router(weather.router)
app.include_router(suggest.router)
