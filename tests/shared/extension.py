from http.cookies import BaseCookie
import json

from tests.apps.example import Config, StyleParams, AuthCookies


user_id = 42
kitchen_sink_request = dict(
    path=f"/endpoint/decorated/{user_id}/",
    method="POST",
    headers={
        "x-header-one": "one",
        "x-header-two": "2",
        "cookie": "session=123; csrf=adxfl3ils",
    },
    query_string=dict(
        q="hello",
        limit=10,
        page=1,
        offset=10,
        home="false",
        color="ffffff",
        theme="dark",
        logo="logo.png",
    ),
    json=dict(id=1, name="Joe", tags=["a", "b", "c"]),
)

kitchen_sink_endpoints = ["base.decorated_kitchen_sink", "base.undecorated_kitchen_sink"]
kitchen_sink_urls = [
    "/kitchen-sink/decorated/{user_id}/",
    "/kitchen-sink/undecorated/{user_id}/",
]


def validate_kitchen_sink_payload(payload, kitchen_sink_request, **kwargs):
    request_cookies = {
        name: morsel.value
        for name, morsel in BaseCookie(kitchen_sink_request["headers"]["cookie"]).items()
    }

    # common
    # returns {'q': None, 'skip': 0, 'limit': 100}
    # assert response.commons == {'q': 'Hello', 'skip': 0, 'limit': 10}

    db = payload["db"]
    assert isinstance(db, dict)
    assert db["db_uri"] == Config().db_uri

    x_header_one = payload["x_header_one"]
    assert x_header_one == kitchen_sink_request["headers"]["x-header-one"]
    assert isinstance(x_header_one, str)

    headers_model = payload["headers_model"]
    request_headers = kitchen_sink_request["headers"].copy()
    request_headers["x-header-two"] = int(request_headers["x-header-two"])

    for header_name in headers_model:
        assert headers_model[header_name] == request_headers[header_name]
    assert isinstance(headers_model, dict)

    headers = payload["headers"]
    assert set(kitchen_sink_request["headers"].items()).issubset(set(headers.items()))
    assert isinstance(headers, dict)

    body = payload["body"]
    assert body == kitchen_sink_request["json"]
    assert isinstance(body, dict)

    item = payload["item"]
    assert item == kitchen_sink_request["json"]
    assert isinstance(item, dict)

    name = payload["name"]
    assert name == kitchen_sink_request["json"]["name"]
    assert isinstance(name, str)

    tags = payload["tags"]
    assert tags == kitchen_sink_request["json"]["tags"]
    assert isinstance(tags, list)

    style_params = payload["style_params"]
    assert style_params == StyleParams.parse_obj(kitchen_sink_request["query_string"]).dict()
    assert isinstance(style_params, dict)

    color = payload["color"]
    assert color == kitchen_sink_request["query_string"]["color"]
    assert isinstance(color, str)

    query = payload["query"]
    assert query == {key: str(value) for key, value in kitchen_sink_request["query_string"].items()}
    assert isinstance(query, dict)

    session = payload["session"]
    assert session == request_cookies["session"]
    assert isinstance(session, str)

    auth = payload["auth"]
    assert auth == AuthCookies.parse_obj(request_cookies).dict()
    assert isinstance(auth, dict)

    cookies = payload["cookies"]
    assert cookies == request_cookies
    assert isinstance(cookies, dict)

    raw_body = payload["raw_body"]
    assert json.loads(raw_body) == kitchen_sink_request["json"]
    assert isinstance(raw_body, str)

    body = payload["body"]
    assert body == kitchen_sink_request["json"]
    assert isinstance(body, dict)

    bytes_body = payload["bytes_body"]
    assert json.loads(bytes_body) == kitchen_sink_request["json"]
    assert isinstance(bytes_body, str)

    str_body = payload["str_body"]
    assert json.loads(str_body) == kitchen_sink_request["json"]
    assert isinstance(str_body, str)

    user_id = payload["user_id"]
    assert user_id == kwargs.get("user_id")
    assert isinstance(user_id, type(kwargs.get("user_id")))

    extra = payload["extra"]
    assert extra is None
