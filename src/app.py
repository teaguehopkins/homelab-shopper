import logging
import os
import secrets
from flask import Flask, render_template, jsonify, request
import requests
from werkzeug.exceptions import HTTPException

from src.config import load_config
from src.routes.search import search_bp
from src.logging_setup import configure as _configure_logging

# Ensure logging is configured before any module-level loggers are created.
_configure_logging()

logger = logging.getLogger(__name__)

def create_app() -> Flask:
    """Flask application factory."""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Register blueprints
    app.register_blueprint(search_bp)

    # ---------------- Security: secret key & cookies -----------------
    # 1. Try explicit environment variable.
    secret_key = os.getenv("SECRET_KEY")

    # 2. Fallback to value in config.yaml (security.secret_key).
    if not secret_key:
        try:
            cfg_tmp = load_config()
            secret_key = cfg_tmp.get('security', {}).get('secret_key')
        except Exception:
            secret_key = None  # on error we just generate a random key

    # 3. Generate a cryptographically-strong key as last resort.
    if not secret_key or secret_key.startswith('${'):
        secret_key = secrets.token_hex(32)

    app.secret_key = secret_key

    # Cookie security settings (honour config.yaml if present)
    app.config.setdefault('SESSION_COOKIE_SECURE', True)
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')

    # ---------------- Error handlers ----------------
    def _json_error_response(message: str, status_code: int = 500):
        """Return a consistent JSON error payload."""
        body = {
            'status': 'error',
            'message': message,
        }
        # For /search endpoint we know frontend expects these extra fields
        if request.path.startswith('/search'):
            body.update({'listings': [], 'total_found': 0})
        return jsonify(body), status_code

    @app.errorhandler(requests.exceptions.RequestException)
    def _handle_requests_error(exc):  # noqa: ANN001
        logger.error("External request error: %s", exc)
        return _json_error_response(f'Upstream request failed: {exc}', 502)

    @app.errorhandler(Exception)
    def _handle_generic_error(exc):  # noqa: ANN001
        logger.exception("Unhandled exception", exc_info=exc)
        status = exc.code if isinstance(exc, HTTPException) else 500  # type: ignore[attr-defined]
        return _json_error_response(str(exc), status)

    @app.errorhandler(404)
    def _handle_404(exc):  # noqa: ANN001
        return _json_error_response('Resource not found', 404)

    @app.errorhandler(405)
    def _handle_405(exc):  # noqa: ANN001
        return _json_error_response('Method not allowed', 405)

    # -------------------------------------------------

    # Jinja filter
    @app.template_filter('price')
    def _format_price(value):  # noqa: D401
        return 'N/A' if value is None else f"${value:,.2f}"

    @app.route('/')
    def index():  # type: ignore
        cfg = load_config()
        full_search_enabled = cfg.get('search', {}).get('full_search', False)
        return render_template('index.html', listings=[], full_search_enabled=full_search_enabled)

    return app


# Export default app for WSGI servers (Gunicorn, etc.)
app = create_app()

if __name__ == '__main__':  # pragma: no cover
    app.run(host='0.0.0.0', port=5000) 