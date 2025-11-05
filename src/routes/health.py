"""Health check and service info endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "service": "Lead Enrichment API",
        "version": "0.1.0",
        "status": "running",
        "description": "B2B company enrichment with web research and Orbis database matching",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "enrich_company": "/api/enrich-company",
        },
        "example_request": {
            "name": "WILDWINE LTD",
            "domain": "wildwine.je",
            "city": "London",
            "country": "United Kingdom",
            "phone": "+447797893894",
        },
    }


@router.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "service": "lead-enrichment"}
