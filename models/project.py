# models/history.py
import uuid
from datetime import datetime
from extensions import db

class Project(db.Model):
    __tablename__ = "Project_Management"

    irb_number = db.Column(db.String(50), primary_key=True) # [PK] character varying(50)
    name = db.Column(db.String(255), nullable=False) #計畫名稱
    pi_id = db.Column(db.Text, db.ForeignKey('users.fhir_practitioner_id')) # 關聯到您之前的 User 模型
    fhir_study_id = db.Column(db.String(64)) # 對應 FHIR 資源的 ID
    status = db.Column(db.String(64), default='ACTIVE') # 狀態
    dataType = db.Column(db.String(255), nullable=False) #計畫名稱
    Del = db.Column(db.SmallInteger, default=0)
    Assistant = db.Column(db.Text)
    device_list = db.Column(db.Text)

    # def to_dict(self):
    #     return {
    #         "index": self.index,
    #         "id": self.id,
    #         "applicant": self.applicant,
    #         "project": self.project,
    #         "createdAt": int(self.created_at.timestamp()*1000),
    #         "resultCount": self.result_count,
    #     }

class ProjectMember(db.Model):
    __tablename__ = "project_member"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Text, nullable=False)
    old_patient_id = db.Column(db.Text, nullable=False)
    new_patient_id = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    Del = db.Column(db.SmallInteger, nullable=True)   # NULL = 還活著