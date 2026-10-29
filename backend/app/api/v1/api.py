from fastapi import APIRouter
from app.api.v1.endpoints import health, verify, history, reports, search, evidence, verdict, analytics

api_router = APIRouter()

# Include endpoint subrouters
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(verify.router, tags=["Verification Pipeline"])
api_router.include_router(search.router, tags=["Search & Source Discovery"])
api_router.include_router(evidence.router, tags=["Evidence & Source Comparison"])
api_router.include_router(verdict.router, tags=["Verdict & Confidence Engine"])
api_router.include_router(history.router, tags=["History"])
api_router.include_router(reports.router, tags=["Reports"])
api_router.include_router(analytics.router, tags=["Analytics"])


