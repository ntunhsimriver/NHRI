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
    full_name = db.Column(db.String(100))
    organization = db.Column(db.String(100))
    role = db.Column(db.Enum(UserRole, name="user_role_enum"), nullable=False)
    fhir_practitioner_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

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
