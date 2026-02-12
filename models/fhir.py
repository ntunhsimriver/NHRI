from extensions import db
from werkzeug.security import check_password_hash
import uuid
import enum
from datetime import datetime, date

class ResourceInfo(db.Model):
    __tablename__ = 'resourceInfo'
    
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ResourceType = db.Column('ResourceType', db.Text)
    Name = db.Column(db.Text)
    Flags = db.Column(db.Text)
    Card = db.Column(db.Text)
    Type = db.Column(db.Text)
    Description = db.Column(db.Text)
    ChineseName = db.Column(db.Text)   
    # Searchable 在 MySQL 是 TINYINT(1)，通常對應 Boolean 或 Integer
    SearchBool = db.Column(db.Integer) 
    ValueSet = db.Column(db.Text)
    Reference = db.Column(db.Text)
    Title = db.Column(db.Text)



class Datatypes(db.Model):
    __tablename__ = 'datatypes'
    
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 以下欄位在 MySQL 皆為 LONGTEXT
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
    Del = db.Column(db.Text)

class FhirMapping_Category(db.Model):
    __tablename__ = 'FhirMapping_Category'
    
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.Text)
    Note = db.Column(db.Text)
    Del = db.Column(db.Text)


class FHIR_Bundle:
    """專門拆解 Bundle 的工具類別"""
    def __init__(self, fhir):
        self.entries = fhir.get("entry", [])
        self.total = fhir.get("total")

class FHIR_ResearchStudy:
    def __init__(self, fhir):
        # 將抓取的資料存成物件的屬性 (Attribute)
        self.resourceType = fhir.get("resourceType")
        self.id = fhir.get("id")
        self.lastUpdated = fhir.get("meta", {}).get("lastUpdated", {})
        self.name = fhir.get("title")
        self.status = fhir.get("status")
        # 處理 PI ID (進階一點的抓法)
        pi_ref = fhir.get("principalInvestigator", {}).get("reference", "")
        self.pi_id = pi_ref


class FHIR_Practitioner:
    def __init__(self, fhir=None):
        if fhir: # 因為要拚Json，所以這邊就預設有讀到FHIR才表示他是要讀資料
            # 將抓取的資料存成物件的屬性 (Attribute)
            self.id = fhir.get("id")
            names = fhir.get("name", []) # 因為名字可能會有多個，就先取use是official的那個
            target_name = next((n for n in names if n.get("use") == "official"), 
                               names[0] if names else {})
            self.name = target_name.get("text", "Unknown")
            telecoms = fhir.get("telecom", [])
            self.phone = "無電話資訊"
            for t in telecoms:
                if t.get("system") == "phone":
                    self.phone = t.get("value")
                    break
    def to_fhir(self):
        # 將物件屬性拼回 FHIR JSON 格式
        fhir_json = {
            "resourceType": "Practitioner",
            "id": self.id,
            "active": True,
            "name": [
                {
                    "use": "official",
                    "text": self.name
                }
            ]
        }
        return fhir_json


class FHIR_Patient:
    def __init__(self, fhir):
        # 將抓取的資料存成物件的屬性 (Attribute)
        self.id = fhir.get("id")
        self.lastUpdated = fhir.get("meta", {}).get("lastUpdated", {})
        names = fhir.get("name", []) # 因為名字可能會有多個，就先取use是official的那個
        target_name = next((n for n in names if n.get("use") == "official"), 
                           names[0] if names else {})
        self.name = target_name.get("text", "Unknown")
        # self.telecoms = fhir.get("telecom", [])
        self.gender = fhir.get("gender")
        self.birthDate = fhir.get("birthDate")
        self.Age = self.getAge(self.birthDate)
        
        # 2. 抓取聯絡電話 (取第一筆 work phone)
        telecoms = fhir.get("telecom", [])
        self.phone = "無電話資訊"
        for t in telecoms:
            if t.get("system") == "phone":
                self.phone = t.get("value")
                break
        # 3. 抓取地址 (格式化成字串)
        addresses = fhir.get("address", [])
        if addresses:
            addr = addresses[0]
            
            # 1. 優先抓取完整的 text 欄位
            full_text = addr.get("text")
            
            if full_text:
                self.address = full_text
            else:
                # 2. 如果沒有 text，才進行手動拼接 (防呆回退機制)
                city = addr.get("city", "")
                district = addr.get("district", "")
                lines = "".join(addr.get("line", []))
                self.address = f"{city}{district}{lines}"
                
                # 如果拼接出來還是空的，給予預設值
                if not self.address.strip():
                    self.address = "地址格式不全"
        else:
            self.address = "無地址資訊"

    # 計算生日
    def getAge(self, bDate):
        birthdate = datetime.strptime(bDate, "%Y-%m-%d").date() 
        today = date.today() # 取今天日期

        return today.year - birthdate.year - (
            (today.month, today.day) < (birthdate.month, birthdate.day) # 處理生日月分跟日期的問題
        )

class FHIR_Organization:
    def __init__(self, fhir):
        self.id = fhir.get("id")        
        # 1. 抓取機構名稱
        self.name = fhir.get("name", "未知醫療機構")
        
        # 2. 抓取聯絡電話 (取第一筆 work phone)
        telecoms = fhir.get("telecom", [])
        self.phone = "無電話資訊"
        for t in telecoms:
            if t.get("system") == "phone":
                self.phone = t.get("value")
                break
        
        # 3. 抓取地址 (格式化成字串)
        addresses = fhir.get("address", [])
        if addresses:
            addr = addresses[0]
            city = addr.get("city", "")
            district = addr.get("district", "")
            lines = "".join(addr.get("line", []))
            self.address = f"{city}{district}{lines}"
        else:
            self.address = "無地址資訊"

    def to_summary(self):
        """ 方便在時間軸下方顯示的小標籤 """
        return f"🏥 {self.name}"


class FHIR_ResearchSubject:
    def __init__(self, fhir):
        # 將抓取的資料存成物件的屬性 (Attribute)
        self.id = fhir.get("id")
        self.lastUpdated = fhir.get("meta", {}).get("lastUpdated", {})
        # self.telecoms = fhir.get("telecom", [])
        self.status = fhir.get("status")
        self.birthDate = fhir.get("birthDate")
        self.pat_id = fhir.get("individual", {}).get("reference", "")
        self.consent = fhir.get("consent", {}).get("reference", "")

class FHIR_Condition:
    def __init__(self, fhir):
        self.id = fhir.get("id")
        self.recordedDate = fhir.get("recordedDate", "Unknown Date")
        
        # 抓取 ICD 代碼與顯示名稱
        coding = fhir.get("code", {}).get("coding", [{}])[0]
        self.code = coding.get("code", "No Code")
        self.display = coding.get("display", "")
        self.text = fhir.get("code", {}).get("text", self.display)
        # 臨床狀態 (Active, Relapse, etc.)
        self.status = fhir.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "unknown")


# 結果Procedure沒用到 先暫時放著
class FHIR_Procedure:
    def __init__(self, fhir):
        self.id = fhir.get("id")
        self.status = fhir.get("status")
        
        # 1. 抓取 Procedure 的名稱 (Code)
        # 優先取 text，若無則取 coding 中的 display
        code_data = fhir.get("code", {})
        self.text = code_data.get("text")
        
        coding = code_data.get("coding", [{}])[0]
        if not self.text:
            self.text = coding.get("display", "Unknown Procedure")
        
        self.system = coding.get("system", "")

        # 2. 處理執行時間 (Performed)
        # Procedure 的時間可能是 performedDateTime 或 performedPeriod
        self.time = fhir.get("performedDateTime")
        if not self.time:
            period = fhir.get("performedPeriod", {})
            self.time = period.get("start") # 如果是區間，取開始時間

        # 3. 處理地點 (Location / Performer)
        performers = fhir.get("performer", [])
        self.performer = "Unknown Hospital"
        if performers:
            # 嘗試抓取執行者或單位的名稱
            actor = performers[0].get("actor", {})
            self.performer = actor.get("display", "Hospital A")


class FHIR_Medication:
    def __init__(self, fhir):
        self.id = fhir.get("id")
        code_data = fhir.get("code", {})
        self.name = code_data.get("text")
        
        coding = code_data.get("coding", [{}])[0]
        if not self.name:
            self.name = coding.get("display", "Unknown Medication")
            
        self.code = coding.get("code")
        self.system = coding.get("system")
        
        # 額外資訊：劑型 (Form)
        self.form = fhir.get("form", {}).get("coding", [{}])[0].get("display", "Tablet")

class FHIR_MedicationRequest:
    def __init__(self, fhir, fhir_server_url=None):
        self.id = fhir.get("id")
        self.status = fhir.get("status")
        self.code = "N/A"         # 預設代碼
        self.system = ""          # 預設系統 (如 RxNorm)
        self.authoredOn = fhir.get("authoredOn")          # 預設系統 (如 RxNorm)
        self.requester = fhir.get("requester", {}).get("reference", "")
        self.dosage_text = fhir.get("dosageInstruction", [{}])[0].get("text", "無用法說明")
        # 1. 先嘗試從本體抓取 CodeableConcept
        med_cc = fhir.get("medicationCodeableConcept")
        
        if med_cc:
            # 解析名稱與代碼
            self.name, self.code, self.system = self._parse_codeable_concept(med_cc)
        else:
            # 2. 如果 CC 是空的，改找 Reference
            med_ref = fhir.get("medicationReference")
            if med_ref:
                self.name =  med_ref.get("reference")
                # 注意：Reference 模式下，本體通常沒有 code，除非 display 裡有寫
            else:
                self.name = "Unknown Medication"

    def _parse_codeable_concept(self, cc):
        """ 解析 CodeableConcept，回傳 (名稱, 代碼, 系統) """
        name = cc.get("text")
        code = "N/A"
        system = ""
        
        codings = cc.get("coding", [])
        if codings:
            first_coding = codings[0]
            # 如果沒有 text，就用 coding 的 display 當名稱
            if not name:
                name = first_coding.get("display", "Unnamed Medication")
            # 抓取代碼與系統
            code = first_coding.get("code", "N/A")
            system = first_coding.get("system", "")
            
        return name, code, system

class FHIR_Observation:
    def __init__(self, fhir):
        self.id = fhir.get("id")
        self.status = fhir.get("status")
        
        # 1. 抓取檢驗名稱 (優先取 text，次之取 coding.display)
        code_data = fhir.get("code", {})
        self.name = code_data.get("text")
        
        codings = code_data.get("coding", [])
        if not self.name and codings:
            self.name = codings[0].get("display", "Unknown Test")
        
        self.code = codings[0].get("code", "N/A") if codings else "N/A"

        self.performer = fhir.get("performer", [{}])[0].get("reference", "")

        # 先抓effectiveDateTime就好
        self.effectiveDateTime = fhir.get("effectiveDateTime")

        # 3. 處理數值與單位 (valueQuantity)
        value_qty = fhir.get("valueQuantity", {})
        self.value = value_qty.get("value")
        self.unit = value_qty.get("unit", "")
        self.value_string = f"{self.value} {self.unit}" if self.value is not None else "No Value"

        # 4. 判斷異常狀態 (Interpretation)
        # 抓取像是 "H" (High) 或 "L" (Low)
        interpret = fhir.get("interpretation", [{}])[0].get("coding", [{}])[0]
        self.interpretation = interpret.get("display") or interpret.get("code")
        
        # 5. 抓取參考範圍 (Reference Range)
        ref_ranges = fhir.get("referenceRange", [])
        if ref_ranges:
            high = ref_ranges[0].get("high", {}).get("value")
            low = ref_ranges[0].get("low", {}).get("value")
            self.ref_text = f"Range: {low if low else ''} - {high if high else ''} {self.unit}"
        else:
            self.ref_text = ""

        # --- 處理 Component ---
        self.components = []
        raw_components = fhir.get("component", [])
        for comp in raw_components:
            self.components.append(FHIR_Component(comp))

class FHIR_Component:
    def __init__(self, comp_fhir):
        # 1. 抓取組件名稱 (例如: Systolic blood pressure)
        code_data = comp_fhir.get("code", {})
        self.name = code_data.get("text")
        
        codings = code_data.get("coding", [])
        if not self.name and codings:
            self.name = codings[0].get("display", "Unknown Component")
            self.code = codings[0].get("code")
        
        # 2. 抓取數值與單位
        value_qty = comp_fhir.get("valueQuantity", {})
        self.value = value_qty.get("value")
        self.unit = value_qty.get("unit", "")
        self.value_string = f"{self.value} {self.unit}" if self.value is not None else "N/A"


class FHIR_Consent:
    def __init__(self, fhir):
        self.id = fhir.get("id")
        self.status = fhir.get("status")
        self.dateTime = fhir.get("dateTime")
        self.pat_id = fhir.get("patient", {}).get("reference", "")
        self.url = fhir.get("sourceAttachment", {}).get("url", "")
        self.title = fhir.get("sourceAttachment", {}).get("title", "")
