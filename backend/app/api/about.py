"""About and version information endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

from app.utils.version import get_version, get_changelog

router = APIRouter()

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)


class VersionResponse(BaseModel):
    """Version information response."""
    version: str
    name: str = "Walkabout"
    description: str = "Self-hosted flight deal aggregator"


@router.get("/api/version", response_model=VersionResponse)
async def get_version_info():
    """Return the current version as JSON."""
    return VersionResponse(version=get_version())


@router.get("/api/changelog")
async def get_changelog_info():
    """Return the changelog as plain text."""
    return get_changelog()


@router.get("/legacy", response_class=HTMLResponse)
async def about_page(request: Request):
    """Render the about page with version and changelog."""
    version = get_version()
    changelog = get_changelog()

    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "version": version,
            "changelog": changelog,
        }
    )
