from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.api.routes_index import router as index_router
from app.api.routes_query import router as query_router


def create_app() -> FastAPI:
    app = FastAPI(title="RepoOps Maintainer Agent", version="0.3.0")
    app.include_router(health_router)
    app.include_router(index_router)
    app.include_router(query_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
