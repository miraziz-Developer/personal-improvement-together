"""ASGI entry point:  uv run uvicorn pit.main:app --reload"""

from pit.api.app import create_app
from pit.config import get_settings
from pit.observability import init_sentry

init_sentry(get_settings(), "api")
app = create_app()
