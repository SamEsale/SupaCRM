"""OpenAPI utilities placeholder"""

from fastapi.openapi.utils import get_openapi


def custom_openapi(app):
    return get_openapi(title="SupaCRM API", version="0.0.1", routes=app.routes)
