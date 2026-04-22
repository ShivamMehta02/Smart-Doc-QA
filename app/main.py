import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger, set_correlation_id
from app.schemas.response import HealthResponse

# Initialize Logging
setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade Document Q&A API for TheHireHub.AI",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware: Correlation ID & Request Timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", "")
    set_correlation_id(correlation_id)
    
    start_time = time.time()
    response: Response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        "request_processed",
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration=f"{duration:.4f}s"
    )
    return response

# Include V1 API Routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check endpoint."""
    return HealthResponse(
        status="healthy",
        api="online",
        database="connected", # TODO: Actual check
        redis="connected",    # TODO: Actual check
        version=settings.APP_VERSION
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
