from extensions import db
from werkzeug.security import check_password_hash
import uuid
import enum
from datetime import datetime, date
from sqlalchemy import text

class resourceInfo(db.Model):
    __tablename__ = 'resourceInfo'
    
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ResourceType = db.Column('ResourceType', db.Text)
    Name = db.Column(db.Text)
    Flags = db.Column(db.Text)
    Card = db.Column(db.Text)
    Type = db.Column(db.Text)
    Description = db.Column(db.Text)
    ChineseName = db.Column(db.Text)   
    
    SearchBool = db.Column(db.Integer) 
    ValueSet = db.Column(db.Text)
    Reference = db.Column(db.Text)
    Title = db.Column(db.Text)
    MainPatient = db.Column(db.SmallInteger)



class datatypes(db.Model):
    __tablename__ = 'datatypes'
    
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    Datatype = db.Column(db.Text)
    Name = db.Column(db.Text)
    Flags = db.Column(db.Text)
    Card = db.Column(db.Text)
    Type = db.Column(db.Text)
    Description = db.Column(db.Text)
    ValueSet = db.Column(db.Text)
    Reference = db.Column(db.Text)
    Title = db.Column(db.Text)

class FhirMappging(db.Model):
    __tablename__ = 'FhirMappging'
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CatId = db.Column(db.Integer)
    name = db.Column(db.Text)
    fhirpath = db.Column(db.Text)
    resource = db.Column(db.Text)
    Note = db.Column(db.Text)
    Del = db.Column(db.SmallInteger)

class FhirMapping_Category(db.Model):
    __tablename__ = 'FhirMapping_Category'
    
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.Text)
    Note = db.Column(db.Text)
    Del = db.Column(db.SmallInteger)

class device_history(db.Model):
    __tablename__ = "device_history"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.Text, nullable=False)
    patient_id = db.Column(db.Text, nullable=False)
    start_datetime = db.Column(
        db.DateTime,
        server_default=text("timezone('Asia/Taipei', now())"),
        nullable=False
    )
    end_datetime = db.Column(
        db.DateTime,
        nullable=False
    )
    status = db.Column(db.String(20), nullable=False, server_default="active")
    note = db.Column(db.Text, nullable=True)
    
     # 設備所屬計畫
    project_id = db.Column(db.Text, nullable=True)

    # 設備綁定計畫的時間
    project_start_datetime = db.Column(
        db.DateTime,
        nullable=True
    )
    project_end_datetime = db.Column(
        db.DateTime,
        nullable=True
    )

class FHIR_Practitioner:
    def __init__(self, fhir=None):
        if fhir: 
            
            self.id = fhir.get("id")
            names = fhir.get("name", []) 
            target_name = next((n for n in names if n.get("use") == "official"), 
                               names[0] if names else {})
            self.name = target_name.get("text", "Unknown")
            self.active = fhir.get("active")
            telecoms = fhir.get("telecom", [])
            self.phone = "無電話資訊"
            for t in telecoms:
                if t.get("system") == "phone":
                    self.phone = t.get("value")
                    break
    def to_fhir(self):
        
        fhir_json = {
            "resourceType": "Practitioner",
            "id": self.id,
            "active": self.active,
            "name": [
                {
                    "use": "official",
                    "text": self.name
                }
            ]
        }
        return fhir_json
