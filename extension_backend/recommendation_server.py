import json
import threading
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = "127.0.0.1"
PORT = 8765

VALID_STRATEGIES = {
    "balanced",
    "rb-heavy",
    "wr-heavy",
}

_state_lock = threading.Lock()
_state = {
    "session": None,
    "recommendation": None,
    "recommendation_version": 0,
}
_server = None
_server_thread = None


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            return _json_safe(item_method())
        except Exception:
            pass

    return str(value)


def _recommendation_view(recommendation):
    if not recommendation:
        return None

    recommended = recommendation.get("recommended_player")
    rankings = recommendation.get("rankings", [])

    fields = (
        "deterministic_rank",
        "name",
        "position",
        "team",
        "adp",
        "ecr",
        "projected_points",
        "reasoning",
    )

    def player_view(player):
        if not player:
            return None

        return {
            field: _json_safe(player.get(field))
            for field in fields
        }

    return {
        "recommended_player": player_view(recommended),
        "recommendation_reasoning": _json_safe(
            recommendation.get("recommendation_reasoning")
        ),
        "rankings": [
            player_view(player)
            for player in rankings[:5]
        ],
    }


def set_session(session):
    session = _json_safe(session or {})

    with _state_lock:
        existing = _state.get("session") or {}
        merged = {**existing, **session}
        _state["session"] = merged

    return deepcopy(merged)


def get_session():
    with _state_lock:
        session = deepcopy(_state.get("session"))

    return session


def update_session_metadata(**metadata):
    return set_session(metadata)


def wait_for_session(poll_seconds=0.1):
    while True:
        session = get_session()

        if session and session.get("draft_id"):
            return session

        time.sleep(poll_seconds)


def wait_for_strategy(poll_seconds=0.1):
    while True:
        session = get_session() or {}
        strategy = session.get("strategy")

        if strategy in VALID_STRATEGIES:
            return strategy

        time.sleep(poll_seconds)


def publish_recommendation(recommendation):
    view = _recommendation_view(recommendation)

    with _state_lock:
        _state["recommendation"] = view
        _state["recommendation_version"] += 1


def clear_recommendation():
    with _state_lock:
        _state["recommendation"] = None
        _state["recommendation_version"] += 1


def get_recommendation_payload():
    with _state_lock:
        return {
            "recommendation": deepcopy(
                _state.get("recommendation")
            ),
            "version": _state.get(
                "recommendation_version",
                0,
            ),
        }


class RecommendationHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        body = json.dumps(
            _json_safe(payload),
            separators=(",", ":"),
        ).encode("utf-8")

        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"ok": True})
            return

        if self.path == "/session":
            self._send_json(
                200,
                {"session": get_session()},
            )
            return

        if self.path == "/recommendation":
            self._send_json(
                200,
                get_recommendation_payload(),
            )
            return

        self._send_json(
            404,
            {"error": "Not found"},
        )

    def do_POST(self):
        if self.path != "/session":
            self._send_json(
                404,
                {"error": "Not found"},
            )
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
            raw_body = self.rfile.read(content_length)
            payload = json.loads(
                raw_body.decode("utf-8") or "{}"
            )
        except (ValueError, json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "Invalid JSON"},
            )
            return

        draft_id = str(
            payload.get("draft_id") or ""
        ).strip()

        if not draft_id:
            self._send_json(
                400,
                {"error": "draft_id is required"},
            )
            return

        session_update = {
            "draft_id": draft_id,
        }

        for field in (
            "sleeper_user_id",
            "sleeper_username",
            "sleeper_url",
        ):
            if field in payload:
                session_update[field] = (
                    payload.get(field)
                )

        if "strategy" in payload:
            strategy = str(
                payload.get("strategy") or ""
            ).strip().lower()

            if strategy not in VALID_STRATEGIES:
                self._send_json(
                    400,
                    {"error": "Invalid strategy"},
                )
                return

            session_update[
                "strategy"
            ] = strategy

        session = set_session(
            session_update
        )

        self._send_json(
            200,
            {"ok": True, "session": session},
        )

    def log_message(self, format, *args):
        # Keep localhost HTTP traffic out of the VS Code terminal.
        return


def start_recommendation_server(
    host=HOST,
    port=PORT,
):
    global _server
    global _server_thread

    if _server_thread and _server_thread.is_alive():
        return _server

    _server = ThreadingHTTPServer(
        (host, port),
        RecommendationHandler,
    )

    _server_thread = threading.Thread(
        target=_server.serve_forever,
        daemon=True,
        name="fantasyagent-extension-server",
    )
    _server_thread.start()

    return _server
