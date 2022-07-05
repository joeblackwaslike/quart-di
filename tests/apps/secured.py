from typing import Optional
import logging

from di.dependant import Marker
from quart import Blueprint
from werkzeug.exceptions import Unauthorized

from quart_di.compat import Annotated
from quart_di import QuartDI
from quart_di.security import (
    APIKeyHeader,
    RequiredSecuritySchemes,
    AlternativeSecuritySchemes,
)
from quart_di.markers import T

from shared import setup_logging
from .common import create_app, register_json_error_handlers

logger = logging.getLogger(__name__)
setup_logging("quart_di", "tests")


class PublicAPIKey(APIKeyHeader):
    unauthorized_error = None
    name = "x-public-api-key"


class SecretAPIKey(APIKeyHeader):
    unauthorized_error = None
    name = "x-secret-api-key"


class APIKeys(RequiredSecuritySchemes):
    public: Optional[PublicAPIKey]
    secret: Optional[SecretAPIKey]


class SecurityModel(AlternativeSecuritySchemes):
    api_keys: Optional[APIKeys]


NO_KEYS_ERROR_MSG = "No public `x-public-api-key` or secret `x-secret-api-key` api key provided"
BOTH_KEYS_ERROR_MSG = "Both public `x-public-api-key` and secret `x-secret-api-key` api keys provided, must provide onr or the other"


def enforce_authorized_user(auth: SecurityModel) -> None:
    api_keys = auth.api_keys
    public_api_key = auth.api_keys.public.api_key if auth.api_keys.public is not None else None
    secret_api_key = auth.api_keys.secret.api_key if auth.api_keys.secret is not None else None

    logger.info(
        "Got api keys",
        extra=dict(
            api_keys=api_keys,
            public=public_api_key,
            secret=secret_api_key,
        ),
    )

    if api_keys is None or (public_api_key is None and secret_api_key is None):
        raise Unauthorized(NO_KEYS_ERROR_MSG)
    if api_keys and (public_api_key is not None and secret_api_key is not None):
        raise Unauthorized(BOTH_KEYS_ERROR_MSG)


# Annotations
RequireApiKeyAuth = Annotated[T, Marker(enforce_authorized_user, scope="request")]


base = Blueprint("base", __name__)


@base.post("/secured")
def secured(_: RequireApiKeyAuth, auth: SecurityModel):
    return dict(
        api_keys=dict(
            public=auth.api_keys.public.api_key if auth.api_keys.public else None,
            secret=auth.api_keys.secret.api_key if auth.api_keys.secret else None,
        ),
    )


di = QuartDI(decorate_views=True)
app = create_app(base, di)
register_json_error_handlers(app)
