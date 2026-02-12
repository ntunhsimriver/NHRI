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
import models.fhir as FHIR # 這邊是抓全部FHIR Resource的Class(就是抓全部欄位的內容)
from jsonpath_ng import jsonpath, parse
from pydantic import create_model
from collections import Counter

def register_fhir(app):
    fhir = FHIRClient()  # 從環境變數讀設定
    app.register_blueprint(create_fhir_blueprint(client=fhir, db=db))

def read_FHIR_api(Resource): # 所有get資料都靠他
    URL = cfg.FHIR_SERVER_URL + Resource # 搜尋條件
    res = requests.get(URL, verify=False)
    Response = json.loads(str(res.text))

    return Response

def put_FHIR_api(id, FHIR): # 回傳完整
    URL = cfg.FHIR_SERVER_URL + id # 搜尋條件
    res = requests.put(URL, json=FHIR, verify=False)
    # Response = json.loads(str(res.text)) # 先用不到

    return res

def post_FHIR_api(FHIR, resource): # 回傳完整
    URL = cfg.FHIR_SERVER_URL # 搜尋條件
    res = requests.post(URL+resource, json=FHIR, verify=False)

    return res

# 這邊是改用資料庫的內容處理fhir json
def FHIRData_Handle(SearchURL, CatId, readFlag): # readFlag=1 表示要去抓資料，=0表示是json直接進來
    getResult = []

    # 1.先抓FHIR資料
    if readFlag:
        data = read_FHIR_api(SearchURL)
    else:
        data = SearchURL
    
    # 1. 取得內層規則 (不管是不是 Bundle，這都要用到)
    study_rules = FHIR.FhirMappging.query.filter_by(CatId=CatId).all()
    
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
    # 使用正則表達式拆分路徑，同時處理屬性名和陣列索引（如 identifier[0]）
    parts = re.findall(r'([^.\[\]]+)|\[(\d+)\]', path)
    
    current = data
    for i in range(len(parts)):
        key, index = parts[i]
        
        # 處理陣列索引情況 [n]
        if index:
            index = int(index)
            # 如果目前位置不是列表，或長度不足，則補齊
            while len(current) <= index:
                current.append({})
            
            # 如果這是路徑的最後一部分，直接賦值
            if i == len(parts) - 1:
                current[index] = value
            else:
                # 準備進入下一層
                next_part_is_index = parts[i+1][1] != ''
                if not current[index]:
                    current[index] = [] if next_part_is_index else {}
                current = current[index]
        
        # 處理屬性名稱情況
        else:
            # 如果這是路徑的最後一部分，直接賦值
            if i == len(parts) - 1:
                current[key] = value
            else:
                # 檢查下一層是陣列還是物件，先行初始化
                next_part_is_index = parts[i+1][1] != ''
                if key not in current:
                    current[key] = [] if next_part_is_index else {}
                current = current[key]

def get_AllPatient(study_id): # 還不是新邏輯
    getResult = [] # 準備存處理好的Patient資料
    print(FHIRSearch_Handle(10, [study_id]))
    Response = read_FHIR_api("/ResearchSubject" + "?study=ResearchStudy/" + study_id)
    
    Bundle_entry = FHIR.FHIR_Bundle(Response)

    for b in Bundle_entry.entries:
        ResearchSubject_Info = FHIR.FHIR_ResearchSubject(b['resource'])
        print(b['resource'])

        Response = read_FHIR_api(ResearchSubject_Info.pat_id)

        PatInfo = FHIR.FHIR_Patient(Response)
        getResult.append({
                "PatInfo": PatInfo,  # 這裡存的是整個study的資料，他是物件
                "ResearchSubjectStatus": ResearchSubject_Info.status,    # 這裡存的是PI名字，他是字串
            })
        print(PatInfo)

    return getResult

def get_Patient(PatID, study_id): # 同意書可以一起讀? # 還不是新邏輯
    Response = read_FHIR_api("Patient/" + PatID)
    PatInfo = FHIR.FHIR_Patient(Response)

    # 為了要抓這個人在這個專案底下的更新日期(只能把她當收案日期)，去抓他最早一筆紀錄的最後更新日期，且只抓一筆???
    Response = read_FHIR_api("ResearchSubject?individual=Patient/" + PatID + "&study=ResearchStudy/" + study_id + "&_sort=_lastUpdated")
    Bundle_entry = FHIR.FHIR_Bundle(Response)
    lastUpdated = FHIR.FHIR_ResearchSubject(Bundle_entry.entries[0]['resource']).lastUpdated
    lastUpdated = lastUpdated[:10]

    getConsent = []
    Bundle_entry = FHIR.FHIR_Bundle(Response)
    for b in Bundle_entry.entries:
        Info = FHIR.FHIR_ResearchSubject(b['resource'])
        # Response = read_FHIR_api(Info.consent)
        ConsentId = Info.consent
        if ConsentId:
            getConsent.append(FHIR.FHIR_Consent(read_FHIR_api(ConsentId)))
        print(ConsentId)
    return PatInfo, lastUpdated, getConsent



def get_Project(pi_id):
    getResult = [] # 準備存處理好的資料
    study = FHIRData_Handle(FHIRSearch_Handle(8, [pi_id]), 2, 1)

    # 抓每一個ResearchStudy
    for b in study:
        # 從ResearchStudy裡面抓PI的名字(怕之後會跟db裡面的不一樣，所以先再抓一次)

        getPIName = FHIRData_Handle(b.PI, 3, 1)[0].name
        # 這邊直接count這個study底下有多少ResearchSubject(因為他一個裡面只能放一個人，所以就直接等於count人)
        getSubjectCount = FHIRData_Handle(FHIRSearch_Handle(9, [ b.ProjectId]), 1, 1)[0].SummaryCount

        getResult.append({
            "study_info": b,  # 這裡存的是整個study的資料，他是物件
            "pi_name": getPIName,    # 這裡存的是PI名字，他是字串
            "SubjectCount": getSubjectCount,    # 這裡存的是這個study底下有多少人，他是字串
        })

    return getResult

def getAllInfo(PatID): # 還不是新邏輯
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




def getObs14days(PatID): # 還不是新邏輯
    print(datetime.now())
    # 1. 自動計算日期
    # 今天日期 (例如: 2026-01-26)
    today = datetime.now()
    # 14 天前的日期 (例如: 2026-01-12)
    fourteen_days_ago_noformat = today - timedelta(days=14)
    fourteen_days_ago = (fourteen_days_ago_noformat).date().isoformat()
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
    # api_url = f"/Observation?subject=Patient/{PatID}&code={target_codes}&date=ge{fourteen_days_ago}&_sort=date&_count=1000"
    # Response = read_FHIR_api(api_url)
    # Bundle_entry = FHIR.FHIR_Bundle(Response)

    # 這邊先抓出所有內容
    rows = FHIRData_Handle(FHIRSearch_Handle(16, [PatID, target_codes, fourteen_days_ago, '1000']), 1, 1)

    sorted_dates = [ (today - timedelta(days=13-i)).date().isoformat() for i in range(14) ]
    storage = {d: {'SBP': [], 'DBP': [], 'HR': []} for d in sorted_dates}
    code_map = {'8480-6': 'SBP', '8462-4': 'DBP', '8867-4': 'HR'}
    for row in rows:
        if row.BundleResouce:
            if 'component' in row.BundleResouce:
                result = FHIRData_Handle(row.BundleResouce, 8, 0)
            else:
                result = FHIRData_Handle(row.BundleResouce, 7, 0)
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
    print(datetime.now())
    return sbp_list, dbp_list, hr_list, sorted_dates


def getDevice():

    getResult = [] # 準備存處理好的資料
    getFHIR = FHIRData_Handle('/Device', 6, 1)

    print(len(getFHIR))
    # status_counts = Counter(item.status for item in getFHIR)
    status_counts = Counter(
        label
        for item in getFHIR
        for label in ([item.status] + (['foundPat'] if item.pat_id else []))
        if label # 確保 label 不是 None
    )
    print(status_counts)

    return getFHIR, len(getFHIR), status_counts


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

def addDevice_FHIR(data):
    result = {}
    study_rules = FHIR.FhirMappging.query.filter_by(CatId=6, Del=0).all()
    for count, s in enumerate(study_rules):
        if count == 0: # 0的時候，可以先把resourceType塞進去
            FHIR_mappingJson(result, "resourceType", s.resource)
        if data.get(s.name):
            FHIR_mappingJson(result, s.fhirpath, data[s.name])
    Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)        
    return Response


def upload_FHIR(data):

    getFHIR = FHIRData_Handle(data, 1, 0)
    getFirstInfo = getFHIR[0] # 取第一個就可以知道最外層的，要先確認他到底是什麼Resource

    if getFirstInfo.type == "transaction":
        res = post_FHIR_api(data, "") # transaction可以直接上傳
    else:
        res = post_FHIR_api(data, getFirstInfo.resourceType) # Bundle及其他resource都要加上resourceType
    return res


def addProject_FHIR(data):
    print(data)
    # result = {}
    # study_rules = FHIR.FhirMappging.query.filter_by(CatId=6, Del=0).all()
    # for count, s in enumerate(study_rules):
    #     if count == 0: # 0的時候，可以先把resourceType塞進去
    #         FHIR_mappingJson(result, "resourceType", s.resource)
    #     if data.get(s.name):
    #         FHIR_mappingJson(result, s.fhirpath, data[s.name])
    # Response = put_FHIR_api(result['resourceType'] + "/" + result['id'], result)        
    return data