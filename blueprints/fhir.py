from flask import Blueprint, current_app, jsonify, session
from routes.fhir_api import create_fhir_blueprint
from mylib.fhir_client import FHIRClient
from extensions import db
from sqlalchemy import or_
from config import BaseConfig as cfg  
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, date, timedelta
import time
import models.fhir as FHIR 
from models.project import Project, ProjectMember
from models.user import User
from jsonpath_ng import jsonpath, parse
from pydantic import create_model
from collections import Counter
from dateutil.relativedelta import relativedelta
from pathlib import Path
import threading
import secrets
import hashlib
import uuid
from threading import Thread
import shutil




resource_types = [
        "Encounter",
        "Observation",
        "MedicationRequest",
        "Procedure",
        "Condition",
        "DiagnosticReport",
        "Consent",
        "Device"
    ]
def get_token():
    response = requests.post(
            cfg.OAUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": cfg.OAUTH_CLIENT_ID,
                "client_secret": cfg.OAUTH_CLIENT_SECRET,
            },
            verify=cfg.VERIFY_TLS,  
        )
    response.raise_for_status()

    token_json = response.json()
    token = token_json.get('access_token')
    if not token:
        raise ValueError("OAuth 回應裡沒有 access_token")

    headers = {
        'Authorization': f'Bearer {token}',
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    return headers

def register_fhir(app):
    fhir = FHIRClient()  
    app.register_blueprint(create_fhir_blueprint(client=fhir, db=db))


def get_new_patient_id(project_id):
    project_id = str(project_id).strip()

    if not project_id:
        return None
    salt = cfg.PATIENT_ID_SALT
    timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S%f")
    rand_str = secrets.token_hex(8)
    raw = f"{project_id}|{timestamp_str}|{rand_str}|{salt}"
    
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    
    new_uuid = uuid.UUID(bytes=digest[:16])
    return str(new_uuid)



def find_patient_id(pat_identi):
    
    Bundles_Pat = FHIRData_Handle(None, "Patient?identifier=" + pat_identi, 1, 1)[0]
    if Bundles_Pat.BundleResource != None:
        PatInfo = FHIRData_Handle(None, Bundles_Pat.BundleResource, 9, 0)[0] 
        pat_id = PatInfo.id

        return pat_id
    else:
        return None

def read_FHIR_api(Resource, params=None):  
    headers = get_token()
    URL = cfg.FHIR_SERVER_URL + Resource
    
    try:
        res = requests.get(URL, headers=headers, params=params, verify=False, timeout=30)

        if res.status_code != 200:
            return {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "exception",
                        "diagnostics": f"HTTP {res.status_code}: {res.text[:500]}"
                    }
                ]
            }

        if not res.text or not res.text.strip():
            return {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "exception",
                        "diagnostics": "FHIR API returned empty response"
                    }
                ]
            }

        return res.json()

    except Exception as e:
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": "error",
                    "code": "exception",
                    "diagnostics": str(e)
                }
            ]
        }

def put_FHIR_api(id, FHIR): 
    headers = get_token()
    URL = cfg.FHIR_SERVER_URL + id 
    res = requests.put(URL, json=FHIR, headers=headers, verify=False)
    

    return res

def post_FHIR_api(FHIR, resource): 
    headers = get_token()
    URL = cfg.FHIR_SERVER_URL 
    full_url = f"{URL}{resource or ''}"
    res = requests.post(full_url, json=FHIR, headers=headers, verify=False)

    return res



def FHIRData_Handle(resource, SearchURL, CatId, readFlag): 

    getResult = []

    
    if readFlag:
        data = read_FHIR_api(SearchURL)
    else:
        data = SearchURL
    if data is None:
        return []

    
    if resource is not None:
        study_rules = FHIR.FhirMappging.query.filter_by(CatId=CatId, resource=resource, Del=0).all()
    else:
        study_rules = FHIR.FhirMappging.query.filter_by(CatId=CatId, Del=0).all()
    
    field_definitions = {s.name: (object, None) for s in study_rules}
    FHIRModel = create_model('FHIRModel', **field_definitions)
    
    
    compiled_rules = [(s.name, parse(s.fhirpath.replace("[x]", "[*]"))) for s in study_rules]
    
    
    
    if data.get('resourceType') == 'Bundle' and study_rules[0].resource != 'Bundle': 
        bundle_rules = FHIR.FhirMappging.query.filter_by(Id=1).all()
        for row in bundle_rules:
            bundle_expr = parse(row.fhirpath.replace("[x]", "[*]"))
            matches = bundle_expr.find(data)
            
            resource_list = [match.value for match in matches]
    
    
    else:
        
        resource_list = [data]
    
    for res_item in resource_list:
        
        
        extracted_data = {}
        for field_name, expr in compiled_rules:
            found = expr.find(res_item)
            extracted_data[field_name] = [f.value for f in found] if found else []

        
        
        max_len = max([len(v) for v in extracted_data.values()]) if extracted_data else 0

        
        for i in range(max_len):
            temp_dict = {}
            for field_name, values in extracted_data.items():
                
                
                
                
                if i < len(values):
                    temp_dict[field_name] = values[i]
                elif len(values) == 1:
                    temp_dict[field_name] = values[0]
                else:
                    temp_dict[field_name] = None
            
            
            obj = FHIRModel(**temp_dict)
            getResult.append(obj)
    return getResult


def FHIRSearch_Handle(SearchId, SearchData):
    Result = ""
    Flag = 0
    Search = FHIR.FhirMappging.query.filter_by(Id=SearchId).first() 
    Search_List = Search.fhirpath.split(";") 
    for count, s  in enumerate(Search_List):
        if count != 0:
            Result += "&" 
        else:
            Result = Search.resource + "?" 
        if "?" in s:
            s = s.replace('?', SearchData[count]) 
            Flag += 1

        Result += s
    return Result

def FHIR_mappingJson(data, path, value):
    parts = re.findall(r'([^\.\[\]]+)|\[(\d+|\*)\]', path)

    def set_path(current, parts, value):
        for i in range(len(parts)):
            key, index = parts[i]

            if index != '':
                if index == '*':
                    if not isinstance(value, list):
                        raise ValueError("當路徑含 [*] 時，value 必須是 list")

                    result_list = []
                    remaining_parts = parts[i+1:]

                    for item in value:
                        obj = {}
                        set_path(obj, remaining_parts, item)
                        result_list.append(obj)

                    return result_list

                index = int(index)

                while len(current) <= index:
                    current.append({})

                if i == len(parts) - 1:
                    current[index] = value
                else:
                    next_part_is_index = parts[i+1][1] != ''
                    if not current[index]:
                        current[index] = [] if next_part_is_index else {}
                    current = current[index]

            else:
                if i == len(parts) - 1:
                    current[key] = value
                else:
                    next_part_is_index = parts[i+1][1] != ''
                    if key not in current:
                        current[key] = [] if next_part_is_index else {}
                    elif parts[i+1][1] == '*' and key not in current:
                        current[key] = []
                    current = current[key]

        return current

    
    if '[*]' in path:
        star_match = re.match(r'^(.*?)\[\*\](\..+)?$', path)
        if not star_match:
            raise ValueError("不支援的 [*] 路徑格式")

        prefix = star_match.group(1)
        suffix = star_match.group(2) or ""

        if prefix not in data:
            data[prefix] = []

        if not isinstance(value, list):
            raise ValueError("當使用 [*] 時，value 必須是 list")

        for item in value:
            obj = {}
            if suffix.startswith('.'):
                set_path(obj, re.findall(r'([^\.\[\]]+)|\[(\d+|\*)\]', suffix[1:]), item)
            else:
                obj = item
            data[prefix].append(obj)
    else:
        set_path(data, parts, value)

def FHIR_listMapping(data, CatId): 
    result = {}
    study_rules = FHIR.FhirMappging.query.filter_by(CatId=CatId, Del=0).all()
    for count, s in enumerate(study_rules):
        if count == 0: 
            FHIR_mappingJson(result, "resourceType", s.resource)
        if data.get(s.name):
            FHIR_mappingJson(result, s.fhirpath, data[s.name])
    return result

def get_CompleteCount(pat_id):
    completeness = 0
    for resource_type in resource_types:
        url = f"{resource_type}?patient={pat_id}&_count=1"
        
        getCountBundle = FHIRData_Handle(None, read_FHIR_api(url), 1, 0)[0]
        if getCountBundle.BundleResource is not None:
            completeness += 1
    CompleteCount = int(round(completeness / len(resource_types) * 100, 0))

    return CompleteCount

def getDataCount_toSQL(study_id):
    study = FHIRData_Handle(None, FHIRSearch_Handle(10, [study_id]), 5, 1)
    for s in study:
        completeness = 0
        for resource_type in resource_types:
            url = f"{resource_type}?patient={s.pat_id}&_count=1"
            
            getCountBundle = FHIRData_Handle(None, read_FHIR_api(url), 1, 0)[0]
            if getCountBundle.BundleResource is not None:
                completeness += 1
        CompleteCount = int(round(completeness / len(resource_types) * 100, 0))
        ProjectMemberInfo = ProjectMember.query.filter_by(
            new_patient_id=s.pat_id,
            Del=0
        ).first()
        if ProjectMemberInfo is None:
            continue

        ProjectMemberInfo.data_count = CompleteCount
        ProjectMemberInfo.data_count_updated_at = datetime.now()
        db.session.commit()
    return

def get_AllPatient(study_id): 
    getResult = [] 

    study = FHIRData_Handle(None, FHIRSearch_Handle(10, [study_id]), 5, 1)
    for s in study:
        PatInfo = FHIRData_Handle(None, read_FHIR_api(s.pat_id), 9, 0)

        DeviceInfo = FHIRData_Handle(None, FHIRSearch_Handle(42, [s.pat_id]), 6, 1)

        
        ProjectMemberInfo = ProjectMember.query.filter_by(
            new_patient_id=s.pat_id,
            Del=0
        ).first()

        if ProjectMemberInfo is None:
            CompleteCount = 0
            CompleteCount_updated_at = None
        else:
            CompleteCount = ProjectMemberInfo.data_count
            CompleteCount_updated_at = ProjectMemberInfo.data_count_updated_at
        
        
        getResult.append({
                "startDate": s.start,
                "PatInfo": PatInfo[0],  
                "DeviceInfo": DeviceInfo,  
                "ResearchSubjectStatus": s.status,    
                "CompleteCount": CompleteCount,    
                "CompleteCount_updated_at": CompleteCount_updated_at,    
            })


    return getResult

def get_Patient(PatID, study_id): 
    Response = read_FHIR_api("Patient/" + PatID) 
    PatInfo = FHIRData_Handle(None, Response, 9, 0)[0] 

    
    getSubject = FHIRData_Handle(None, FHIRSearch_Handle(43, [PatID,study_id]), 5, 1)[0]

    DeviceInfo = FHIRData_Handle(None, FHIRSearch_Handle(42, [PatID]), 6, 1) 

    FirstDate = getSubject.start
    FirstDate = FirstDate[:10]

    getConsent = FHIRData_Handle(None, FHIRSearch_Handle(49, [getSubject.id]), 10, 1) 

    return PatInfo, FirstDate, getConsent, DeviceInfo

def safe_int(value):
    if value is None:
        return 0
    if value == "":
        return 0
    return int(value)

def countAllData(study_id):
    
    today = datetime.now().strftime("%Y-%m-%d")
    TotlaData = 0
    CountDataList = []

    ProjectInfo = FHIRData_Handle(None, "ResearchSubject?study=ResearchStudy/" + study_id, 5, 1)
    pat_id_list = []
    for item in ProjectInfo:
        pat_id_list.append(item.pat_id)
    if pat_id_list == []:
        return 0, resource_types, [0, 0, 0, 0, 0, 0, 0, 0]
    else:
        pat_str = ",".join(pat_id_list) 
        ProjectInfo = Project.query.filter_by(irb_number=study_id).first()
        device_list = ProjectInfo.device_list
        if device_list:
            device_list_id = "Device/" + device_list.replace(",", ",Device/")
        else:
            device_list_id = ""

        
        for type in resource_types:
            
            if type == "Observation" and device_list_id != "":
                CountData_pat = FHIRData_Handle(None, type + "?patient=" + pat_str +  " &_lastUpdated=" + today + "&_summary=count", 1, 1)[0].SummaryCount
                CountData_device = FHIRData_Handle(None, type + "?device=" + device_list_id +  "&_lastUpdated=" + today + "&_summary=count", 1, 1)[0].SummaryCount
                CountData_all = FHIRData_Handle(None, type + "?device=" + device_list_id + "&patient=" + pat_str + "&_lastUpdated=" + today + "&_summary=count", 1, 1)[0].SummaryCount
                CountData = ( safe_int(CountData_pat) + safe_int(CountData_device) - safe_int(CountData_all))
            else:
                url = type + "?patient=" + pat_str +  "&_lastUpdated=" + today + "&_summary=count"
                CountData = FHIRData_Handle(None, url, 1, 1)[0].SummaryCount
                
            CountDataList.append(CountData)
            TotlaData += int(CountData)
        
        resource_count = [TotlaData, resource_types, CountDataList]
        ProjectInfo.resource_count = json.dumps(resource_count, ensure_ascii=False)
        ProjectInfo.resource_count_updated_at = datetime.now()
        db.session.commit()
        return [TotlaData, resource_types, CountDataList]


def get_IndexProject(study_id):
    getSubjectCount = FHIRData_Handle(None, FHIRSearch_Handle(9, [study_id]), 1, 1)[0].SummaryCount

    
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    months = []
    months_data = []
    total = 0

    for i in range(5, -1, -1):
        
        
        
        start_date = (current_month_start - relativedelta(months=i)).strftime('%Y-%m-%d')
        end_date = (current_month_start - relativedelta(months=i-1)).strftime('%Y-%m-%d')

        months.append(start_date[:7])
        
        

        count = FHIRData_Handle(
                None,
                FHIRSearch_Handle(50, [study_id, start_date, end_date]),
                1, 1
            )[0].SummaryCount
        try:
            total += count
        except:
            pass
        months_data.append(total)
    
    return getSubjectCount, [months, months_data]

def getAssistant(ProjectId): 
    result = []
    
    ProjectInfo = Project.query.filter_by(irb_number = ProjectId).first()

    Assistant_List = ProjectInfo.Assistant.split(';') if ProjectInfo.Assistant not in [None, ''] else []


    Assistant_Info_list = User.query.filter(
        User.role.in_(["ASSISTANT", "PI"]),
        User.Del == 0
    ).order_by(User.role.asc()).all()

    for row in Assistant_Info_list:
        row_data = {
            "id": str(row.id),
            "full_name": row.full_name,   
            "email": row.email,   
            "role": row.role.value,   
            "selected": str(row.id) in Assistant_List
        }
        result.append(row_data)
    
    
    
    
    return result

def get_ProjectID(pi_id):
    UserInfo = User.query.filter_by(fhir_practitioner_id=pi_id, Del=0).first()

    filters = [
        Project.pi_id == pi_id
    ]

    if UserInfo is not None and UserInfo.id is not None:
        filters.append(
            Project.Assistant.contains(str(UserInfo.id))
        )

    ProjectInfo = Project.query.filter(
        or_(*filters)
    ).all()

    result = []
    seen = set()

    for p in ProjectInfo:
        if not p.irb_number:
            continue

        if p.irb_number in seen:
            continue

        seen.add(p.irb_number)

        result.append({
            "study_id": str(p.irb_number),
            "study_name": p.name if hasattr(p, "name") else "",
            "study_status": p.status
        })

    return result

def get_Project(pi_id):
    getResult = [] 
    UserInfo = User.query.filter_by(fhir_practitioner_id=pi_id, Del=0).first()
    ProjectInfo = Project.query.filter(
        or_(
            Project.pi_id == pi_id,
            Project.Assistant.contains(UserInfo.id)
        )
    ).all()
    ids = [str(p.fhir_study_id) for p in ProjectInfo if p.fhir_study_id]

    
    for study_id in ids:
        study = FHIRData_Handle(None, study_id, 2, 1)[0]
        Assistant = getAssistant(study.ProjectId) 

        
        getPIName = FHIRData_Handle(None, study.PI, 3, 1)[0].name
        
        getSubjectCount = FHIRData_Handle(None, FHIRSearch_Handle(9, [ study.ProjectId]), 1, 1)[0].SummaryCount

        getResult.append({
            "study_info": study,  
            "pi_name": getPIName,    
            "SubjectCount": getSubjectCount,    
            "Assistant": Assistant,    
        })

    return getResult
































































































def getObs14days(PatID, DeviceID, start, end): 
    target_codes = "85354-9,8480-6,8462-4,8867-4"

    code_map = {
        '8480-6': 'SBP',
        '8462-4': 'DBP',
        '8867-4': 'HR'
    }

    
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()

    days = (end_date - start_date).days

    sorted_dates = [
        (start_date + timedelta(days=i)).isoformat()
        for i in range(days + 1)
    ]

    
    storage = {
        d: {
            'SBP': [],
            'DBP': [],
            'HR': []
        }
        for d in sorted_dates
    }

    
    for day in sorted_dates:
        rows = []

        try:
            if PatID:
                print("查詢 PatID:", PatID, "日期:", day)

                search_result = FHIRSearch_Handle(
                    16,
                    [PatID, target_codes, day, day, '10']
                )

                rows = FHIRData_Handle(None, search_result, 1, 1)

            elif DeviceID:
                print("查詢 DeviceID:", DeviceID, "日期:", day)

                search_result = FHIRSearch_Handle(
                    55,
                    [DeviceID, target_codes, day, day, '10']
                )

                rows = FHIRData_Handle(None, search_result, 1, 1)

            else:
                rows = []

        except Exception as e:
            print(f"{day} 資料抓取失敗:", e)
            rows = []

        
        for row in rows:
            if row.BundleResource:
                if 'component' in row.BundleResource:
                    result = FHIRData_Handle(None, row.BundleResource, 8, 0)
                else:
                    result = FHIRData_Handle(None, row.BundleResource, 7, 0)

                for r in result:
                    if not getattr(r, "effectiveDateTime", None):
                        continue

                    row_date = r.effectiveDateTime[:10]

                    if row_date in storage:
                        category = code_map.get(r.code)

                        if category:
                            storage[row_date][category].append(r.value)

    final_data = {
        'date': sorted_dates,
        'SBP': [],
        'DBP': [],
        'HR': []
    }

    
    for d in sorted_dates:
        for cat in ['SBP', 'DBP', 'HR']:
            vals = storage[d][cat]

            avg = round(sum(vals) / len(vals), 1) if vals else None

            final_data[cat].append(avg)

    sbp_list = final_data["SBP"]
    dbp_list = final_data["DBP"]
    hr_list = final_data["HR"]

    return sbp_list, dbp_list, hr_list, sorted_dates

def getDeviceCount_toSQL(study_id, new_device_id=None):
    result = []

    ProjectInfo = Project.query.filter_by(irb_number=study_id).first()

    if ProjectInfo is None:
        print("找不到 ProjectInfo:", study_id)
        return result

    device_data = []

    if ProjectInfo.device_list:
        try:
            device_data = json.loads(ProjectInfo.device_list)

            if not isinstance(device_data, list):
                device_data = []

        except Exception as e:
            print("device_list 不是 JSON list:", e)
            device_data = []

    device_ids = [
        device.get("device_id")
        for device in device_data
        if isinstance(device, dict) and device.get("device_id")
    ]

    if new_device_id and new_device_id not in device_ids:
        device_ids.append(new_device_id)

    
    device_ids = list(dict.fromkeys(
        str(device_id).strip()
        for device_id in device_ids
        if device_id and str(device_id).strip()
    ))

    if len(device_ids) == 0:
        print("沒有 device_id，不更新")
        return result

    device_list = ",".join(device_ids)

    getFHIR = FHIRData_Handle(
        None, f"Device?_id={device_list}&_sort=patient&_sort=status&_count=100", 6, 1
    )

    for device in getFHIR:
        countData = FHIRData_Handle(
            None, f"Observation?device=Device/{device.id}&_summary=count", 1, 1
        )[0].SummaryCount

        result.append({
            "device_id": device.id,
            "count": countData
        })

    status_counts = Counter(
        label
        for item in getFHIR
        for label in ([item.status] + (["foundPat"] if item.pat_id else []))
        if label
    )

    status_counts["foundPat"] = status_counts.get("foundPat", 0)

    if len(result) > 0:
        ProjectInfo.device_list = json.dumps(result, ensure_ascii=False)
        ProjectInfo.device_list_updated_at = datetime.now()
        ProjectInfo.device_count = json.dumps(dict(status_counts), ensure_ascii=False)
        ProjectInfo.device_count_updated_at = datetime.now()

        db.session.commit()
        print("device_list / device_count 更新完成")
    else:
        print("FHIR 沒有查到 device，不更新 DB")

    return result
def getDevice(study_id):
    getResult = [] 
    ProjectInfo = Project.query.filter_by(irb_number=study_id).first()
    try:
        device_data = json.loads(ProjectInfo.device_list)
        device_ids = [device["device_id"] for device in device_data]
        device_list = ",".join(device_ids)
    except:
        device_data = []
        device_list = "None"
    

    
    getFHIR = FHIRData_Handle(None, 'Device?_id=' + str(device_list) + '&_sort=patient&_sort=status&_count=100', 6, 1)
    for device in getFHIR:
        device_dict = device.model_dump() if hasattr(device, 'model_dump') else device.dict()
        countData = next(
            (device["count"] for device in device_data if device["device_id"] == device_dict['id']),
            0
        )
        device_dict['countData'] = countData
        getResult.append(device_dict)
        
    
    try:
        status_counts = json.loads(ProjectInfo.device_count)
        status_counts_updated_at = ProjectInfo.device_count_updated_at
    except:
        status_counts = {}
        status_counts_updated_at = None
    return [getResult, len(getFHIR), status_counts, status_counts_updated_at]

def getDeviceCount(study_id):
    getResult = [] 
    ProjectInfo = Project.query.filter_by(irb_number=study_id).first()

    try:
        device_data = json.loads(ProjectInfo.device_list)
    except:
        device_data = []
    device_ids = [device["device_id"] for device in device_data]
    device_list = ",".join(device_ids)
    try:
        status_counts = json.loads(ProjectInfo.device_count)
    except:
        status_counts = {}
    

    return [len(device_ids), status_counts]


def update_device_history(device_id, patient_id, note=None):

    now_time = datetime.now()

    old_history = FHIR.device_history.query.filter_by(
        device_id=device_id,
        status="active"
    ).filter(
        FHIR.device_history.end_datetime.is_(None)
    ).first()

    
    if patient_id == "":
        if old_history:
            old_history.end_datetime = now_time
            old_history.status = "ended"
            if note:
                old_history.note = note
        db.session.commit()
        return True

    
    if not old_history:
        new_history = FHIR.device_history(
            device_id=device_id,
            patient_id=patient_id,
            start_datetime=now_time,
            end_datetime=None,
            status="active",
            note=note
        )
        db.session.add(new_history)
        db.session.commit()
        return True

    
    if old_history.patient_id == patient_id:
        return True

    
    old_history.end_datetime = now_time
    old_history.status = "ended"

    new_history = FHIR.device_history(
        device_id=device_id,
        patient_id=patient_id,
        start_datetime=now_time,
        end_datetime=None,
        status="active",
        note=note
    )
    db.session.add(new_history)
    db.session.commit()

    return True
def run_getDeviceCount_toSQL(app, study_id, device_id):
    with app.app_context():
        try:
            getDeviceCount_toSQL(study_id, device_id)

        except Exception as e:
            db.session.rollback()

        finally:
            db.session.remove()
def addDevice_FHIR(data, study_id):
    pat_id = data['pat_id']
    
    result = FHIR_listMapping(data, 6)
    Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)
    app = current_app._get_current_object()

    thread = Thread(
        target=run_getDeviceCount_toSQL,
        args=(app, study_id, data['id'])
    )
    thread.daemon = True
    thread.start()

    update_device_history(
        device_id=data['id'],
        patient_id=pat_id,
        note=""
    )

    return True, Response


def upload_FHIR(data):
    
    getFHIR = FHIRData_Handle(None, data, 1, 0)
    getFirstInfo = getFHIR[0] 
    if getFirstInfo.type == "transaction":
        res = post_FHIR_api(data, "") 
    else:
        if 'id' in data:
            res = put_FHIR_api(getFirstInfo.resourceType + '/' + getFirstInfo.id, data)
        else:
            res = post_FHIR_api(data, getFirstInfo.resourceType) 
    
    return res

def merge_to_simple_json(q_data, r_data):
    
    q_map = {item['linkId'].lower(): item for item in q_data.get('item', [])}
    
    merged_results = []

    
    for resp_item in r_data.get('item', []):
        link_id_lower = resp_item['linkId'].lower()
        question = q_map.get(link_id_lower)
        
        if not question:
            continue

        simple_answers = []
        for ans in resp_item.get('answer', []):
            
            raw_val = list(ans.values())[0]
            
            
            display_text = str(raw_val)
            if question.get('type') == 'choice':
                options = question.get('answerOption', [])
                for opt in options:
                    coding = opt.get('valueCoding', {})
                    if str(coding.get('code')) == str(raw_val):
                        display_text = coding.get('display')
                        break
            
            
            simple_answers.append(display_text)

        
        merged_results.append({
            "linkId": question['linkId'],    
            "text": question['text'],        
            "answers": simple_answers        
        })

    return merged_results

def getQA(pat_id):
    result = []
    BundleInfo = FHIRData_Handle(None, 'QuestionnaireResponse?subject=Patient/' + pat_id + '&_sort=-authored', 1, 1)
    for bundle in BundleInfo:
        result_list = {}
        r_json = bundle.BundleResource
        if not r_json:
            continue
        q_json = read_FHIR_api(r_json['questionnaire'])
        q_map = {item['linkId'].lower(): item for item in q_json.get('item', [])}
        qa_list = merge_to_simple_json(q_json, r_json)
        
        result_list['Q_id'] = r_json['questionnaire']
        result_list['A_id'] = 'QuestionnaireResponse' + r_json['id']
        result_list['QA'] = qa_list
        result_list['status'] = r_json['status']

        result.append(result_list)
    return result

def addProject_FHIR(data, pra_id):

    ProjectId = data.get('ProjectId')
    type = data.get('type')
    
    existing_project = Project.query.filter_by(irb_number=ProjectId).first()
    
    if existing_project and type =="new":
        
        return {"success": False, "message": f"IRB編號 {ProjectId} 已存在"}

    data['PI'] = pra_id 
    result = FHIR_listMapping(data, 2)


    ProjectName = data.get('ProjectName')
    ProjectStatus = data.get('ProjectStatus')
    PI = pra_id
    dataType = data.get('dataType')
    fhir_study_id = 'ResearchStudy/' + ProjectId

    Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)    
    if Response.ok:
        if type =="new":
            
            new_projecy = Project(irb_number = ProjectId, name = ProjectName, pi_id = pra_id, fhir_study_id = fhir_study_id, status = ProjectStatus, dataType = dataType)
            db.session.add(new_projecy)
            db.session.commit()
            return {'success': True, 'message': '已新增成功'}
        else:

            existing_project.name = ProjectName
            existing_project.status = ProjectStatus
            existing_project.dataType = dataType

            session['study_name'] = ProjectName
            session['study_status'] = ProjectStatus

            db.session.commit()
            return {'success': True, 'message': '已更新成功'}
        
    else:
        return {"success": False, "message": result.text}



def addPatient_FHIR(data, study_id):
    type = data.get('type')


    pat_id = data.get('pat_id')

    if pat_id != None:
        inputResSub = {
            'pat_id': "Patient/" + pat_id,
            'start': data.get('start'),
            'id': study_id + '-' + pat_id,
            'status': data.get('status'),
            'studyId': "ResearchStudy/" + study_id
        }

        inputPat = {
            'id': pat_id,
            'birthDate': data.get('birthDate'),
            'gender': data.get('gender'),
        }
        ResearchSubject_rules = FHIR.FhirMappging.query.filter_by(CatId=5, Del=0).all()

        if type == 'new': 
            result = FHIR_listMapping(inputPat, 9)
            Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result) 
        result = FHIR_listMapping(inputResSub, 5)
        Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)  

        return Response
    else:
        return None

def upload_Consent(study_id, pat_id, filename):

    
    getSubject = FHIRData_Handle(None, FHIRSearch_Handle(43, [pat_id,study_id]), 5, 1)[0] 

    data = {
        "status": "active",
        "pat_id": "Patient/" + pat_id,
        "subjectId": "ResearchSubject/" + getSubject.id,
        "url":  '/' + study_id + '-' + pat_id + '/' + filename,
        "dateTime": datetime.now().strftime('%Y-%m-%d'),
    }
    result = FHIR_listMapping(data, 10)

    

    res = post_FHIR_api(result, 'Consent')
    

    return res


def get_DevicePatient(pat_id, study_id):

    Response = read_FHIR_api("Patient/" + pat_id) 
    PatInfo = FHIRData_Handle(None, Response, 9, 0)[0] 
    
    return PatInfo


def getAllEncounter(pat_id):

    EncBundle = FHIRData_Handle(None, "Encounter?_sort=-date&patient=Patient/" + pat_id, 1, 1)
    
    result = []
    for e in EncBundle:
        
        enc_data = FHIRData_Handle(None, e.BundleResource, 11, 0)
        
        result.extend(e.model_dump() for e in enc_data)
    
    return result

def getAllTreatment(pat_id, needType):
    result = []

    for n in needType:

        Bundles = FHIRData_Handle(None, n + "?_sort=-date&patient=Patient/" + pat_id, 1, 1)

        for b in Bundles:
            if not b.BundleResource:
                continue

            resource_type = b.BundleResource['resourceType']
            ResultData = FHIRData_Handle(resource_type, b.BundleResource, 13, 0)

            for model in ResultData:
                row = model.__dict__.copy()
                row["type"] = resource_type
                result.append(row)

    result_sorted = sorted(
        result,
        key=lambda x: x["date"] or "",
        reverse=True
    )
    return result_sorted


def getEnc(enc_id):

    result = {}

    EncBundle = FHIRData_Handle(None, "Encounter/" + enc_id + "/$everything", 1, 1)

    for e in EncBundle:
        resource_type = e.BundleResource['resourceType']
        if resource_type in ['Patient', 'Encounter']:
            continue
        ResultData = FHIRData_Handle(resource_type, e.BundleResource, 12, 0)
        if resource_type not in result:
            result[resource_type] = []
        result[resource_type].extend([model.__dict__ for model in ResultData])

    return result

def run_export(ProjectId, result, zip_password):
    put_FHIR_api(result['resourceType'] + "/" + result['id'], result)
    Export_data(ProjectId, result['resourceType'] + "/" + result['id'], zip_password)

def getBULK(ProjectId, zip_password):
    ProjectInfo = FHIRData_Handle(None, "ResearchSubject?study=ResearchStudy/" + ProjectId, 5, 1)
    
    pat_id_list = []
    for item in ProjectInfo:
        pat_id_list.append(item.pat_id)
    if pat_id_list == []:
        return jsonify({
            "success": False,
            "message": "無資料可匯出",
            "project_id": ProjectId
        }), 202
    else:
        today = datetime.now()
        data = {
            "pat_id": pat_id_list,
            "actual": "true",
            "type": "person",
            "date": today.strftime("%Y-%m-%dT%H:%M:%S"),
            "id": ProjectId + "-" + today.strftime("%Y%m%d"),
        }
        result = FHIR_listMapping(data, 14)

        
        t = threading.Thread(target=run_export, args=(ProjectId, result, zip_password))
        t.start()

        
        return jsonify({
            "success": True,
            "message": "匯出已開始",
            "project_id": ProjectId
        }), 202


def Export_data(ProjectId, GroupId, zip_password):
    """啟動 $export，輪詢，下載 NDJSON；全程回傳可偵錯的 JSON"""
    def get_token():
        resp = requests.post(
            cfg.OAUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": cfg.OAUTH_CLIENT_ID,
                "client_secret": cfg.OAUTH_CLIENT_SECRET,
            },
            timeout=cfg.REQUEST_TIMEOUT, #requests 逾時秒數  30sec
            verify=cfg.VERIFY_TLS,  
        )
        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return None, {"ok": False, "stage": "oauth", "http": getattr(resp, "status_code", None),
                          "message": f"取得 token 失敗: {e}", "text": getattr(resp, "text", "")}
        return data.get("access_token"), {"ok": True, "stage": "oauth"}

    
    token, odebug = get_token()
    if not token:
        return odebug

    FHIR_BASE = cfg.FHIR_SERVER_URL.rstrip("/") + "/" + GroupId + "/"
    headers = {
        "Prefer": "respond-async",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/fhir+json"
    }

    
    try:
        r = requests.get(FHIR_BASE + "$export", headers=headers,
                         timeout=cfg.REQUEST_TIMEOUT, verify=cfg.VERIFY_TLS)
    except Exception as e:
        return {"ok": False, "stage": "kickoff", "message": f"$export 請求失敗: {e}"}

    kickoff_info = {
        "status": r.status_code,
        "content_location": r.headers.get("Content-Location"),
        "body_sample": r.text[:500]
    }
    if r.status_code != 202:
        return {"ok": False, "stage": "kickoff", "http": r.status_code,
                "message": "啟動 $export 未回 202，請確認伺服器是否支援或權限是否足夠",
                "detail": kickoff_info}

    job_url = r.headers.get("Content-Location")
    if not job_url:
        return {"ok": False, "stage": "kickoff", "http": r.status_code,
                "message": "未收到 Content-Location（工作查詢網址）", "detail": kickoff_info}

    
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = cfg.NDJSON_DIR
    out_root.mkdir(parents=True, exist_ok=True)
    folder_pro = out_root / f"{ProjectId}"
    folder_pro.mkdir(exist_ok=True)
    folder = folder_pro / ts
    folder.mkdir(exist_ok=True)
    (folder / "JobId.txt").write_text(job_url, encoding="utf-8")
    (folder / "zip_password.txt").write_text(zip_password, encoding="utf-8")

    last = {}
    while True:
        try:
            
            token, _ = get_token()
            if not token:
                return {"ok": False, "stage": "poll", "message": "輪詢時重新取得 token 失敗"}
            headers["Authorization"] = f"Bearer {token}"

            p = requests.get(job_url, headers=headers,
                             timeout=cfg.REQUEST_TIMEOUT, verify=cfg.VERIFY_TLS)
            last = {"status": p.status_code, "body_sample": p.text[:500]}
            if p.status_code == 202:
                time.sleep(cfg.POLL_INTERVAL)
                continue
            if p.status_code != 200:
                return {"ok": False, "stage": "poll", "http": p.status_code,
                        "message": "輪詢未完成或發生錯誤", "detail": last}
            
            result = p.json()
            break
        except Exception as e:
            time.sleep(cfg.POLL_INTERVAL)

    if not isinstance(result, dict) or "output" not in result:
        return {"ok": False, "stage": "poll", "message": "完成回應缺少 output", "detail": result}

    

    files = []
    for i, item in enumerate(result["output"], start=1):
        try:
            token, _ = get_token()
            if not token:
                return {"ok": False, "stage": "download", "message": "下載前取得 token 失敗"}
            h = {"Authorization": f"Bearer {token}", "Accept": "application/x-ndjson"}
            nd = requests.get(item["url"], headers=h,
                              timeout=max(cfg.REQUEST_TIMEOUT, 60),
                              verify=cfg.VERIFY_TLS)
            if nd.status_code == 200:
                path = folder / f"{i}_{item['type']}.ndjson"
                path.write_bytes(nd.content)
                files.append(path.name)
            else:
                return {"ok": False, "stage": "download", "http": nd.status_code,
                        "message": f"下載 {item.get('type')} 失敗", "url": item.get("url")}
        except Exception as e:
            return {"ok": False, "stage": "download", "message": f"下載異常: {e}"}
    (folder / "OK.txt").write_text("OK", encoding="utf-8")
    return {
        "ok": True,
        "stage": "done",
        "folder": str(folder.resolve()),
        "ndjson_count": len(files),
        "ndjson_files": files[:10],  
        "job_url": job_url
    }

def get_latest_export_status(project_id):
    base_folder = Path(cfg.NDJSON_DIR) / project_id
    
    if not base_folder.exists():
        return []

    subfolders = [f for f in base_folder.iterdir() if f.is_dir()]

    results = []

    for sub in subfolders:
        files = list(sub.iterdir())

        job_file = sub / "JobId.txt"
        OK_file = sub / "OK.txt"
        ndjson_files = [f for f in files if f.suffix == ".ndjson"]

        
        if not files:
            status = "empty"
            status_text = "資料夾為空"

        elif job_file.exists() and not ndjson_files:
            status = "running"
            status_text = "執行中"

        elif OK_file.exists() and ndjson_files:
            status = "completed"
            status_text = "已完成"

        else:
            status = "error"
            status_text = "異常"

        
        last_updated = datetime.fromtimestamp(sub.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        results.append({
            "project_id": project_id,
            "folder": sub.name,
            "status": status,
            "status_text": status_text,
            "countData": len(ndjson_files),
            "lastUpdated": last_updated
        })

    
    results.sort(key=lambda x: x["folder"], reverse=True)

    return results


def cleanup_old_export_folders(project_id, days=90):
    base_folder = Path(cfg.NDJSON_DIR) / project_id

    
    if not base_folder.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(days=days)
    deleted_count = 0

    for sub in base_folder.iterdir():
        
        if not sub.is_dir():
            continue

        sub_mtime = datetime.fromtimestamp(sub.stat().st_mtime)

        
        if sub_mtime < cutoff_time:
            shutil.rmtree(sub)
            deleted_count += 1
            print(f"[CLEANUP] 已刪除超過 {days} 天的匯出資料夾：{sub}")

    return deleted_count

def cleanup_all_old_export_folders(days=90):
    base_folder = Path(cfg.NDJSON_DIR)

    if not base_folder.exists():
        return 0

    total_deleted = 0

    for project_folder in base_folder.iterdir():
        if not project_folder.is_dir():
            continue

        project_id = project_folder.name
        total_deleted += cleanup_old_export_folders(project_id, days=days)

    print(f"[CLEANUP] 共刪除 {total_deleted} 個超過 {days} 天的匯出資料夾")
    return total_deleted