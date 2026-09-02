from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

import app.models

from app.core.config import settings

from app.api.routes.auth import (
    router as auth_router,
)

from app.api.routes.roles import (
    router as roles_router,
)

from app.api.routes.permissions import (
    router as permissions_router,
)

from app.api.routes.users import (
    router as users_router,
)

from app.api.routes.audit_logs import (
    router as audit_logs_router,
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:4200",
    ],

    allow_credentials=True,

    allow_methods=[
        "*",
    ],

    allow_headers=[
        "*",
    ],
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(
    auth_router
)

app.include_router(
    roles_router
)

app.include_router(
    permissions_router
)

app.include_router(
    users_router
)

app.include_router(
    audit_logs_router
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "message":
            "FashionStore API funcionando"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status":
            "ok"
    }