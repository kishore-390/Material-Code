from fastapi import APIRouter

from app.api.endpoints import (
    ai,
    analytics,
    approvals,
    audit,
    auth,
    common_codes,
    cpse,
    dashboard,
    demo_import,
    duplicate_codes,
    harmonization,
    materials,
    notifications,
    procurement,
    settings as settings_endpoint,
    synchronization,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(materials.router)
api_router.include_router(ai.router)
api_router.include_router(harmonization.router)
api_router.include_router(approvals.router)
api_router.include_router(common_codes.router)
api_router.include_router(cpse.router)
api_router.include_router(synchronization.router)
api_router.include_router(demo_import.router)
api_router.include_router(dashboard.router)
api_router.include_router(analytics.router)
api_router.include_router(procurement.router)
api_router.include_router(audit.router)
api_router.include_router(notifications.router)
api_router.include_router(settings_endpoint.router)
api_router.include_router(duplicate_codes.router)
