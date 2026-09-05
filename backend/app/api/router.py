from fastapi import APIRouter

from app.api.endpoints import (
    ai,
    approvals,
    audit,
    auth,
    common_codes,
    cpse,
    dashboard,
    harmonization,
    materials,
    notifications,
    settings as settings_endpoint,
    uploads,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(materials.router)
api_router.include_router(ai.router)
api_router.include_router(harmonization.router)
api_router.include_router(approvals.router)
api_router.include_router(common_codes.router)
api_router.include_router(common_codes.common_materials_router)
api_router.include_router(cpse.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
api_router.include_router(notifications.router)
api_router.include_router(settings_endpoint.router)
api_router.include_router(uploads.router)
