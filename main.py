import os, sys, signal, time
from flask import Flask, render_template, g
from config import BaseConfig
from extensions import db
from flask import send_from_directory
from blueprints.fhir import register_fhir, cleanup_all_old_export_folders
from blueprints.pages import bp as pages_bp
from blueprints.auth import bp as auth_bp
from blueprints.api_watch import bp as api_watch_bp
import secrets
from apscheduler.schedulers.background import BackgroundScheduler # 排程用



def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # 連config用的
    app.config.from_object(BaseConfig)

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

    # 註冊 Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_watch_bp)
    register_fhir(app)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: cleanup_all_old_export_folders(days=cfg.CLEAN_FOLDERS_DAYS),
        trigger='cron',
        hour=3,
        minute=0
    )
    scheduler.start()


    # 優雅關閉
    def handle_sigterm(signal_number, frame):
        print("\U0001F50C 收到 SIGTERM，優雅關閉中...")
        time.sleep(1)
        print("✅ Flask 已正常關閉")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    return app

app = create_app()

# 如果有 errorhandler，也要寫在 app 之後
@app.errorhandler(500)
def handle_500(e):
    return "內部伺服器錯誤 (IIS)", 500


@app.errorhandler(404)
def page_not_found(e):
    # 你可以在這裡 print 一些資訊，它會出現在 WSGI_LOG 裡
    print(f"Flask 收到了一個 404 請求: {e}")
    return "<h1>這是 Flask 丟出的 404 畫面</h1><p>代表 Flask 已經啟動成功了！</p>", 404

if __name__ == "__main__":
    import os, sys
    from extensions import db  # 確保可用

    def compute_debug():
        argv = " ".join(sys.argv).lower()
        if "--debug" in argv:
            return True
        if os.getenv("FLASK_ENV", "").strip().lower() == "development":
            return True
        if os.getenv("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on"):
            return True
        return False

    debug = compute_debug()
    app = create_app()
    app.config["DEBUG"] = debug  # 覆寫 config 裡的預設
    print(f"🚀 Flask 啟動中（debug={debug}）")

    if debug:
        with app.app_context():
            db.create_all()
            print("📦 已自動建立資料表（開發模式）")

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template(
            "errors/500.html",
            error_message=str(error) if current_app.debug else None
        ), 500

    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=debug)

