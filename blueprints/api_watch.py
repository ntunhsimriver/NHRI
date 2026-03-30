from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from config import BaseConfig as cfg  # 讀 config
from blueprints import fhir 
import requests
import json
import os
import datetime
import csv


bp = Blueprint("api_watch", __name__)

TransFHIR_list = [
    {
        "data": "DataWithTimePeriod",
        "project": "historic_data_origin"
    },
    {
        "data": "SleepDataWithTimePeriod",
        "project": "sleep_data"
    }
]

# 轉土撥鼠的東西
def handler_watch(data, project_type):
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
            # 建立該資源在 Server 上的存取路徑
            # check_url = f"{ServerIP_Full}Device/{res_id}"
            # print(check_url)
            try:
                # 使用 GET 請求確認資源是否存在
                # headers = fhir.get_token()
                # response = requests.get(check_url, headers=headers)
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


@bp.route('/api/trans_watch/<datatype>', methods=['POST'])
def api_trans_watch(datatype):
    print(request.get_json())

    data = request.get_json()
    try:

        if datatype == "historic_data_origin":
            for row in data['daily_data']:
                res_Groundhog = handler_watch([row], datatype)
                CleanJson = clean_duplicate_entries_with_server_check(res_Groundhog)
                res = fhir.post_FHIR_api(CleanJson, "")
                break
        else:
            res_Groundhog = handler_watch(data, datatype)
            CleanJson = clean_duplicate_entries_with_server_check(res_Groundhog)
            res = fhir.post_FHIR_api(CleanJson, "")

        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500