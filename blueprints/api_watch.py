from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from config import BaseConfig as cfg  # 讀 config
from blueprints import fhir 
import requests
import json
import os
import datetime
import csv
import pandas as pd
from pathlib import Path



bp = Blueprint("api_watch", __name__)

TransFHIR_list = [
    {
        "data": "DataWithTimePeriod",
        "project": "historic_data_origin"
    },
    {
        "data": "SleepDataWithTimePeriod",
        "project": "sleep_data"
    },
    {
        "data": "麗臺手錶",
        "project": "麗臺手錶"
    }
]

mapping_list = {
    '帳號': 'account',
    '會員名稱': 'PatientID',
    '量測日期時間': 'datetime',
    '心率': 'heart_rate',
    '量測時間 (UTC)': 'measurement_time_utc',
    '步數': 'steps',
    '距離': 'distance',
    '卡路里': 'calories',
    '活躍時間': 'active_time'
}



# 轉土撥鼠的東西
def handler_watch(data, project_type):
    if project_type != "麗臺手錶":
        data = watch_mapping_patient(data)
    inputdata = {
        "ProjectGroup": "THBC_NHRI",
        "Project": project_type}

    inputdata['data'] = data

    headers_Groundhog = {'WebUsername':'admin@gmail.com', 'WebUserpassword':'aB12345678!'} 
    response = requests.post(cfg.Trans_FHIR, headers=headers_Groundhog, json=inputdata)
    result = json.loads(str(response.text))

    return result

def clean_duplicate_entries_with_server_check(bundle_json, auth_token=None):
    unique_entries = []
    seen_full_urls = set()
    
    # 設定 Header (如果有 token 的話)
    # headers = fhir.get_token()
    for entry in bundle_json.get('entry', []):
        resource = entry.get('resource')
        if not resource:
            continue
            
        res_type = resource.get('resourceType')
        res_id = resource.get('id')
        full_url = entry.get('fullUrl')
        # 1. 檢查 Device 是否已經存在於 FHIR Server
        if res_type == 'Device' and res_id:
            try:
                # 使用 GET 請求確認資源是否存在
                response = fhir.read_FHIR_api(f"Device/{res_id}")

                # 如果有回傳資料（代表存在）
                if response and isinstance(response, dict) and response.get("resourceType") == "Device":
                    continue
            except Exception as e:
                print(f"連線至 FHIR Server 出錯: {e}")

        # 2. 原有的本地去重邏輯 (防止同一個 Bundle 內有重複的 fullUrl)
        if full_url:
            if full_url not in seen_full_urls:
                unique_entries.append(entry)
                seen_full_urls.add(full_url)
        else:
            unique_entries.append(entry)

    bundle_json['entry'] = unique_entries


    return bundle_json

def watch_mapping_patient(data):
    result = []
    for row in data:
        print(f"Device/{row['deviceid']}")
        DeviceInfo = fhir.FHIRData_Handle(None, f"Device/{row['deviceid']}", 6, 1)
        # print(DeviceInfo.pat_id)
        pat_id = DeviceInfo[0].pat_id
        if pat_id is not None:
            row['PatientID'] = pat_id.replace("Patient/", "")
        result.append(row)
    # print(result)
    return result

def Watch_leadtek(df):
    result_data = []
    df = df.dropna()
    df = df.rename(columns=mapping_list)
    df['datetime'] = pd.to_datetime(df['datetime'])\
                                    .dt.strftime('%Y-%m-%dT%H:%M:%S%z')
    for _, row in df.iterrows():
        if 'heart_rate' in df.columns:
            data = {
                "deviceid": "device-" + row["PatientID"],
                "Patient": [{
                    "account": row["account"],
                    "PatientID": "patient-" + row["PatientID"]
                }],
                "Observation_HeartRate": [{
                    "PatientID": "patient-" + row["PatientID"],
                    "datetime":  row["datetime"],
                    "heart_rate": row["heart_rate"]
                }]
            }
        else:
            data = {
                "deviceid": "device-" + row["PatientID"],
                "Patient": [{
                    "account": row["account"],
                    "PatientID": "patient-" + row["PatientID"]
                }],
                "Observation_Sport": [{
                    "PatientID": "patient-" + row["PatientID"],
                    "datetime": row["datetime"],
                    "Sport": [
                        {
                            "value": row["steps"],
                            "code": "steps"
                        },
                        {
                            "value": row["distance"],
                            "code": "distance"
                        },
                        {
                            "value": row["calories"],
                            "code": "calories"
                        },
                        {
                            "value": row["active_time"],
                            "code": "active_time"
                        }
                    ]
                }]
            }
        
        result_data.append(data)
    return result_data
@bp.route('/api/trans_watch/<datatype>', methods=['POST'])
def api_trans_watch(datatype):
    data = request.get_json()
    study_id = request.args.get("study_id")
    try:
        if datatype == "Watch":
            filename = data['filename']
            print(filename)
            # full_path = f"{Path(cfg.BASE_DATA_DIR)} / Watch / {filename}
            df = pd.read_csv(filename)
            data = Watch_leadtek(df)
            
            res_Groundhog = handler_watch(data, "麗臺手錶")

            CleanJson = clean_duplicate_entries_with_server_check(res_Groundhog)
            # with open("input_result.json", "w", encoding='utf-8') as json_file:
            #     json.dump(res_Groundhog, json_file)  
            res = fhir.upload_FHIR_mappingID(study_id, CleanJson)
        elif datatype == "historic_data_origin":
            for row in data['daily_data']:
                res_Groundhog = handler_watch([row], datatype)
                CleanJson = clean_duplicate_entries_with_server_check(res_Groundhog)
                res = fhir.upload_FHIR_mappingID(study_id, CleanJson)
                # break
        
        else:
            res_Groundhog = handler_watch(data, datatype)
            CleanJson = clean_duplicate_entries_with_server_check(res_Groundhog)
            res = fhir.upload_FHIR_mappingID(study_id, CleanJson)

        return jsonify(res.json()), res.status_code
        # return res_Groundhog
        
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500