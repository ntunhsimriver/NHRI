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
from models.project import Project, ProjectMember
from extensions import db
import re
from pathlib import Path
# import shutil
import pyminizip
import tempfile


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
    if session['role'] == "SUPER_ADMIN":
        return render_template('error_page.html', message=f"錯誤原因：無此權限"), 403
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))

    session.pop('study_id', None)
    session.pop('study_name', None)
    session.pop('study_status', None)
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
    # print(getProjectInfo_All)

    CountAllData_All = fhir.countAllData(session['study_id'])
    CountAllData = CountAllData_All[0]
    getCountDataList = CountAllData_All[1:]
    # print(CountAllData_All)

    getDevice = fhir.getDeviceCount(session['study_id'])
    TotalDev = getDevice[0] # 總設備術
    CountDev = getDevice[1] # 個別設備數
    # print(getDevice)

    return render_template('index.html', CountDev=CountDev, TotalDev=TotalDev, getProjectInfo=getProjectInfo, getMonthProjectInfo=getMonthProjectInfo, CountAllData=CountAllData, getCountDataList=getCountDataList, script_path=url_for('static', filename='Content/Scripts/index.js'))

@bp.route('/set_study_session/<study_id>/<study_name>/<study_status>') # 這個是為了先把study ID寄進去session裡面，這樣後續要抓資料比較好抓，不用再透過PI
def set_study_session(study_id, study_name, study_status):
    # 將 ID 存入 session
    session['study_id'] = study_id
    session['study_name'] = study_name
    session['study_status'] = study_status
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

@bp.route('/caseMember/<study_id>')
def caseMember(study_id):
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    data = ProjectMember.query.filter_by(project_id=study_id, Del=0).all()
    return render_template('caseMember.html', data=data, script_path=url_for('static', filename='Content/Scripts/caseMember.js'))

@bp.route("/caseManageDetail/<case_id>/<ResearchSubjectStatus>")
def caseManageDetail(case_id, ResearchSubjectStatus):
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


    # 這邊是問卷資料
    getQAInfo = fhir.getQA(case_id)


    return render_template("caseManageDetail.html", PatInfo=PatInfo, FirstDate=FirstDate, getConsent=getConsent, ResearchSubjectStatus=ResearchSubjectStatus, getDeviceInfo=getDeviceInfo, getQAInfo=getQAInfo, script_path=url_for('static', filename='Content/Scripts/caseManageDetail.js'))


# @bp.route("/api/caseManage/<case_id>")
# def case_encounter(case_id):
#     result = fhir.getAllEncounter(case_id)
#     return jsonify(result)

@bp.route("/api/getEncounter_all/<case_id>")
def api_getEnc_all(case_id):
    # print(enc_id)
    getAllEncounter = fhir.getAllEncounter(case_id)

    return jsonify(getAllEncounter) # 使用 jsonify 確保格式正確

@bp.route("/api/getTreatment_all/<case_id>/<Resource>")
def api_getTreat_all(case_id, Resource):
    getAllData = fhir.getAllTreatment(case_id, [Resource])

    return jsonify(getAllData) # 使用 jsonify 確保格式正確

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
    print(getObs14daysResult)

    return jsonify(getObs14daysResult) # 使用 jsonify 確保格式正確


@bp.route('/api/addPatient', methods=['POST'])
def api_addPatient():
    print(session['study_status'] )
    if session['study_status'] == "withdrawn":
        return jsonify({'success': False, 'message': '已撤銷計劃無法新增資料!'})
    data = request.get_json()

    res = fhir.addPatient_FHIR(data, session['study_id'])
    member = ProjectMember(
        project_id=session['study_id'],
        old_patient_id="",
        new_patient_id="Patient/" + data.get('pat_id'),
        created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        Del=0
    )

    db.session.add(member)
    db.session.commit()
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
    res = fhir.getBULK(data['project_id'], data['zip_password'])
    print(res)
    return res


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
    if session['study_status'] == "withdrawn":
        return jsonify({'success': False, 'message': '已撤銷計劃無法新增資料!'})

    data = request.get_json()
    res = fhir.addDevice_FHIR(data, session['study_id'])
    if res[0]:
        if res[1].ok:
            return jsonify({'success': True, 'message': '已新增成功'})
    else:
        return jsonify({'success': False, 'message': res[1]})


@bp.route('/projectManage')
def projectManage():
    if session['role'] == "ASSISTANT":
        return render_template('error_page.html', message=f"錯誤原因：無此權限"), 403
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
    if session['study_status'] == "withdrawn":
        return jsonify({'success': False, 'message': '已撤銷計劃無法新增資料!'})
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
    if session['study_status'] == "withdrawn":
        return jsonify({'success': False, 'message': '已撤銷計劃無法新增資料!'})
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
            result = fhir.upload_FHIR_mappingID(study_id, data) # 直接把檔案轉成 Python 字典
            
            if result.ok:
                return jsonify({"success": True, "message": file.filename})
            else:
                return jsonify({"success": False, "message": result.text})
        elif file_type == 'FHIR_pat':
            data = json.load(file)
            result = fhir.upload_FHIR_changeID(pat_id, data) # 直接把檔案轉成 Python 字典
            
            if result.ok:
                return jsonify({"success": True, "message": file.filename})
            else:
                return jsonify({"success": False, "message": result.text})
        elif file_type == 'Watch':
            url = f"{cfg.BASE_URL}/api/trans_watch/Watch?study_id={study_id}"
            print(save_path)
            res = requests.post(url, json={
                "filename": save_path
            })

            return jsonify({"success": True, "message": file.filename})
        elif file_type == 'Consent':
            result = fhir.upload_Consent(study_id, pat_id, new_filename) # 直接把檔案轉成 Python 字典
            if result.ok:
                return jsonify({"success": True, "message": "已收到同意書: " + file.filename})
            else:
                return jsonify({"success": False, "message": result.text})
        elif file_type == 'Asus':
            data = json.load(file)
            fhir_project = request.form.get('fhir_project')  # 這樣拿
            url = f"{cfg.BASE_URL}/api/trans_watch/{fhir_project}?study_id={study_id}"

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

    password_file = base_path / "zip_password.txt"
    if not password_file.exists():
        return {"error": "找不到 zip_password.txt"}, 404

    zip_password = password_file.read_text(encoding="utf-8").strip()
    if not zip_password:
        return {"error": "zip_password.txt 內容是空的"}, 400

    # 暫存 zip 檔
    temp_zip = Path(cfg.NDJSON_DIR) / f"{folder_name}.zip"

    # 收集資料夾內所有檔案
    file_list = []
    relative_list = []

    for root, dirs, files in os.walk(base_path):
        for file in files:
            # 不把密碼檔自己壓進去
            if file == "zip_password.txt":
                continue

            full_path = Path(root) / file
            rel_path = full_path.relative_to(base_path)

            file_list.append(str(full_path))
            relative_list.append(str(rel_path.parent) if str(rel_path.parent) != "." else "")

    if not file_list:
        return {"error": "沒有可壓縮的檔案"}, 400

    # 建立加密 zip
    pyminizip.compress_multiple(
        file_list,
        relative_list,
        str(temp_zip),
        zip_password,
        5
    )

    return send_file(
        str(temp_zip),
        as_attachment=True,
        download_name=f"{folder_name}.zip"
    )


@bp.route("/api/getNewID", methods=["POST"])
def api_getNewID():
    data = request.get_json()
    result = fhir.get_new_patient_id(data['projectId'])
    print(result)
    return jsonify(f"Patient/{result}")

@bp.route("/api/project_member/save_all", methods=["POST"])
def save_all_project_member():
    data = request.get_json(silent=True) or {}
    rows = data.get("data", [])
    print(rows)

    if not rows:
        return jsonify({"error": "沒有資料"}), 400

    # 👉 取 project_id（假設全部同一個）
    project_id = rows[0].get("project_id")

    if not project_id:
        return jsonify({"error": "缺少 project_id"}), 400

    try:
        # 🔥 1. 先全部標記為刪除
        ProjectMember.query.filter_by(project_id=project_id).update({
            "Del": 1
        })

        # 🔥 2. 再重新新增
        for item in rows:
            old_patient_id = item.get("old_patient_id")
            new_patient_id = item.get("new_patient_id")
            created_at = item.get("created_at")

            if not old_patient_id or not new_patient_id:
                continue
            PatInfo = fhir.read_FHIR_api(new_patient_id)
            print(PatInfo['resourceType'])
            if PatInfo['resourceType'] != 'Patient':
                data_addPatient = {
                  "pat_id": new_patient_id.replace("Patient/", ""),
                  "gender": "unknown",
                  "start": datetime.datetime.now().strftime("%Y-%m-%d"),
                  "type": "new"
                }

                addPatientResult = fhir.addPatient_FHIR(data_addPatient, project_id)
                print(addPatientResult)
            member = ProjectMember(
                project_id=project_id,
                old_patient_id=old_patient_id,
                new_patient_id=new_patient_id,
                created_at=created_at,
                Del=0
            )

            db.session.add(member)

        db.session.commit()

        return jsonify({"message": "更新成功"}), 200

    except Exception as e:
        db.session.rollback()
        print("錯誤:", e)
        return jsonify({"error": "更新失敗"}), 500

@bp.route('/api/test', methods=['POST'])
def api_test():
    study_id = 'IRB-2026-001'
    data = request.get_json()
    # result = fhir.check_export_folder(data)
    result = fhir.upload_FHIR_mappingID(study_id, data)

    return jsonify(result)

