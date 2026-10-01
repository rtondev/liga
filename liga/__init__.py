import os

from flask import Flask, flash, redirect, render_template, request, url_for
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix

from liga.blueprints import register
from liga.config import Config
from liga.db import init_db
from liga.security import csrf_ok, current_user, ensure_csrf, reject_csrf


def create_app() -> Flask:
    app = Flask(__name__, instance_path=os.path.dirname(Config.DATABASE))
    app.config.from_object(Config)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    init_db(app)
    register(app)

    @app.template_global()
    def csrf_input():
        return Markup(f'<input type="hidden" name="csrf" value="{ensure_csrf()}">')

    @app.context_processor
    def inject():
        user = current_user()
        return {
            "csrf_token": ensure_csrf(),
            "current_user": user,
            "theme": (user or {}).get("theme") or "light",
        }

    @app.before_request
    def protect():
        ensure_csrf()
        if request.method == "POST" and not csrf_ok():
            return reject_csrf()

    @app.errorhandler(404)
    def missing(_error):
        return render_template("main/error.html"), 404

    @app.errorhandler(413)
    def too_big(_error):
        flash("Arquivo grande demais.", "error")
        return redirect(request.referrer or url_for("main.home"))

    return app
