import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

class BaseConfig:

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "secretData")
    # SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///data.db")
    SQLALCHEMY_DATABASE_URI = ("postgresql+psycopg2://postgres:1qaz2wsx@localhost:5432/THBCNHRI") # 這邊改成用PosrgreSQL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JSON
    JSON_LIST_PATH = os.getenv(
    "JSON_LIST_PATH",
    os.path.join(os.path.dirname(__file__), "data", "options.json")
    )

    JSON_UPLOAD_DIR = os.getenv(
        "JSON_UPLOAD_DIR",
        os.path.join(os.path.dirname(__file__), "data", "uploads")
    )
    
    JSON_PRESET_DIR = os.getenv(
        "JSON_PRESET_DIR",
        os.path.join(os.path.dirname(__file__), "data", "presets")
    )

    PROJECT_CONFIG_DIR = os.getenv(
        "PROJECT_CONFIG_DIR",
        os.path.join(os.path.dirname(__file__), "data", "project_configs")
    )

    TEMPLATE_DIR = os.getenv(
        "TEMPLATE_DIR",
        os.path.join(os.path.dirname(__file__), "data", "templates")
    )
    SELECTION_DIR = os.getenv(
        "SELECTION_DIR",
        os.path.join(os.path.dirname(__file__), "data", "selections")
    )

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))  # 2MB 上限

    # Server
    HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT = int(os.getenv("FLASK_PORT", "3001"))
    DEBUG = (
        "--debug" in os.getenv("FLASK_CMDLINE", "")
        or os.getenv("FLASK_ENV", "").strip().lower() == "development"
        or os.getenv("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on")
    )

    #fhir config 
    # 後端位址（可被環境變數覆蓋，沒有就用預設）
    Trans_FHIR       = os.getenv("Trans_FHIR", "https://fhir.com.tw/GroundFHIRtest/api/FHIRtransAPItest/FHIRtrans") # 土撥鼠的API
    OAUTH_URL        = os.getenv("OAUTH_URL", "http://103.124.73.31:8888/realms/HAPI/protocol/openid-connect/token")
    FHIR_SERVER_URL  = os.getenv("FHIR_SERVER_URL", "http://localhost:8080/hapi-fhir-jpaserver-starter/fhir/")
    OAUTH_CLIENT_ID  = os.getenv("OAUTH_CLIENT_ID", "oauth_tools")
    OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "auEtGIPotzMP3thaVI1VD1xeFkAtX2FV")  # ⚠️ 正式環境建議用環境變數覆蓋
    VERIFY_TLS = os.getenv("VERIFY_TLS", "true").lower() != "false"  # 自簽憑證可設 false
    NDJSON_DIR = Path(os.getenv("NDJSON_DIR", BASE_DIR / "static/data/data_ndjson"))
    NDJSON_DIR.mkdir(parents=True, exist_ok=True)

    REQUEST_TIMEOUT=30          # requests 逾時秒數
    POLL_INTERVAL=20     # $export 輪詢間隔秒
    PROXY_CHUNK_SIZE = int(os.getenv("PROXY_CHUNK_SIZE", "8192"))
    BASE_DIR_STAC = BASE_DIR / "static"
    # # ===== Aggregate Table 路徑設定 =====
    # DATA_NDJSON_DIR = BASE_DIR / "static" / "data" / "data_ndjson"

    # # 找出最新的資料夾
    # if DATA_NDJSON_DIR.exists():
    #     subfolders = [f for f in DATA_NDJSON_DIR.iterdir() if f.is_dir()]
    #     if subfolders:
    #         AGGREGATE_FOLDER_PATH = str(max(subfolders, key=os.path.getctime))
    #     else:
    #         AGGREGATE_FOLDER_PATH = str(DATA_NDJSON_DIR)  # fallback
    # else:
    #     AGGREGATE_FOLDER_PATH = str(DATA_NDJSON_DIR)  # fallback

    # # Agg_tables 資料夾
    # AGGREGATE_TARGET_FOLDER = BASE_DIR / "static" / "data" / "Agg_tables"
    # Path(AGGREGATE_TARGET_FOLDER).mkdir(parents=True, exist_ok=True)
    # AGGREGATE_TARGET_FOLDER = str(AGGREGATE_TARGET_FOLDER)