from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import connect_db, close_db
from app.routers import auth, users, health, codesprint, gamification, admin, syntax_match, tech_logo_match, tech_logo_match_admin
from app.website_generator import website_generator_router
from app.website_generator.ai_content_engine import ai_content_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="India Web Programmers API",
    description="Enterprise-grade API for India Web Programmers platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(codesprint.router, prefix="/api")
app.include_router(gamification.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(syntax_match.router, prefix="/api")
app.include_router(tech_logo_match.router, prefix="/api")
app.include_router(tech_logo_match_admin.router, prefix="/api")
app.include_router(website_generator_router, prefix="/api")
app.include_router(ai_content_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "India Web Programmers API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else None,
    }
