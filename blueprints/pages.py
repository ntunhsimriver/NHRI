from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from blueprints import fhir 
from config import BaseConfig as cfg  # 讀 config
import requests
import json
import os

bp = Blueprint("pages", __name__)

@bp.app_context_processor
def inject_user():
    return dict(username=session.get('username'), 
        fhir_practitioner_id=session.get('fhir_practitioner_id'),
        study_id=session.get('study_id'), 
        study_name=session.get('study_name'))

@bp.route('/')
def root():
    return redirect(url_for('pages.index_page'))

@bp.route('/selectproject')
def selectproject():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))

    session.pop('study_id', None)
    session.pop('study_name', None)
    data = fhir.get_Project(session['fhir_practitioner_id'])
    return render_template('selectproject.html', data=data, script_path=url_for('static', filename='Content/Scripts/selectproject.js'))

@bp.route('/index')
def index_page():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    print(session['study_id'])
    return render_template('index.html', script_path=url_for('static', filename='Content/Scripts/index.js'))

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
    lastUpdated = getPatInfo[1] # 最後更新日期(當作收案日)
    getConsent = getPatInfo[2] # 抓同意書內容
    # 直接去抓他全部的值
    getAllInfoResult = fhir.getAllInfo(case_id)
    # 這個是畫 生理數據 (Vitals) 的折線圖用的
    getObs14daysResult = fhir.getObs14days(case_id)
    print(getObs14daysResult)
    return render_template("caseManage.html", getObs14daysResult=getObs14daysResult, getAllInfoResult=getAllInfoResult, PatInfo=PatInfo, lastUpdated=lastUpdated, getConsent=getConsent, ResearchSubjectStatus=ResearchSubjectStatus, script_path=url_for('static', filename='Content/Scripts/caseManage.js'))

@bp.route('/dataImport')
def dataImport():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    return render_template('dataImport.html', script_path=url_for('static', filename='Content/Scripts/dataImport.js'))

@bp.route('/deviceManage')
def deviceManage():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    getDevice = fhir.getDevice()
    data = getDevice[0] # 所有device的內容
    TotalDev = getDevice[1] # 總設備術
    CountDev = getDevice[2] # 個別設備數

    return render_template('deviceManage.html', data=data, TotalDev=TotalDev, CountDev=CountDev, script_path=url_for('static', filename='Content/Scripts/deviceManage.js'))

@bp.route('/api/addDevice', methods=['POST'])
def api_addDevice():
    data = request.get_json()

    res = fhir.addDevice_FHIR(data)
    # 進土撥鼠的專案
    # data_in = {'ProjectGroup': 'THBC_NHRI', 'Project': 'Device', 'data': [data]}
    # headers_Groundhog = {'WebUsername':'admin@gmail.com', 'WebUserpassword':'aB12345678!'} 
    # response = requests.post(cfg.Trans_FHIR, headers=headers_Groundhog, json=data_in, verify=False)
    # json_fhir = json.loads(str(response.text))
    # response_FHIR = requests.post(cfg.FHIR_SERVER_URL, json=json_fhir, verify=False)
    if res.ok:
        return jsonify({'success': True, 'message': '已新增成功'})
    else:
        return jsonify({'success': False, 'message': '新增失敗'})


@bp.route('/projectManage')
def projectManage():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    data = fhir.get_Project(session['fhir_practitioner_id'])    
    return render_template('projectManage.html', data=data, script_path=url_for('static', filename='Content/Scripts/projectManage.js'))

@bp.route('/api/addProject', methods=['POST'])
def api_addProject():
    data = request.get_json()


    res = fhir.addProject_FHIR(data, session['fhir_practitioner_id'])
    # 進土撥鼠的專案
    # data_in = {'ProjectGroup': 'THBC_NHRI', 'Project': 'Device', 'data': [data]}
    # headers_Groundhog = {'WebUsername':'admin@gmail.com', 'WebUserpassword':'aB12345678!'} 
    # response = requests.post(cfg.Trans_FHIR, headers=headers_Groundhog, json=data_in, verify=False)
    # json_fhir = json.loads(str(response.text))
    # response_FHIR = requests.post(cfg.FHIR_SERVER_URL, json=json_fhir, verify=False)
    return jsonify(res)

# @bp.route('/crossData')
# def crossData_page():
#     if 'username' not in session:
#         return redirect(url_for('auth.login_page'))
#     return render_template('crossData.html', script_path=url_for('static', filename='Content/Scripts/crossData.js'))


@bp.route('/api/uploadFHIR', methods=['POST'])
def api_uploadFHIR():
    file = request.files.get('file')
    if file:
        # 1. 定義上傳路徑
        upload_dir = "./uploads"
        # 2. 檢查資料夾是否存在，不存在就建立 (核心修復)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            print(f"建立資料夾: {upload_dir}")
        # 3. 執行存檔
        save_path = os.path.join(upload_dir, file.filename)
        file.save(save_path)
        # 指針歸0
        file.seek(0)
        data = json.load(file)
        result = fhir.upload_FHIR(data) # 直接把檔案轉成 Python 字典
        
        if result.ok:
            return jsonify({"success": True, "message": file.filename})
        else:
            return jsonify({"success": False, "message": result.text})
    return jsonify({"success": False, "message": "沒收到檔案"})
