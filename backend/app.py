import logging
import os
import pkgutil
import importlib
import uuid

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

log = logging.getLogger('compass')

# The Vite dev server and `vite preview`. Deployments set COMPASS_CORS_ORIGINS to the
# site that serves the frontend ('*' still works, for a public read-only API).
DEFAULT_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173'


def create_app():
    logging.basicConfig(level=os.environ.get('COMPASS_LOG_LEVEL', 'INFO'),
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    app = Flask(__name__)
    app.json.ensure_ascii = False  # Malayalam, Tamil… titles stay readable in responses
    CORS(app, origins=os.environ.get('COMPASS_CORS_ORIGINS', DEFAULT_ORIGINS).split(','),
         supports_credentials=True)
    if os.environ.get('COMPASS_TRUST_PROXY') == '1':
        # Behind nginx/Toolforge's proxy, so the rate limit sees the real client address.
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    from services.wiki import purge_expired_cache
    purge_expired_cache()
    _register_limits(app)
    _register_errors(app)

    import routes
    for _, name, _ in pkgutil.iter_modules(routes.__path__):
        mod = importlib.import_module(f"routes.{name}")
        if hasattr(mod, "bp"):
            app.register_blueprint(mod.bp)

    @app.get('/api/health')
    def health():
        return jsonify({'ok': True})

    _serve_frontend(app)
    return app


def _serve_frontend(app):
    """With COMPASS_STATIC_DIR (the frontend's `dist/`), one server hosts both: files
    are served as they are and every other non-API path gets index.html, so deep links
    such as /u/Ranjithsiji/tasks open the app."""
    static_dir = os.environ.get('COMPASS_STATIC_DIR')
    if not static_dir or not os.path.isdir(static_dir):
        return
    from flask import send_from_directory
    static_dir = os.path.abspath(static_dir)

    @app.get('/', defaults={'path': ''})
    @app.get('/<path:path>')
    def frontend(path):
        if path.startswith('api/'):
            return jsonify({'error': 'Not found'}), 404
        if path and os.path.isfile(os.path.join(static_dir, path)):
            return send_from_directory(static_dir, path)
        return send_from_directory(static_dir, 'index.html')


def _register_limits(app):
    from services.ratelimit import from_env
    limiter = from_env()
    if not limiter:
        return

    @app.before_request
    def limit():
        # Live streams hold one connection open; counting them would only penalise
        # users who keep a tab open.
        if not request.path.startswith('/api/') or request.path.endswith('/stream') or request.method == 'OPTIONS':
            return None
        wait = limiter.check(request.remote_addr or 'unknown')
        if wait:
            resp = jsonify({'error': f'Too many requests. Try again in {wait} s.'})
            resp.status_code = 429
            resp.headers['Retry-After'] = str(wait)
            return resp
        return None


def _register_errors(app):
    """User-facing errors (no such user, no edits on that wiki) are raised as UserError
    and returned with their message (404, or 400 for a malformed request). Anything else is logged with an id and the
    client only gets the id, not internal URLs or tracebacks."""

    from services.wiki import UserError

    @app.errorhandler(UserError)
    def user_error(e):
        return jsonify({'error': str(e)}), e.status

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify({'error': e.description}), e.code

    @app.errorhandler(Exception)
    def server_error(e):
        error_id = uuid.uuid4().hex[:8]
        log.exception('error %s on %s %s', error_id, request.method, request.full_path)
        return jsonify({'error': f'Something went wrong (error {error_id}). Please try again.',
                        'errorId': error_id}), 500


if __name__ == "__main__":
    create_app().run(
        debug=os.environ.get('FLASK_DEBUG') == '1',
        host=os.environ.get('COMPASS_HOST', '127.0.0.1'),
        port=int(os.environ.get('COMPASS_PORT', 5000)),
        threaded=True,
    )
