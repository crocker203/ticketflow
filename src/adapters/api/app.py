from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from src.config import settings
from src.adapters.api.routes import router
from src.adapters.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables are created if running without migrations
    try:
        await init_db()
    except Exception as exc:
        print(f"[Warning] DB initialization skipped (will retry on query or use mock): {exc}")
    yield
    # Shutdown logic if needed


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "Automated Customer Support Ticket Categorization & Analytics Microservice. "
            "Built with Hexagonal Architecture, FastAPI, SQLAlchemy 2.0, PostgreSQL, and Pytest."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/docs")

    return app


app = create_app()
