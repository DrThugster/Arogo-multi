# backend/app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.database import mongodb_client, redis_client
from app.routes import (
    consultation,
    summary,
    report,
    speech,
    websocket  # New separate file for WebSocket handling
)
from app.services.chat_service import ChatService
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Starting up the application...")
        
        # Test database connections
        mongodb_client.admin.command('ping')
        redis_client.ping()
        logger.info("Successfully connected to databases")
        
        # Initialize WebSocket manager
        websocket.initialize_manager()
        
    except Exception as e:
        logger.error(f"Startup Error: {str(e)}")
        raise e
    
    yield
    
    # Shutdown
    try:
        logger.info("Shutting down the application...")
        
        # Close database connections
        mongodb_client.close()
        logger.info("Database connections closed")
        
        # Clean up WebSocket connections
        await websocket.cleanup_connections()
        
    except Exception as e:
        logger.error(f"Shutdown Error: {str(e)}")

app = FastAPI(
    title="Multilingual Telemedicine API",
    description="AI-powered multilingual telemedicine consultation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Language middleware
@app.middleware("http")
async def add_language_headers(request: Request, call_next):
    """Add language handling headers to requests."""
    response = await call_next(request)
    # Get language from request header or default to English
    language = request.headers.get("Accept-Language", "en").split(",")[0]
    response.headers["Content-Language"] = language
    return response

# Include routers with proper prefixes and tags
app.include_router(
    consultation.router,
    prefix="/api/consultation",
    tags=["consultation"]
)

app.include_router(
    summary.router,
    prefix="/api/summary",
    tags=["summary"]
)

app.include_router(
    report.router,
    prefix="/api/report",
    tags=["report"]
)

app.include_router(
    speech.router,
    prefix="/api/speech",
    tags=["speech"]
)

# Include WebSocket routes
app.include_router(websocket.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check the health status of the application."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "mongodb": "disconnected",
                "redis": "disconnected"
            },
            "language_services": {
                "bhashini": "unknown",
                "translation_cache": "unknown"
            }
        }

        # Check MongoDB
        try:
            mongodb_client.admin.command('ping')
            health_status["services"]["mongodb"] = "connected"
        except Exception as e:
            logger.error(f"MongoDB health check failed: {str(e)}")
            health_status["services"]["mongodb"] = f"error: {str(e)}"

        # Check Redis
        try:
            redis_client.ping()
            health_status["services"]["redis"] = "connected"
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            health_status["services"]["redis"] = f"error: {str(e)}"

        # Check Bhashini Service
        try:
            bhashini_status = await speech.router.check_bhashini_status()
            health_status["language_services"]["bhashini"] = bhashini_status
        except Exception as e:
            logger.error(f"Bhashini service check failed: {str(e)}")
            health_status["language_services"]["bhashini"] = f"error: {str(e)}"

        # Overall status check
        services_healthy = all(
            status == "connected" 
            for status in health_status["services"].values()
        )
        language_services_healthy = all(
            status not in ["error", "unknown"] 
            for status in health_status["language_services"].values()
        )

        if services_healthy and language_services_healthy:
            return health_status
        else:
            return JSONResponse(
                status_code=503,
                content=health_status
            )

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    error_response = {
        "detail": str(exc),
        "status": "error",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add language-specific error messages if available
    if hasattr(request.state, "language"):
        try:
            speech_processor = speech.router.speech_processor
            translated_error = await speech_processor.bhashini_service.translate_text(
                text=str(exc),
                source_language="en",
                target_language=request.state.language
            )
            error_response["translated_detail"] = translated_error["text"]
        except:
            pass
            
    return JSONResponse(
        status_code=500,
        content=error_response
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )