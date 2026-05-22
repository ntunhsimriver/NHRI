import os
import sys
import signal
import time
import uuid

from flask import Flask, render_template, g, request, jsonify, current_app
from config import BaseConfig as cfg
from extensions import db
from blueprints.fhir import register_fhir, cleanup_all_old_export_folders
from blueprints.pages import bp as pages_bp
from blueprints.auth import bp as auth_bp
from blueprints.api_watch import bp as api_watch_bp
import secrets
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.security import generate_password_hash
from models.user import User, UserRole


def register_error_handlers(app):

    @app.errorhandler(404)
    def page_not_found(error):
        print(f"Flask 收到 404：{request.path}")

        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "message": "找不到 API"
            }), 404

        return render_template(
            "errors/error.html",
            error_code=404,
            title="找不到頁面",
            message="很抱歉，您要瀏覽的頁面不存在，可能已被移除、網址錯誤或權限不足。",
            error_message=None,
            icon_bg_class="bg-amber-100",
            icon_text_class="text-amber-500",
            header_bg_class="bg-gradient-to-r from-amber-50 to-white",
            code_text_class="text-amber-600"
        ), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        print(f"Flask 收到 500：{request.path}，錯誤：{error}")

        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "message": "系統發生錯誤"
            }), 500

        return render_template(
            "errors/error.html",
            error_code=500,
            title="無法連線至伺服器",
            message="很抱歉，系統目前暫時無法處理您的請求。請稍後再試，或聯絡系統管理員協助確認。",
            error_message=str(error) if current_app.debug else None,
            icon_bg_class="bg-red-100",
            icon_text_class="text-red-500",
            header_bg_class="bg-gradient-to-r from-red-50 to-white",
            code_text_class="text-red-600"
        ), 500

def create_default_admin():
    admin_email = "admin@gmail.com"
    admin_password = "aB12345678!"

    admin = User.query.filter_by(email=admin_email).first()

    if not admin:
        admin_id = uuid.uuid4()

        admin = User(
            id=admin_id,
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            status="true",
            full_name="admin",
            organization="NHRI",
            role=UserRole.SUPER_ADMIN,
            fhir_practitioner_id=f"Practitioner/{admin_id}",
            Del=0
        )

        db.session.add(admin)
        db.session.commit()

        print("👤 已建立預設管理員帳號：admin@gmail.com")
    else:
        print("👤 預設管理員帳號已存在，略過建立")


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')

    app.config.from_object(cfg)
    db.init_app(app)

    @app.before_request
    def generate_nonce():
        g.nonce = secrets.token_urlsafe(16)

    @app.after_request
    def add_csp(response):
        nonce = getattr(g, 'nonce', secrets.token_urlsafe(16))

        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"style-src 'self'; "
            f"img-src 'self' data:; "
            f"font-src 'self' data:; "
            f"connect-src 'self'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"frame-ancestors 'self'; "
            f"object-src 'none';"
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_watch_bp)
    register_fhir(app)

    register_error_handlers(app)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: cleanup_all_old_export_folders(days=cfg.CLEAN_FOLDERS_DAYS),
        trigger='cron',
        hour=3,
        minute=0
    )
    scheduler.start()

    def handle_sigterm(signal_number, frame):
        print("🔌 收到 SIGTERM，優雅關閉中...")
        scheduler.shutdown(wait=False)
        time.sleep(1)
        print("✅ Flask 已正常關閉")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    return app


def compute_debug():
    argv = " ".join(sys.argv).lower()

    if "--debug" in argv:
        return True

    if os.getenv("FLASK_ENV", "").strip().lower() == "development":
        return True

    if os.getenv("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on"):
        return True

    return False


app = create_app()


if __name__ == "__main__":
    debug = compute_debug()
    app.config["DEBUG"] = debug

    print(f"🚀 Flask 啟動中（debug={debug}）")

    if debug:
        with app.app_context():
            db.create_all()
            print("📦 已自動建立資料表（開發模式）")
            create_default_admin()

    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=debug
    )