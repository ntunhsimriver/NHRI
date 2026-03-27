from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from blueprints import fhir 
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

    getDevice = fhir.getDevice()
    data = getDevice[0] # 所有device的內容
    TotalDev = getDevice[1] # 總設備術
    CountDev = getDevice[2] # 個別設備數

    return render_template('index.html', CountDev=CountDev, TotalDev=TotalDev, getProjectInfo=getProjectInfo, getMonthProjectInfo=getMonthProjectInfo, script_path=url_for('static', filename='Content/Scripts/index.js'))

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
    print(getDeviceInfo)
    # 直接去抓他全部的值
    # getAllInfoResult = fhir.getAllInfo(case_id)
    getAllEncounter = fhir.getAllEncounter(case_id)
    getAllTreatment = fhir.getAllTreatment(case_id, ['Procedure', 'MedicationRequest'])
    getAllDiaRep = fhir.getAllTreatment(case_id, ['DiagnosticReport'])

    # 這個是畫 生理數據 (Vitals) 的折線圖用的
    getObs14daysResult = fhir.getObs14days(case_id, "")


    print(getObs14daysResult)
    return render_template("caseManage.html", getObs14daysResult=getObs14daysResult, getAllEncounter=getAllEncounter, getAllTreatment=getAllTreatment, getAllDiaRep=getAllDiaRep, PatInfo=PatInfo, FirstDate=FirstDate, getConsent=getConsent, ResearchSubjectStatus=ResearchSubjectStatus, getDeviceInfo=getDeviceInfo, script_path=url_for('static', filename='Content/Scripts/caseManage.js'))

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
    print(device_id)
    getObs14daysResult = fhir.getObs14days("", device_id)

    return jsonify(getObs14daysResult) # 使用 jsonify 確保格式正確


@bp.route('/api/addPatient', methods=['POST'])
def api_addPatient():
    data = request.get_json()

    res = fhir.addPatient_FHIR(data, session['study_id'])
    print(res)
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
    # elif 'study_id' not in session:
    #     return redirect(url_for('pages.selectproject'))
    data = fhir.get_Project(session['fhir_practitioner_id'])    

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
    getMemberEmail = data['item_member']
    getMember_proid = data['item_proid']
    getMemberEmail_List = getMemberEmail.split(',')
    member_result = []
    for m in getMemberEmail_List:
        Assistant_Info = User.query.filter_by(email=m).first()
        member_result.append(str(Assistant_Info.id))
    member_result = ';'.join(member_result)
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

        if file_type == 'FHIR':
            data = json.load(file)
            result = fhir.upload_FHIR(data) # 直接把檔案轉成 Python 字典
            
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
    return jsonify({"success": False, "message": "沒收到檔案"})


