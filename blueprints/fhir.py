from flask import Blueprint, current_app
from routes.fhir_api import create_fhir_blueprint
from mylib.fhir_client import FHIRClient
from extensions import db
from config import BaseConfig as cfg  # 讀 config
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, date, timedelta
import time
import models.fhir as FHIR # 這邊是抓全部FHIR Resource的Class(就是抓全部欄位的內容)
from models.project import Project
from models.user import User
from jsonpath_ng import jsonpath, parse
from pydantic import create_model
from collections import Counter
from dateutil.relativedelta import relativedelta
from pathlib import Path

# 這個是算資料完整度的list
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
            verify=cfg.VERIFY_TLS,  # $export 輪詢間隔秒  20sec
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
    fhir = FHIRClient()  # 從環境變數讀設定
    app.register_blueprint(create_fhir_blueprint(client=fhir, db=db))

# 這邊是用身份證字號去抓人的id，暫時沒用了
def find_patient_id(pat_identi):
    # 不管它到底有沒有重複，就是取第一個
    Bundles_Pat = FHIRData_Handle(None, "Patient?identifier=" + pat_identi, 1, 1)[0]
    if Bundles_Pat.BundleResource != None:
        PatInfo = FHIRData_Handle(None, Bundles_Pat.BundleResource, 9, 0)[0] # 拿去處理
        pat_id = PatInfo.id

        return pat_id
    else:
        return None

def read_FHIR_api(Resource, params=None):  # 所有get資料都靠他
    headers = get_token()
    URL = cfg.FHIR_SERVER_URL + Resource
    # print(URL)
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

def put_FHIR_api(id, FHIR): # 回傳完整
    headers = get_token()
    URL = cfg.FHIR_SERVER_URL + id # 搜尋條件
    res = requests.put(URL, json=FHIR, headers=headers, verify=False)
    # Response = json.loads(str(res.text)) # 先用不到

    return res

def post_FHIR_api(FHIR, resource): # 回傳完整
    headers = get_token()
    URL = cfg.FHIR_SERVER_URL # 搜尋條件
    full_url = f"{URL}{resource or ''}"
    res = requests.post(full_url, json=FHIR, headers=headers, verify=False)

    return res

# 這邊是改用資料庫的內容處理fhir json
# resource是有些可能會一個Category裡面有很多不同resource，readFlag=1 表示要去抓資料，=0表示是json直接進來
def FHIRData_Handle(resource, SearchURL, CatId, readFlag): 

    getResult = []

    # 1.先抓FHIR資料
    if readFlag:
        data = read_FHIR_api(SearchURL)
    else:
        data = SearchURL
    if data is None:
        return []

    # 1. 取得內層規則 (不管是不是 Bundle，這都要用到)
    if resource is not None:
        study_rules = FHIR.FhirMappging.query.filter_by(CatId=CatId, resource=resource, Del=0).all()
    else:
        study_rules = FHIR.FhirMappging.query.filter_by(CatId=CatId, Del=0).all()
    # 動態建立 Model
    field_definitions = {s.name: (object, None) for s in study_rules}
    FHIRModel = create_model('FHIRModel', **field_definitions)
    
    # 預先編譯內層規則
    compiled_rules = [(s.name, parse(s.fhirpath.replace("[x]", "[*]"))) for s in study_rules]
    # --- 核心邏輯：判斷資料型態 ---
    
    # 情況 A：它是 Bundle，需要先解開 entry
    if data.get('resourceType') == 'Bundle' and study_rules[0].resource != 'Bundle': # 如果
        bundle_rules = FHIR.FhirMappging.query.filter_by(Id=1).all()
        for row in bundle_rules:
            bundle_expr = parse(row.fhirpath.replace("[x]", "[*]"))
            matches = bundle_expr.find(data)
            # 這裡的 match.value 就是裡面的每一筆 Resource
            resource_list = [match.value for match in matches]
    
    # 情況 B：它本身就是一個單獨的 Resource (例如 Patient, ResearchStudy)
    else:
        # 直接包成 list，讓後面的迴圈統一處理
        resource_list = [data]
    # --- 統一處理 Resource ---
    for res_item in resource_list:
        # 1. 先把所有欄位的匹配結果抓出來，存在一個字典裡
        # 這裡的 extracted_data[field_name] 會是一個 list
        extracted_data = {}
        for field_name, expr in compiled_rules:
            found = expr.find(res_item)
            extracted_data[field_name] = [f.value for f in found] if found else []

        # 2. 找出這些欄位中，匹配到最多筆數的是多少 (例如 Bundle entry 有 30 筆)
        # 如果完全沒抓到資料，max_len 會是 0
        max_len = max([len(v) for v in extracted_data.values()]) if extracted_data else 0

        # 3. 用迴圈把每一筆資料「拆解」出來
        for i in range(max_len):
            temp_dict = {}
            for field_name, values in extracted_data.items():
                # 這裡的邏輯：
                # 如果該欄位有多筆，就按 index 取 (i)
                # 如果該欄位只有一筆，就重複使用那一筆 (例如 Patient 名稱)
                # 如果該筆沒資料，就給 None
                if i < len(values):
                    temp_dict[field_name] = values[i]
                elif len(values) == 1:
                    temp_dict[field_name] = values[0]
                else:
                    temp_dict[field_name] = None
            
            # 4. 每一筆 i 都轉換成一個獨立的 Pydantic 物件並存入 getResult
            obj = FHIRModel(**temp_dict)
            getResult.append(obj)
    return getResult

# 處理Search的語法
def FHIRSearch_Handle(SearchId, SearchData):
    Result = ""
    Flag = 0
    Search = FHIR.FhirMappging.query.filter_by(Id=SearchId).first() # 這邊去抓這個search的資訊
    Search_List = Search.fhirpath.split(";") # 用;區分
    for count, s  in enumerate(Search_List):
        if count != 0:
            Result += "&" # 每個查詢參數用&隔開
        else:
            Result = Search.resource + "?" # 因為搜尋要打問號後面才是查詢參數
        if "?" in s:
            s = s.replace('?', SearchData[count]) # 有問號的地方要替代成要查詢的內容
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

    # 特別處理 [*]
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

def FHIR_listMapping(data, CatId): # 放要進去的值的json, 從資料庫裡面取出來的json
    result = {}
    study_rules = FHIR.FhirMappging.query.filter_by(CatId=CatId, Del=0).all()
    for count, s in enumerate(study_rules):
        if count == 0: # 0的時候，可以先把resourceType塞進去
            FHIR_mappingJson(result, "resourceType", s.resource)
        if data.get(s.name):
            FHIR_mappingJson(result, s.fhirpath, data[s.name])
    return result

def get_AllPatient(study_id): 
    getResult = [] # 準備存處理好的Patient資料

    study = FHIRData_Handle(None, FHIRSearch_Handle(10, [study_id]), 5, 1)
    for s in study:
        PatInfo = FHIRData_Handle(None, read_FHIR_api(s.pat_id), 9, 0)

        DeviceInfo = FHIRData_Handle(None, FHIRSearch_Handle(42, [s.pat_id]), 6, 1)

        # 算資料完整度
        completeness = 0
        for resource_type in resource_types:
            url = f"{resource_type}?patient={s.pat_id}&_count=1"
            
            getCountBundle = FHIRData_Handle(None, read_FHIR_api(url), 1, 0)[0]
            if getCountBundle.BundleResource is not None:
                completeness += 1
        CompleteCount = int(round(completeness / len(resource_types) * 100, 0))
        # print(CompleteCount)
        getResult.append({
                "startDate": s.start,
                "PatInfo": PatInfo[0],  # 這裡存的是整個study的資料，他是物件
                "DeviceInfo": DeviceInfo,  # 這裡存這個患者戴的設備
                "ResearchSubjectStatus": s.status,    # 這裡存的是PI名字，他是字串
                "CompleteCount": CompleteCount    # 這裡存每個人的資料完整度
            })


    return getResult

def get_Patient(PatID, study_id): # 同意書可以一起讀
    Response = read_FHIR_api("Patient/" + PatID) # 先抓Patient資料
    PatInfo = FHIRData_Handle(None, Response, 9, 0)[0] # 拿去處理

    # 為了以防他很多筆資料，就抓他最新的一筆(且同一個案件的同一個人底下，只抓最新的一筆) 其他不理她
    getSubject = FHIRData_Handle(None, FHIRSearch_Handle(43, [PatID,study_id]), 5, 1)[0]

    DeviceInfo = FHIRData_Handle(None, FHIRSearch_Handle(42, [PatID]), 6, 1) # 不知道後續會不會帶很多設備

    FirstDate = getSubject.start
    FirstDate = FirstDate[:10]

    getConsent = FHIRData_Handle(None, FHIRSearch_Handle(49, [getSubject.id]), 10, 1) # 抓同意書內容

    return PatInfo, FirstDate, getConsent, DeviceInfo

# 算一下主頁的資料量
# def countAllData(study_id):
def countAllData():
    today = datetime.now().strftime("%Y-%m-%d")
    TotlaData = 0
    CountDataList = []

    # getAllSubject = FHIRData_Handle(None, FHIRSearch_Handle(10, [study_id]), 1, 1)
    # print(getAllSubject[0].BundleResource)
    # for s in getAllSubject:
    #     subject_id = FHIRData_Handle(None, s.BundleResource, 1, 0)[0].id
    
    # 先改成 單純把他的資料量都滾出來，之後想要加邏輯再說
    for type in resource_types:
        # print(read_FHIR_api(Resource, params=None))
        CountData = FHIRData_Handle(None, type + "?_lastUpdated=" + today + "&_summary=count", 1, 1)[0].SummaryCount
        CountDataList.append(CountData)
        TotlaData += int(CountData)

    return TotlaData, resource_types, CountDataList

def get_IndexProject(study_id):
    getSubjectCount = FHIRData_Handle(None, FHIRSearch_Handle(9, [study_id]), 1, 1)[0].SummaryCount

    # 開始抓這個月開始的前六個月，每個月的收案人數
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    months = []
    months_data = []
    total = 0

    for i in range(5, -1, -1):
        # 計算該月的開始與結束日期
        # start_date: 該月 1 號 (ge)
        # end_date: 下個月 1 號 (lt)
        start_date = (current_month_start - relativedelta(months=i)).strftime('%Y-%m-%d')
        end_date = (current_month_start - relativedelta(months=i-1)).strftime('%Y-%m-%d')

        months.append(start_date[:7])
        # months_data.append(FHIRData_Handle(None, FHIRSearch_Handle(50, [study_id, start_date, end_date]), 1, 1)[0].SummaryCount) # 這邊直接建查fhir時候要的格式
        # 收案人數，改成用累計的

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
    # print(months_data)
    return getSubjectCount, [months, months_data]

def getAssistant(ProjectId): # 產出助理清單
    result = []
    # 先讀資料表，確定這個研究案的助理有誰
    ProjectInfo = Project.query.filter_by(irb_number = ProjectId).first()

    Assistant_List = ProjectInfo.Assistant.split(';') if ProjectInfo.Assistant not in [None, ''] else []

    print(Assistant_List)

    Assistant_Info_list = User.query.filter_by(role="ASSISTANT").all()
    print(Assistant_Info_list)

    for row in Assistant_Info_list:
        print(row.id)
        row_data = {
            "id": str(row.id),
            "full_name": row.full_name,   # 建議加
            "email": row.email,   # 建議加
            "selected": str(row.id) in Assistant_List
        }
        result.append(row_data)
    # for row_a in Assistant_List:
    #     Assistant_Info = User.query.filter_by(id=row_a).first()
    #     result.append(Assistant_Info)
    # result = [model.__dict__ for model in result]
    print(result)
    return result


def get_Project(pi_id):
    getResult = [] # 準備存處理好的資料
    study = FHIRData_Handle(None, FHIRSearch_Handle(8, [pi_id]), 2, 1)

    # 抓每一個ResearchStudy
    for b in study:
        Assistant = getAssistant(b.ProjectId) # 這邊先去產助理的清單

        # 從ResearchStudy裡面抓PI的名字(怕之後會跟db裡面的不一樣，所以先再抓一次)
        getPIName = FHIRData_Handle(None, b.PI, 3, 1)[0].name
        # 這邊直接count這個study底下有多少ResearchSubject(因為他一個裡面只能放一個人，所以就直接等於count人)
        getSubjectCount = FHIRData_Handle(None, FHIRSearch_Handle(9, [ b.ProjectId]), 1, 1)[0].SummaryCount

        getResult.append({
            "study_info": b,  # 這裡存的是整個study的資料，他是物件
            "pi_name": getPIName,    # 這裡存的是PI名字，他是字串
            "SubjectCount": getSubjectCount,    # 這裡存的是這個study底下有多少人，他是字串
            "Assistant": Assistant,    # 這裡存這個專案底下的助理有誰
        })

    return getResult

def getAllInfo(PatID): # 還不是新邏輯(但目前也沒有再用了)
    getResult = []
    # 臨床病歷 (Clinical)那頁，總共需要抓Observation、Condition、MedicationRequest

    # 先抓Observation
    Response = read_FHIR_api("/Observation" + "?subject=Patient/" + PatID)

    Bundle_entry = FHIR.FHIR_Bundle(Response)
    for b in Bundle_entry.entries:
        # 【關鍵：特別處理】如果這筆資源含有 component 欄位，就跳過不處理
        if b['resource'].get('component'):
            continue

        Info = FHIR.FHIR_Observation(b['resource'])

        # 抓機構的名字
        Response = read_FHIR_api(Info.performer)
        OrgName = FHIR.FHIR_Organization(Response).name

        effectiveDateTime_raw_date = Info.effectiveDateTime
        effectiveDateTime = effectiveDateTime_raw_date[:10] if effectiveDateTime_raw_date else "0000-00-00"

        getResult.append({
            "Type": "Lb",
            "Name": Info.name,
            "Status": Info.status,
            "Value": str(Info.value) + ' (' + Info.unit + ')',
            "Date": effectiveDateTime,  # 因為effectiveDateTime是datetime所以先改一下日期格式
            "Org": OrgName
        })

    # 再來抓Condition
    Response = read_FHIR_api("/Condition" + "?subject=Patient/" + PatID)

    Bundle_entry = FHIR.FHIR_Bundle(Response)
    for b in Bundle_entry.entries:
        Info = FHIR.FHIR_Condition(b['resource'])

        getResult.append({
            "Type": "Dx",
            "Name": Info.text,
            "Status": Info.status,
            "Value": Info.code,
            "Date": Info.recordedDate,
            "Org": "未知醫療機構"
        })


    # 再來抓MedicationRequest，藥物的code跟name，有可能會放在medicationReference或是medicationCodeableConcept
    Response = read_FHIR_api("/MedicationRequest" + "?subject=Patient/" + PatID)

    Bundle_entry = FHIR.FHIR_Bundle(Response)
    for b in Bundle_entry.entries:
        Info = FHIR.FHIR_MedicationRequest(b['resource'])

        # 抓機構的名字
        Response = read_FHIR_api(Info.requester)
        OrgName = FHIR.FHIR_Organization(Response).name

        if 'Medication/' in Info.name : 
            MedId = Info.name
            Response = read_FHIR_api(Info.name)
            Info_Med = FHIR.FHIR_Medication(Response)

            getResult.append({
                "Type": "Rx",
                "Name": Info_Med.name,
                "Status": Info.status,
                "Value": Info.dosage_text,
                "Date": Info.authoredOn,
                "Org": OrgName
            })
        else:
            getResult.append({
                "Type": "Rx",
                "Name": Info.name,
                "Status": Info.status,
                "Value": Info.dosage_text,
                "Date": Info.authoredOn,
                "Org": OrgName
            })

    # 排序
    getResult = sorted(
        getResult, 
        key=lambda x: (
            x['Date'] in [None, "0000-00-00", "Unknown"], # 空值依然標記為 True (1)
            x['Date'] if x['Date'] else ""               # 確保日期是字串
        ),
        reverse=True # 設定為倒序
    )

    return getResult




def getObs14days(PatID, DeviceID, start, end): 
    # 初始化資料儲存器 (使用字典以確保日期對齊)
    data_map = {} 
    # sorted_dates = []
    code_mapping = {
        '8867-4': 'HR',
        '8480-6': 'SBP',
        '8462-4': 'DBP'
    }

    # 2. 組合 API URL (使用 ge 前綴代表 "大於等於") # 因為14天又有兩個資料，怕到時候資料會很多，先取1000筆，到時候再說
    target_codes = "85354-9,8480-6,8462-4,8867-4"

    # 這邊先抓出所有內容
    if PatID:
        print(str([PatID, target_codes, start, end, '1000']))
        print(FHIRSearch_Handle(16, [PatID, target_codes, start, end, '1000']))
        rows = FHIRData_Handle(None, FHIRSearch_Handle(16, [PatID, target_codes, start, end, '1000']), 1, 1)
    elif DeviceID:
        rows = FHIRData_Handle(None, FHIRSearch_Handle(55, [DeviceID, target_codes, start, end, '1000']), 1, 1)
    # 先把收到的日期轉成date格式
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()
    days = (end_date - start_date).days
    sorted_dates = [
        (start_date + timedelta(days=i)).isoformat()
        for i in range(days + 1)
    ]
    storage = {d: {'SBP': [], 'DBP': [], 'HR': []} for d in sorted_dates}
    code_map = {'8480-6': 'SBP', '8462-4': 'DBP', '8867-4': 'HR'}
    for row in rows:
        if row.BundleResource:
            if 'component' in row.BundleResource:
                result = FHIRData_Handle(None, row.BundleResource, 8, 0)
            else:
                result = FHIRData_Handle(None, row.BundleResource, 7, 0)
            for r in result:
                # 1. 提取日期部分 (取字串前 10 碼: '2026-02-14T08:00:00Z' -> '2026-02-14')
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
    # 3. 轉回對齊的陣列
    sbp_list = final_data["SBP"] 
    dbp_list = final_data["DBP"]
    hr_list = final_data["HR"]
    # print(datetime.now())

    print(sorted_dates)
    return sbp_list, dbp_list, hr_list, sorted_dates


def getDevice(study_id):

    ProjectInfo = Project.query.filter_by(irb_number=study_id).first()
    device_list = ProjectInfo.device_list
    print(ProjectInfo.device_list)


    getResult = [] # 準備存處理好的資料

    # Device清單強制轉str，這樣就算沒有，_id=None也頂多是找不到而已，不會有錯
    getFHIR = FHIRData_Handle(None, 'Device?_id=' + str(device_list) + '&_sort=patient&_sort=status&_count=100', 6, 1)
    for device in getFHIR:
        device_dict = device.model_dump() if hasattr(device, 'model_dump') else device.dict()
        countData = FHIRData_Handle(None, 'Observation?device=Device/' + device.id + '&_summary=count', 1, 1)[0].SummaryCount
        device_dict['countData'] = countData
        getResult.append(device_dict)
        
        print(device)
    # status_counts = Counter(item.status for item in getFHIR)
    status_counts = Counter(
        label
        for item in getFHIR
        for label in ([item.status] + (['foundPat'] if item.pat_id else []))
        if label # 確保 label 不是 None
    )
    # print(status_counts)

    return getResult, len(getFHIR), status_counts

def set_nested_value(dic, path, value):
    """
    根據 'identifier[0].value' 這種路徑自動建立嵌套字典
    """
    if not value: return
    
    keys = path.replace('[', '.').replace(']', '').split('.')
    for key in keys[:-1]:
        if key.isdigit(): # 處理陣列索引
            idx = int(key)
            # 這裡邏輯較複雜，通常建議用現成工具如 dpath 或 glom
            pass 
    # ... (簡化版邏輯)

def addDevice_FHIR(data, study_id):

    # print(data)

    pat_id = find_patient_id(data['pat_id'])

    # if 'Patient/' in data['pat_id'] or data['pat_id'] == "":
    #     print('FHIR')
    # elif re.match(r'^[A-Za-z][0-9]{9}$', data['pat_id']):
    #     pat_id = find_patient_id(data['pat_id'])
    #     if pat_id != None:
    #         data['pat_id'] = 'Patient/' + pat_id
    #     else:
    #         return False, "此身份證字號不存在於FHIR Server"
    # else:
    #     return False, "儲存失敗"
    
    result = FHIR_listMapping(data, 6)
    Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)  

    ProjectInfo = Project.query.filter_by(irb_number=study_id).first()      
    current_list = ProjectInfo.device_list or ""

    device_ids = [d for d in current_list.split(",") if d]
    device_ids.append(data['id'])
    device_ids = list(dict.fromkeys(device_ids))

    ProjectInfo.device_list = ",".join(device_ids)

    db.session.commit()

    return True, Response


def upload_FHIR(data):
    # print(data)
    getFHIR = FHIRData_Handle(None, data, 1, 0)
    getFirstInfo = getFHIR[0] # 取第一個就可以知道最外層的，要先確認他到底是什麼Resource
    print(getFirstInfo)
    if getFirstInfo.type == "transaction":
        res = post_FHIR_api(data, "") # transaction可以直接上傳
    else:
        if 'id' in data:
            res = put_FHIR_api(getFirstInfo.resourceType + '/' + getFirstInfo.id, data)
        else:
            res = post_FHIR_api(data, getFirstInfo.resourceType) # Bundle及其他resource都要加上resourceType
    # print(res.text)
    return res

# 這個是補subject用的，(進來的json, 我的fhir路徑 如subject.reference, 要填進去的值 如Patient/test)
def set_nested_value(data, path, value):
    """
    支援路徑中包含 [*] 的自動填充
    範例：path = 'subject[*].reference'
    """
    parts = path.split('.')
    
    current = data
    for i, key in enumerate(parts):
        # 檢查是否包含 [*]
        if '[*]' in key:
            real_key = key.replace('[*]', '')
            # 確保該鍵值存在且是列表
            if real_key not in current or not isinstance(current[real_key], list):
                current[real_key] = [{}] # 至少建立一個空物件
            
            # 剩餘的路徑遞迴處理
            remaining_path = ".".join(parts[i+1:])
            for item in current[real_key]:
                set_nested_value(item, remaining_path, value)
            return data # 陣列處理完畢，直接返回
            
        # 處理最後一層
        if i == len(parts) - 1:
            current[key] = value
        else:
            # 處理中間層
            current = current.setdefault(key, {})
            
    return data

def findReference(data):
    resourceType = data['resourceType']

    if resourceType == 'Patient':
        return  'Patient'
    else:
        query = FHIR.resourceInfo.query.filter(
            FHIR.resourceInfo.ResourceType == resourceType,
            # FHIR.resourceInfo.Type.like('%Reference(%Patient%'),
            FHIR.resourceInfo.MainPatient == '1'

        )

        resource_info = query.first()
        # if not results:
        #     resource_info = None
        # elif len(results) == 1:
        #     resource_info = results[0]
        # else:
        #     resource_info = next(
        #         (r for r in results if r.MainPatient == 1),
        #         results[0] 
        #     )
        # print(resource_info)
        if resource_info is None:
            return  None
        else:
            # print(resource_info)
            Type = resource_info.Type
            Name = resource_info.Name
            Card = resource_info.Card
            if '*' in Card: # 有*字表示，他是多層
                Name = Name + '[*]'

            # print(Type)

            if 'Reference' in Type:
                PathResult = Name + '.reference'
            elif 'canonical' in Type:
                PathResult = Name
            return PathResult


def upload_FHIR_changeID(pat_id, data):
    just_id = pat_id
    pat_id = f"Patient/{pat_id}" # 先拼一下Patient得id格式
    BundleInfo = FHIRData_Handle(None, data, 1, 0)
    resourceType = BundleInfo[0].resourceType # 用第一層看一下這個resources是不是bundle
    
    if resourceType != 'Bundle':
        PathResult = findReference(data)
        if PathResult == 'Patient':
            print(PathResult)
            data['id'] = just_id
            result = data
        elif PathResult is not None:
            result = set_nested_value(data, PathResult, pat_id)
        else:
            result = data

    elif resourceType == 'Bundle':
        for i, row in enumerate(BundleInfo):
            PathResult = findReference(row.BundleResource)
            if PathResult == 'Patient':
                entry = data["entry"][i]

                # request.url
                req = entry.get("request")
                if isinstance(req, dict) and "url" in req:
                    req["url"] = pat_id

                # resource.id
                res = entry.get("resource")
                if isinstance(res, dict) and "id" in res:
                    res["id"] = just_id

                # fullUrl
                full = entry.get("fullUrl")
                if isinstance(full, str) and "Patient" in full:
                    entry["fullUrl"] = full.split("Patient")[0] + pat_id
            elif PathResult is not None:
                data["entry"][i]["resource"] = set_nested_value(row.BundleResource, PathResult, pat_id)
            
        result = data
    with open("input_result.json", "w", encoding='utf-8') as json_file:
        json.dump(result, json_file)  
    # print(result)
    res = upload_FHIR(result)
    print(res.text)
    return res
def merge_to_simple_json(q_data, r_data):
    # 1. 建立題目字典 (Key 轉小寫以利對照)
    q_map = {item['linkId'].lower(): item for item in q_data.get('item', [])}
    
    merged_results = []

    # 2. 遍歷 QuestionnaireResponse 的答案項目
    for resp_item in r_data.get('item', []):
        link_id_lower = resp_item['linkId'].lower()
        question = q_map.get(link_id_lower)
        
        if not question:
            continue

        simple_answers = []
        for ans in resp_item.get('answer', []):
            # 取得原始答案值 (不論是 String, Integer, Boolean)
            raw_val = list(ans.values())[0]
            
            # 如果是選擇題 (choice)，嘗試找尋對應的顯示文字 (display)
            display_text = str(raw_val)
            if question.get('type') == 'choice':
                options = question.get('answerOption', [])
                for opt in options:
                    coding = opt.get('valueCoding', {})
                    if str(coding.get('code')) == str(raw_val):
                        display_text = coding.get('display')
                        break
            
            # 直接存入字串
            simple_answers.append(display_text)

        # 組合成簡化格式
        merged_results.append({
            "linkId": question['linkId'],    # 保留原始題目 ID
            "text": question['text'],        # 題目文字
            "answers": simple_answers        # 只有文字的列表
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
    # 1. 先查看看有沒有重複的編號
    existing_project = Project.query.filter_by(irb_number=ProjectId).first()
    
    if existing_project:
        # 這裡你可以選擇回傳錯誤，或是更新它
        return {"success": False, "message": f"IRB編號 {ProjectId} 已存在"}

    data['PI'] = pra_id # FHIR也要補一下PI的id
    result = FHIR_listMapping(data, 2)

    # print(result)

    ProjectName = data.get('ProjectName')
    ProjectStatus = data.get('ProjectStatus')
    PI = pra_id
    dataType = data.get('dataType')
    fhir_study_id = 'ResearchStudy/' + ProjectId

    Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)    
    # print(Response.text)
    if Response.ok:
        # 確定進fhir server再進資料庫
        new_projecy = Project(irb_number = ProjectId, name = ProjectName, pi_id = pra_id, fhir_study_id = fhir_study_id, status = ProjectStatus, dataType = dataType)
        db.session.add(new_projecy)
        db.session.commit()
        return {'success': True, 'message': '已新增成功'}
    else:
        # print(result)
        return {"success": False, "message": result.text}



def addPatient_FHIR(data, study_id):
    type = data.get('type')


    pat_id = data.get('pat_id')
    # pat_identi = data.get('pat_identi')

    # if pat_identi is not None:
    #     pat_id = find_patient_id(pat_identi)
    if pat_id != None:
        inputResSub = {
            'pat_id': "Patient/" + pat_id,
            'start': data.get('start'),
            'id': study_id + '-' + pat_id,
            'status': 'on-study',
            'studyId': "ResearchStudy/" + study_id
        }

        inputPat = {
            'id': pat_id,
            'birthDate': data.get('birthDate'),
            'gender': data.get('gender'),
        }
        ResearchSubject_rules = FHIR.FhirMappging.query.filter_by(CatId=5, Del=0).all()

        if type == 'new': # 如果是新增 就要補一個patient進去fhir server
            result = FHIR_listMapping(inputPat, 9)
            Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result) 

        result = FHIR_listMapping(inputResSub, 5)
        Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)  

        return Response
    else:
        return None

def upload_Consent(study_id, pat_id, filename):

    # 這邊因為Consent我綁的是ResearchSubject，所以要先去抓一下他的id
    getSubject = FHIRData_Handle(None, FHIRSearch_Handle(43, [pat_id,study_id]), 5, 1)[0] 

    data = {
        "status": "active",
        "pat_id": "Patient/" + pat_id,
        "subjectId": "ResearchSubject/" + getSubject.id,
        "url":  '/' + study_id + '-' + pat_id + '/' + filename,
        "dateTime": datetime.now().strftime('%Y-%m-%d'),
    }
    result = FHIR_listMapping(data, 10)

    # print(result)

    res = post_FHIR_api(result, 'Consent')
    # Consent_rules = FHIR.FhirMappging.query.filter_by(CatId=5, Del=0).all()

    return res


def get_DevicePatient(pat_id, study_id):

    Response = read_FHIR_api("Patient/" + pat_id) # 先抓Patient資料
    PatInfo = FHIRData_Handle(None, Response, 9, 0)[0] # 拿去處理
    
    return PatInfo


def getAllEncounter(pat_id):

    EncBundle = FHIRData_Handle(None, "Encounter?_sort=-date&patient=Patient/" + pat_id, 1, 1)
    # 抓每一個Encounter
    result = []
    for e in EncBundle:
        # 把他從model轉json
        enc_data = FHIRData_Handle(None, e.BundleResource, 11, 0)
        # print(enc_data)
        result.extend(e.model_dump() for e in enc_data)
    # PatInfo = FHIRData_Handle(None, Response, 11, 0)[0] # 拿去處理
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

def getBULK(ProjectId):
    ProjectInfo = FHIRData_Handle(None, "ResearchSubject?study=ResearchStudy/" + ProjectId, 5, 1)
    
    pat_id_list = []
    for item in ProjectInfo:
        pat_id_list.append(item.pat_id)
    today = datetime.now()
    data = {
        "pat_id": pat_id_list,
        "actual": "true",
        "type": "person",
        "date": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "id": ProjectId + "-" + today.strftime("%Y%m%d"),
    }
    result = FHIR_listMapping(data, 14)

    Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)  
    Export_data(ProjectId, result['resourceType'] + "/" + result['id'])
    return


def Export_data(ProjectId, GroupId):
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
            verify=cfg.VERIFY_TLS,  # $export 輪詢間隔秒  20sec
        )
        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return None, {"ok": False, "stage": "oauth", "http": getattr(resp, "status_code", None),
                          "message": f"取得 token 失敗: {e}", "text": getattr(resp, "text", "")}
        return data.get("access_token"), {"ok": True, "stage": "oauth"}

    # 1) 取得 token
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

    # 2) 啟動 $export
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

    # 3) 輪詢
    # 輪詢前先建資料表，然後先把jobId存起來備用(以jobid有成功為前題就表示bulk應該會成功)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = cfg.NDJSON_DIR
    out_root.mkdir(parents=True, exist_ok=True)
    folder_pro = out_root / f"{ProjectId}"
    folder_pro.mkdir(exist_ok=True)
    folder = folder_pro / ts
    folder.mkdir(exist_ok=True)
    (folder / "JobId.txt").write_text(job_url, encoding="utf-8")

    last = {}
    while True:
        try:
            # 每次輪詢可更新 token（避免過期）
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
            # 200：成功
            result = p.json()
            break
        except Exception as e:
            time.sleep(cfg.POLL_INTERVAL)

    if not isinstance(result, dict) or "output" not in result:
        return {"ok": False, "stage": "poll", "message": "完成回應缺少 output", "detail": result}

    # 4) 下載 NDJSON

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
        "ndjson_files": files[:10],  # 預覽前 10 筆
        "job_url": job_url
    }

from pathlib import Path

def get_latest_export_status(project_id):
    base_folder = Path(cfg.NDJSON_DIR) / project_id
    # 資料夾不存在
    if not base_folder.exists():
        return []

    subfolders = [f for f in base_folder.iterdir() if f.is_dir()]

    results = []

    for sub in subfolders:
        files = list(sub.iterdir())

        job_file = sub / "JobId.txt"
        OK_file = sub / "OK.txt"
        ndjson_files = [f for f in files if f.suffix == ".ndjson"]

        # 判斷狀態
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

        # 取最後更新時間（資料夾時間）
        last_updated = datetime.fromtimestamp(sub.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        results.append({
            "project_id": project_id,
            "folder": sub.name,
            "status": status,
            "status_text": status_text,
            "countData": len(ndjson_files),
            "lastUpdated": last_updated
        })

    # 排序（最新在前）
    results.sort(key=lambda x: x["folder"], reverse=True)

    return results