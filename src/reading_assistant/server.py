"""Loopback demo only. Hosted identity must be supplied by a future integration."""

import secrets
import threading
from importlib.resources import files

import httpx
from flask import Flask, abort, jsonify, request
from jsonschema import ValidationError
from werkzeug.exceptions import HTTPException

from .engine import Recommender, load_catalog


def create_app(catalog=None, audiences=("demo",), model=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=150_000, TRUSTED_HOSTS=["127.0.0.1", "localhost"]
    )
    engine = Recommender(load_catalog(catalog), audiences, model)
    token = secrets.token_urlsafe(32)
    generation_lock = threading.Lock()

    @app.before_request
    def protect():
        if request.remote_addr not in {"127.0.0.1", "::1"}:
            abort(403)
        if request.method == "POST":
            if request.headers.get("X-Reading-Token") != token or not request.is_json:
                abort(403)
            if request.headers.get("Origin") not in {
                None,
                request.host_url.rstrip("/"),
            }:
                abort(403)

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        )
        return response

    @app.errorhandler(Exception)
    def errors(error):
        if isinstance(error, HTTPException):
            return jsonify(error=error.description), error.code
        if isinstance(error, (ValueError, ValidationError, KeyError, TypeError)):
            return jsonify(
                error="Invalid draft or model output. "
                + (
                    str(error)[:200]
                    if isinstance(error, ValueError)
                    else "Check the documented schema."
                )
            ), 400
        if isinstance(error, httpx.HTTPError):
            return jsonify(
                error="Local Ollama request failed. Check that the configured model is installed and the service is running."
            ), 502
        app.logger.error("Reading assistant failed: %s", type(error).__name__)
        return jsonify(error="Request failed; existing writing is unchanged."), 500

    @app.get("/")
    def index():
        return files("reading_assistant").joinpath("web/index.html").read_text()

    @app.get("/app.js")
    def script():
        return app.response_class(
            files("reading_assistant").joinpath("web/app.js").read_text(),
            mimetype="application/javascript",
        )

    @app.get("/state.js")
    def state_script():
        return app.response_class(
            files("reading_assistant").joinpath("web/state.js").read_text(),
            mimetype="application/javascript",
        )

    @app.get("/style.css")
    def style():
        return app.response_class(
            files("reading_assistant").joinpath("web/style.css").read_text(),
            mimetype="text/css",
        )

    @app.get("/api/config")
    def config():
        return jsonify(
            token=token,
            model=model,
            demo_draft=files("reading_assistant").joinpath("demo/draft.md").read_text(),
            sources=len(engine.sources()),
            default_interval=60,
            open_web=False,
        )

    @app.get("/api/sources/<source_id>")
    def source(source_id):
        for item in engine.sources():
            if item["id"] == source_id:
                return jsonify(item)
        abort(404)

    @app.post("/api/recommend")
    def recommend():
        data = request.get_json()
        if not isinstance(data, dict) or set(data) != {"draft"}:
            raise ValueError(
                "Send only a draft field; model and permissions are configured on the server"
            )
        if not generation_lock.acquire(blocking=False):
            return jsonify(error="A recommendation request is already running."), 409
        try:
            return jsonify(engine.recommend(data["draft"]))
        finally:
            generation_lock.release()

    return app
