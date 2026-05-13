from extensions import db
from werkzeug.security import check_password_hash
import uuid
import enum

class UserRole(enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    PI = "PI"
    ASSISTANT = "ASSISTANT"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.String(100))
    organization = db.Column(db.String(100))
    role = db.Column(db.Enum(UserRole, name="user_role_enum"), nullable=False)
    fhir_practitioner_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    Del = db.Column(db.SmallInteger, default=0)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # 使用 @property 讓它變成一個「虛擬屬性」
    @property
    def roleName(self):
        # 把資料庫的 SUPER_ADMIN 轉成漂亮的人類文字
        role_map = {
            UserRole.SUPER_ADMIN: "超級管理員",
            UserRole.PI: "計畫主持人",
            UserRole.ASSISTANT: "研究助理"
        }
        return role_map.get(self.role, "未知角色")

# 記錄使用者登入資訊
class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(128), unique=True, nullable=False)
    last_activity = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    permission_version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

class LoginFailLog(db.Model):
    __tablename__ = 'login_fail_logs'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    fail_count = db.Column(db.Integer, default=0)
    lock_until = db.Column(db.DateTime, nullable=True)
    last_failed_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)