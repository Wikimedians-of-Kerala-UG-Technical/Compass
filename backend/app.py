import pkgutil
import importlib
from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    CORS(app)
    import routes
    for _, name, _ in pkgutil.iter_modules(routes.__path__):
        mod = importlib.import_module(f"routes.{name}")
        if hasattr(mod, "bp"):
            app.register_blueprint(mod.bp)
    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000, threaded=True)
