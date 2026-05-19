from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from config import BaseConfig as cfg  # 讀 config
from blueprints import fhir 
import mylib.fhir_check as fhir_check
import requests
import json
import os
import datetime
import csv
import pandas as pd
from pathlib import Path
import traceback


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

# 共用設定
CSV_TIME_FORMAT = "%Y/%m/%d %H:%M"
JSON_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

HEART_RATE_MIN = 30
HEART_RATE_MAX = 300

STEPS_MIN = 0
STEPS_MAX = 5000

SPO2_MIN = 0
SPO2_MAX = 100


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",  
    "%Y/%m/%d %H:%M:%S",  
    "%Y/%m/%d %H:%M",     
]

def is_datetime(value, time_formats=None):
    if time_formats is None:
        time_formats = TIME_FORMATS

    if isinstance(time_formats, str):
        time_formats = [time_formats]

    value = str(value).strip()

    for fmt in time_formats:
        try:
            datetime.datetime.strptime(value, fmt)
            return True
        except:
            pass

    return False

def check_range(value, min_value, max_value):
    try:
        value = int(str(value).replace(",", "").strip())
        return min_value <= value <= max_value
    except:
        return False

# 轉土撥鼠的東西
def handler_watch(data, project_type):
    print(len(data))
    # if project_type != "麗臺手錶":
    data = watch_mapping_patient(data)
    print(data)
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
    for entry in bundle_json.get('entry', []):
        resource = entry.get('resource')
        if not resource:
            continue
            
        res_type = resource.get('resourceType')
        res_id = resource.get('id')
        full_url = entry.get('fullUrl')
        if res_type == 'Device' and res_id:
            try:
                response = fhir.read_FHIR_api(f"Device/{res_id}")
                if response and isinstance(response, dict) and response.get("resourceType") == "Device":
                    continue
            except Exception as e:
                print(f"連線至 FHIR Server 出錯: {e}")

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
        deviceid = row.get("deviceid")

        if not deviceid:
            # 沒有 deviceid 也照樣保留
            result.append(row)
            continue

        DeviceInfo = fhir.FHIRData_Handle(
            None,
            f"Device/{deviceid}",
            6,
            1
        )

        if DeviceInfo:
            pat_id = DeviceInfo[0].pat_id

            if pat_id:
                row["PatientID"] = pat_id.replace("Patient/", "")

        result.append(row)

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
                            "code": "55423-8"
                        },
                        {
                            "value": row["distance"],
                            "code": "55430-3"
                        },
                        {
                            "value": row["calories"],
                            "code": "55424-6"
                        },
                        {
                            "value": row["active_time"],
                            "code": "101691-4"
                        }
                    ]
                }]
            }
        
        result_data.append(data)
    print(result_data)
    return result_data

STEPS_MAX = 100000

def check_upload_csv(file):
    df = pd.read_csv(file, dtype=str)
    errors = []

    required = ["會員名稱", "量測日期時間", "量測時間 (UTC)"]

    for col in required:
        if col not in df.columns:
            errors.append(f"缺少欄位：{col}")

    has_steps = "步數" in df.columns
    has_hr = "心率" in df.columns

    if not has_steps and not has_hr:
        errors.append("缺少欄位：步數 或 心率")

    if errors:
        return False, errors, df

    for i, row in df.iterrows():
        row_num = i + 2
        if row.isna().all() or row.fillna("").astype(str).str.strip().eq("").all():
            errors.append(f"第 {row_num} 列：此列為空白列，請先刪除空白列後再上傳")
            continue

        time_value = str(row["量測日期時間"]).strip()

        if not is_datetime(time_value, CSV_TIME_FORMAT):
            errors.append(f"第 {row_num} 列：量測日期時間格式錯誤，應為 2026/4/1 00:05")

        if has_steps and pd.notna(row["步數"]) and row["步數"].strip() != "":
            if not check_range(row["步數"], STEPS_MIN, STEPS_MAX):
                errors.append(f"第 {row_num} 列：步數必須是 {STEPS_MIN}~{STEPS_MAX}")

        if has_hr and pd.notna(row["心率"]) and row["心率"].strip() != "":
            if not check_range(row["心率"], HEART_RATE_MIN, HEART_RATE_MAX):
                errors.append(f"第 {row_num} 列：心率必須是 {HEART_RATE_MIN}~{HEART_RATE_MAX}")

    return len(errors) == 0, errors, df


def check_watch_daily_json(data):
    errors = []

    if not isinstance(data, dict):
        return False, ["資料必須是 dict"]

    if "daily_data" not in data:
        return False, ["缺少 daily_data"]

    if not isinstance(data["daily_data"], list):
        return False, ["daily_data 必須是 list"]

    for i, device in enumerate(data["daily_data"]):
        row = i + 1
        prefix = f"daily_data 第 {row} 筆"

        if not isinstance(device, dict):
            errors.append(f"{prefix}：必須是 dict")
            continue

        if not device.get("deviceid"):
            errors.append(f"{prefix}：缺少 deviceid")

        for j, hb in enumerate(device.get("hb", [])):
            p = f"{prefix} hb 第 {j + 1} 筆"

            if not is_datetime(hb.get("time"), JSON_TIME_FORMAT):
                errors.append(f"{p}：time 格式錯誤")

            hr = hb.get("heartrate")
            if not is_int(hr) or not HEART_RATE_MIN <= hr <= HEART_RATE_MAX:
                errors.append(f"{p}：heartrate 必須是 {HEART_RATE_MIN}~{HEART_RATE_MAX}")

        for j, step in enumerate(device.get("step", [])):
            p = f"{prefix} step 第 {j + 1} 筆"

            if not is_datetime(step.get("time"), JSON_TIME_FORMAT):
                errors.append(f"{p}：time 格式錯誤")

            steps = step.get("steps")
            if not is_int(steps) or not STEPS_MIN <= steps <= STEPS_MAX:
                errors.append(f"{p}：steps 必須是 {STEPS_MIN}~{STEPS_MAX}")

        for j, spo2 in enumerate(device.get("spo2", [])):
            p = f"{prefix} spo2 第 {j + 1} 筆"

            if not is_datetime(spo2.get("time"), JSON_TIME_FORMAT):
                errors.append(f"{p}：time 格式錯誤")

            val = spo2.get("spo2")
            if not is_int(val) or not SPO2_MIN <= val <= SPO2_MAX:
                errors.append(f"{p}：spo2 必須是 {SPO2_MIN}~{SPO2_MAX}")

        for j, bp in enumerate(device.get("bp", [])):
            p = f"{prefix} bp 第 {j + 1} 筆"

            if not is_datetime(bp.get("time"), JSON_TIME_FORMAT):
                errors.append(f"{p}：time 格式錯誤")

            for key in ["type", "sys", "dia", "hr"]:
                if not is_int(bp.get(key)):
                    errors.append(f"{p}：{key} 必須是整數")

    return len(errors) == 0, errors

def check_sleep_json(data):
    errors = []

    if not isinstance(data, list):
        return False, ["睡眠資料必須是 list"]

    required = [
        "deviceid",
        "StartTime",
        "EndTime",
        "Toss",
        "ComfortCount",
        "LightCount",
        "AwakeCount",
        "RemCount",
        "SleepScore"
    ]

    int_fields = [
        "Toss",
        "ComfortCount",
        "LightCount",
        "AwakeCount",
        "RemCount",
        "SleepScore"
    ]

    for i, item in enumerate(data):
        row = i + 1
        prefix = f"sleep 第 {row} 筆"

        if not isinstance(item, dict):
            errors.append(f"{prefix}：必須是 dict")
            continue

        for key in required:
            if key not in item:
                errors.append(f"{prefix}：缺少欄位 {key}")
        for key in int_fields:
            if key in item:
                value = item.get(key)

                if not is_int(value):
                    errors.append(f"{prefix}：{key} 必須是整數")
                elif value < 0:
                    errors.append(f"{prefix}：{key} 不可小於 0")

    return len(errors) == 0, errors

@bp.route('/api/trans_watch/<datatype>', methods=['POST'])
def api_trans_watch(datatype, study_id=None, filename=None, data=None):
    try:
        if study_id is None:
            study_id = request.args.get("study_id")
        if datatype == "Watch":
            is_valid, errors, df = check_upload_csv(filename)
            Groundhog_datatype = "麗臺手錶"
            if not is_valid:
                print(str(errors))
                return jsonify({"error": str(errors)}), 500

            Groundhog_data = Watch_leadtek(df)
        elif datatype == "historic_data_origin":
            if data is None:
                data = request.get_json()
            Groundhog_datatype = datatype
            is_valid, errors = check_watch_daily_json(data)

            if not is_valid:
                return jsonify({
                    "success": False,
                    "message": errors
                }), 400
            Groundhog_data = []
            for row in data['daily_data']:
                Groundhog_data.append(row)
        else:
            if data is None:
                data = request.get_json()
            
            Groundhog_datatype = datatype

            is_valid, errors = check_sleep_json(data)
            Groundhog_data = data
            if not is_valid:
                return jsonify({
                    "success": False,
                    "message": errors
                }), 400
        
        res_Groundhog = handler_watch(Groundhog_data, Groundhog_datatype)
        CleanJson = clean_duplicate_entries_with_server_check(res_Groundhog)
        print(study_id)
        if study_id == None:
            res = fhir.upload_FHIR(CleanJson)
            try:
                fhir_response = res.json()
            except Exception:
                fhir_response = res.text if hasattr(res, "text") else str(res)

            return jsonify({
                "success": res.status_code in [200, 201],
                "message": "FHIR 上傳完成",
                "fhir_response": fhir_response
            }), res.status_code
        else:
            res, stats = fhir_check.upload_FHIR_mappingID(study_id, CleanJson)

            try:
                fhir_response = res.json()
            except Exception:
                fhir_response = res.text if hasattr(res, "text") else str(res)

            return jsonify({
                "success": res.status_code in [200, 201],
                "message": "FHIR 上傳完成",
                "fhir_response": fhir_response,
                "stats": stats
            }), res.status_code
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500