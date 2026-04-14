from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, send_file
from blueprints import fhir 
from blueprints import api_watch 
from config import BaseConfig as cfg  # 讀 config
import requests
import json
import os
import sys
import traceback
import datetime
from models.user import User
from models.project import Project
from extensions import db
import re
from pathlib import Path
import shutil

bp = Blueprint("pages", __name__)

@bp.app_context_processor
def inject_user():
    # study_id = session.get('study_id')
    # ProjectInfo = Project.query.filter_by(irb_number=study_id).first()

    return dict(username=session.get('username'), 
        fhir_practitioner_id=session.get('fhir_practitioner_id'),
        role=session.get('role'),
        study_id=session.get('study_id'), 
        study_name=session.get('study_name'),
        )

@bp.route('/')
def root():
    return redirect(url_for('pages.index_page'))

@bp.route('/selectproject')
def selectproject():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))

    session.pop('study_id', None)
    session.pop('study_name', None)
    try:
        data = fhir.get_Project(session['fhir_practitioner_id'])
        return render_template('selectproject.html', data=data, script_path=url_for('static', filename='Content/Scripts/selectproject.js'))
    except Exception as e:
        # 取得詳細的錯誤追蹤（Traceback）
        exc_type, exc_value, exc_traceback = sys.exc_info()
        detailed_error = traceback.format_exception(exc_type, exc_value, exc_traceback)
        
        # 將錯誤印在終端機方便排錯
        print("".join(detailed_error))
        
        # 將錯誤訊息傳給前端模板
        # 在開發階段，建議直接顯示 e，正式上線再改回模糊訊息
        return render_template('error_page.html', message=f"錯誤原因：{str(e)}"), 503
@bp.route('/index')
def index_page():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    print(session['study_id'])

    getProjectInfo_All = fhir.get_IndexProject(session['study_id'])
    getProjectInfo = getProjectInfo_All[0]
    getMonthProjectInfo = getProjectInfo_All[1]

    CountAllData_All = fhir.countAllData()
    CountAllData = CountAllData_All[0]
    getCountDataList = CountAllData_All[1:]
    print(getCountDataList)

    getDevice = fhir.getDevice(session['study_id'])
    data = getDevice[0] # 所有device的內容
    TotalDev = getDevice[1] # 總設備術
    CountDev = getDevice[2] # 個別設備數

    return render_template('index.html', CountDev=CountDev, TotalDev=TotalDev, getProjectInfo=getProjectInfo, getMonthProjectInfo=getMonthProjectInfo, CountAllData=CountAllData, getCountDataList=getCountDataList, script_path=url_for('static', filename='Content/Scripts/index.js'))

@bp.route('/set_study_session/<study_id>/<study_name>') # 這個是為了先把study ID寄進去session裡面，這樣後續要抓資料比較好抓，不用再透過PI
def set_study_session(study_id, study_name):
    # 將 ID 存入 session
    session['study_id'] = study_id
    session['study_name'] = study_name
    # 跳轉到目標頁面 (此時網址就不會帶有 ID)
    return redirect(url_for('pages.index_page'))

@bp.route('/caseManage')
def caseManage():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    data = fhir.get_AllPatient(session['study_id'])
    return render_template('caseManage.html', data=data, script_path=url_for('static', filename='Content/Scripts/caseManage.js'))

@bp.route("/caseManage/<case_id>/<ResearchSubjectStatus>")
def case_detail(case_id, ResearchSubjectStatus):
    # 這裡的 case_id 就是你要的
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    getPatInfo = fhir.get_Patient(case_id, session['study_id']) # 同意書可以這邊一起讀取?
    PatInfo = getPatInfo[0]
    FirstDate = getPatInfo[1] # 最後更新日期(當作收案日)
    getConsent = getPatInfo[2] # 抓同意書內容
    getDeviceInfo = getPatInfo[3] # 抓所有設備的資訊

    # 直接去抓他全部的值
    # getAllInfoResult = fhir.getAllInfo(case_id)
    getAllEncounter = fhir.getAllEncounter(case_id)
    getAllTreatment = fhir.getAllTreatment(case_id, ['Procedure', 'MedicationRequest'])
    getAllDiaRep = fhir.getAllTreatment(case_id, ['DiagnosticReport'])

    # 這個是畫 生理數據 (Vitals) 的折線圖用的

    today = datetime.datetime.now()
    fourteen_days_ago_noformat = today - datetime.timedelta(days=14)
    end = today.strftime("%Y-%m-%d")
    start = fourteen_days_ago_noformat.strftime("%Y-%m-%d")
    getObs14daysResult = fhir.getObs14days(case_id, "", start, end)

    # 這邊是問卷資料
    getQAInfo = fhir.getQA(case_id)


    return render_template("caseManage.html", getObs14daysResult=getObs14daysResult, getAllEncounter=getAllEncounter, getAllTreatment=getAllTreatment, getAllDiaRep=getAllDiaRep, PatInfo=PatInfo, FirstDate=FirstDate, getConsent=getConsent, ResearchSubjectStatus=ResearchSubjectStatus, getDeviceInfo=getDeviceInfo, getQAInfo=getQAInfo, script_path=url_for('static', filename='Content/Scripts/caseManage.js'))

# @bp.route("/api/caseManage/<case_id>")
# def case_encounter(case_id):
#     result = fhir.getAllEncounter(case_id)
#     return jsonify(result)

@bp.route("/api/getEncounter/<enc_id>")
def api_getEnc(enc_id):
    print(enc_id)
    getEncInfo = fhir.getEnc(enc_id)

    return jsonify(getEncInfo) # 使用 jsonify 確保格式正確


@bp.route("/deviceDetail/<pat_id>/<device_id>")
def deviceDetail(pat_id, device_id):


    PatInfo = fhir.get_DevicePatient(pat_id, session['study_id']) # 同意書可以這邊一起讀取?

    # getObs14daysResult = fhir.getObs14days("", device_id)
    return render_template("deviceDetail.html", PatInfo=PatInfo, device_id=device_id, script_path=url_for('static', filename='Content/Scripts/deviceDetail.js'))

@bp.route("/api/deviceDetailObs14days/<device_id>")
def api_deviceDetail(device_id):

    start = request.args.get("start")
    end = request.args.get("end")
    getObs14daysResult = fhir.getObs14days("", device_id, start, end)
    return jsonify(getObs14daysResult) # 使用 jsonify 確保格式正確

@bp.route("/api/caseManageObs14days/<pat_id>")
def api_patObs14days(pat_id):

    start = request.args.get("start")
    end = request.args.get("end")

    getObs14daysResult = fhir.getObs14days(pat_id, "", start, end)

    return jsonify(getObs14daysResult) # 使用 jsonify 確保格式正確


@bp.route('/api/addPatient', methods=['POST'])
def api_addPatient():
    data = request.get_json()

    res = fhir.addPatient_FHIR(data, session['study_id'])
    print(res)
    if res == None:
        return jsonify({'success': False, 'message': '此身份證字號不存在於FHIR Server'})
    else:
        if res.ok:
            return jsonify({'success': True, 'message': '已新增成功'})   
        else:
            return jsonify({'success': False, 'message': '新增失敗'})


@bp.route('/dataImport')
def dataImport():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    return render_template('dataImport.html', script_path=url_for('static', filename='Content/Scripts/dataImport.js'))

@bp.route('/dataExport')
def dataExport():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    data = fhir.get_latest_export_status(session['study_id'])

    return render_template('dataExport.html', data=data, script_path=url_for('static', filename='Content/Scripts/dataExport.js'))

@bp.route('/api/export', methods=['POST'])
def api_export():
    data = request.get_json()
    print(data)
    res = fhir.getBULK(data['project_id'])
    print(res)
    return jsonify({
        "success": True,
        "message": "匯出已開始",
        "project_id": project_id
    }), 202


@bp.route('/deviceManage')
def deviceManage():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    getDevice = fhir.getDevice(session['study_id'])
    data = getDevice[0] # 所有device的內容
    TotalDev = getDevice[1] # 總設備術
    CountDev = getDevice[2] # 個別設備數

    return render_template('deviceManage.html', data=data, TotalDev=TotalDev, CountDev=CountDev, script_path=url_for('static', filename='Content/Scripts/deviceManage.js'))

@bp.route('/api/addDevice', methods=['POST'])
def api_addDevice():
    data = request.get_json()
    res = fhir.addDevice_FHIR(data, session['study_id'])
    if res[0]:
        if res[1].ok:
            return jsonify({'success': True, 'message': '已新增成功'})
    else:
        return jsonify({'success': False, 'message': res[1]})


@bp.route('/projectManage')
def projectManage():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    data = fhir.get_Project(session['fhir_practitioner_id'])    
    print(data)
    # PatInfo = fhir.getProjectManagePatient(session['study_id'])

    return render_template('projectManage.html', data=data, script_path=url_for('static', filename='Content/Scripts/projectManage.js'))

@bp.route('/api/addProject', methods=['POST'])
def api_addProject():
    data = request.get_json()
    res = fhir.addProject_FHIR(data, session['fhir_practitioner_id'])

    return jsonify(res)

@bp.route('/api/addMember', methods=['POST'])
def api_addMember():
    data = request.get_json()
    member_result = data['item_member']
    getMember_proid = data['item_proid']
    ProjectInfo = Project.query.filter_by(irb_number=getMember_proid).first()

    if ProjectInfo:
        ProjectInfo.Assistant = member_result
        db.session.commit()
    return jsonify({"success": True, "message": "新增成功"})

@bp.route('/api/uploadFHIR', methods=['POST'])
def api_uploadFHIR():
    file = request.files.get('file')
    file_type = request.form.get('fileType')  # 這樣拿
    pat_id = request.form.get('patid')  # 這樣拿
    study_id = session['study_id']
    if file:
        # 1. 定義上傳路徑
        subfilename = file.filename.split('.')[-1]
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = now + '.' + subfilename
        if file_type == 'Consent':
            upload_dir = "./static/data/" + file_type + '/' + study_id + '-' + pat_id
        else:
            upload_dir = "./static/data/" + file_type + '/'

        # 2. 檢查資料夾是否存在，不存在就建立 (核心修復)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            print(f"建立資料夾: {upload_dir}")

        # 3. 執行存檔
        save_path = os.path.join(upload_dir, new_filename)
        file.save(save_path)
        # 指針歸0
        file.seek(0)
        # data = json.load(file)

        if file_type == 'FHIR':
            data = json.load(file)
            result = fhir.upload_FHIR_changeID(pat_id, data) # 直接把檔案轉成 Python 字典
            
            if result.ok:
                return jsonify({"success": True, "message": file.filename})
            else:
                return jsonify({"success": False, "message": result.text})
        elif file_type == 'Excel':
            return jsonify({"success": True, "message": file.filename})
        elif file_type == 'Consent':
            result = fhir.upload_Consent(study_id, pat_id, new_filename) # 直接把檔案轉成 Python 字典
            if result.ok:
                return jsonify({"success": True, "message": "已收到同意書: " + file.filename})
            else:
                return jsonify({"success": False, "message": result.text})
        elif file_type == 'Watch':
            data = json.load(file)
            fhir_project = request.form.get('fhir_project')  # 這樣拿
            url = f"{cfg.BASE_URL}/api/trans_watch/{fhir_project}"

            res = requests.post(url, json=data)

            return jsonify({"success": True, "message": res.status_code})
        elif file_type == 'Questionnaire':
            data = json.load(file)
            result = fhir.upload_FHIR_changeID(pat_id, data)
            if result.ok:
                return jsonify({"success": True, "message": "已收到問卷: " + file.filename})
            else:
                return jsonify({"success": False, "message": "上傳失敗"})
        # elif file_type == 'FHIR_ChangeId':
        #     data = json.load(file)
    return jsonify({"success": False, "message": "上傳失敗"})

@bp.route('/api/download', methods=['GET'])
def download_export():
    folder_name = request.args.get("folder_name")

    base_path = Path(cfg.NDJSON_DIR) / folder_name

    if not base_path.exists():
        return {"error": "資料夾不存在"}, 404

    zip_path = shutil.make_archive(
        str(base_path),
        "zip",
        root_dir=base_path
    )

    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"{folder_name}.zip"
    )
@bp.route('/api/test', methods=['POST'])
def api_test():
    data = 'IRB-2026-001'
    # data = request.get_json()
    # result = fhir.check_export_folder(data)
    result = fhir.get_latest_export_status(data)

    return jsonify(result)

