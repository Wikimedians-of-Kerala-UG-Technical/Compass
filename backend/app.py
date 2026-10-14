import os
import pkgutil
import importlib
from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False  # Malayalam, Tamil… titles stay readable in responses
    CORS(app, origins=os.environ.get('COMPASS_CORS_ORIGINS', '*').split(','))
    import routes
    for _, name, _ in pkgutil.iter_modules(routes.__path__):
        mod = importlib.import_module(f"routes.{name}")
        if hasattr(mod, "bp"):
            app.register_blueprint(mod.bp)
    return app


if __name__ == "__main__":
    create_app().run(
        debug=os.environ.get('FLASK_DEBUG') == '1',
        host=os.environ.get('COMPASS_HOST', '127.0.0.1'),
        port=int(os.environ.get('COMPASS_PORT', 5000)),
        threaded=True,
    )
