from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, send_file, Response
from blueprints import fhir 
from blueprints import api_watch 
from blueprints import auth 
import mylib.fhir_check as fhir_check
from config import BaseConfig as cfg  
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
import io
import csv
import pyminizip
import tempfile

def flask_response_to_data(res):
    try:
        return res.get_json()
    except Exception:
        return res.get_data(as_text=True) if hasattr(res, "get_data") else str(res)


def get_stats_from_response(response_data):
    if not isinstance(response_data, dict):
        return None

    if "stats" in response_data:
        return response_data["stats"]

    if isinstance(response_data.get("response"), dict):
        return response_data["response"].get("stats")

    return None



bp = Blueprint("pages", __name__)

@bp.app_context_processor
def inject_user():
    fhir_practitioner_id = session.get('fhir_practitioner_id')

    getProjectID = []

    if fhir_practitioner_id:
        try:
            getProjectID = fhir.get_ProjectID(fhir_practitioner_id)
        except Exception as e:
            print("[inject_user] get_ProjectID 失敗：", e)
            getProjectID = []

    return dict(
        username=session.get('username'),
        user_id=session.get('user_id'),
        fhir_practitioner_id=fhir_practitioner_id,
        role=session.get('role'),
        study_id=session.get('study_id'),
        study_name=session.get('study_name'),
        project_all_id=getProjectID,
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
        
        exc_type, exc_value, exc_traceback = sys.exc_info()
        detailed_error = traceback.format_exception(exc_type, exc_value, exc_traceback)
        
        
        print("".join(detailed_error))
        
        
        
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
    

    
    
    
    ProjectInfo = Project.query.filter_by(irb_number=session['study_id']).first()
    CountAllData_All_update_at = ProjectInfo.resource_count_updated_at
    CountAllData_All_rawdata = ProjectInfo.resource_count
    CountAllData_All = json.loads(CountAllData_All_rawdata)

    CountAllData = CountAllData_All[0]
    getCountDataList = CountAllData_All[1:]
    

    getDevice = fhir.getDeviceCount(session['study_id'])
    TotalDev = getDevice[0] 
    CountDev = getDevice[1] 
    

    return render_template('index.html', CountDev=CountDev, TotalDev=TotalDev, getProjectInfo=getProjectInfo, getMonthProjectInfo=getMonthProjectInfo, CountAllData=CountAllData, getCountDataList=getCountDataList, CountAllData_All_update_at=CountAllData_All_update_at, script_path=url_for('static', filename='Content/Scripts/index.js'))

@bp.route('/set_study_session/<study_id>/<study_name>/<study_status>') 
def set_study_session(study_id, study_name, study_status):
    
    session['study_id'] = study_id
    session['study_name'] = study_name
    session['study_status'] = study_status
    
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
    data = ProjectMember.query.filter_by(project_id=study_id).all()
    return render_template('caseMember.html', data=data, script_path=url_for('static', filename='Content/Scripts/caseMember.js'))

@bp.route("/caseManageDetail/<case_id>/<ResearchSubjectStatus>")
def caseManageDetail(case_id, ResearchSubjectStatus):
    
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))
    getPatInfo = fhir.get_Patient(case_id, session['study_id']) 
    PatInfo = getPatInfo[0]
    FirstDate = getPatInfo[1] 
    getConsent = getPatInfo[2] 
    getDeviceInfo = getPatInfo[3] 
    EndDate = getPatInfo[4] 


    
    getQAInfo = fhir.getQA(case_id)


    return render_template("caseManageDetail.html", PatInfo=PatInfo, FirstDate=FirstDate, EndDate=EndDate, getConsent=getConsent, ResearchSubjectStatus=ResearchSubjectStatus, getDeviceInfo=getDeviceInfo, getQAInfo=getQAInfo, script_path=url_for('static', filename='Content/Scripts/caseManageDetail.js'))

@bp.route("/api/getEncounter_all/<case_id>")
def api_getEnc_all(case_id):
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    getAllEncounter = fhir.getAllEncounter(case_id)

    return jsonify(getAllEncounter) 

@bp.route("/api/getTreatment_all/<case_id>/<Resource>")
def api_getTreat_all(case_id, Resource):
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    getAllData = fhir.getAllTreatment(case_id, [Resource])

    return jsonify(getAllData) 

@bp.route("/api/getEncounter/<enc_id>")
def api_getEnc(enc_id):
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    print(enc_id)
    getEncInfo = fhir.getEnc(enc_id)

    return jsonify(getEncInfo) 


@bp.route("/deviceDetail/<pat_id>/<device_id>")
def deviceDetail(pat_id, device_id):


    PatInfo = fhir.get_DevicePatient(pat_id, session['study_id']) 

    
    return render_template("deviceDetail.html", PatInfo=PatInfo, device_id=device_id, script_path=url_for('static', filename='Content/Scripts/deviceDetail.js'))

@bp.route("/api/deviceDetailObs14days/<device_id>")
def api_deviceDetail(device_id):
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    start = request.args.get("start")
    end = request.args.get("end")
    getObs14daysResult = fhir.getObs14days("", device_id, start, end)
    return jsonify(getObs14daysResult) 

@bp.route("/api/caseManageObs14days/<pat_id>")
def api_patObs14days(pat_id):
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    start = request.args.get("start")
    end = request.args.get("end")

    getObs14daysResult = fhir.getObs14days(pat_id, "", start, end)
    print(getObs14daysResult)

    return jsonify(getObs14daysResult) 


@bp.route('/api/addPatient', methods=['POST'])
def api_addPatient():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    print(session['study_status'] )
    if session['study_status'] == "withdrawn":
        return jsonify({'success': False, 'message': '已撤銷計劃無法新增資料!'})
    data = request.get_json()

    res = fhir.addPatient_FHIR(data, session['study_id'])

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
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
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
    data = getDevice[0] 
    TotalDev = getDevice[1] 
    CountDev = getDevice[2] 
    status_counts_updated_at = getDevice[3] 

    return render_template('deviceManage.html', data=data, TotalDev=TotalDev, CountDev=CountDev, status_counts_updated_at=status_counts_updated_at, script_path=url_for('static', filename='Content/Scripts/deviceManage.js'))

@bp.route('/api/addDevice', methods=['POST'])
def api_addDevice():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401

    if session.get('study_status') == "withdrawn":
        return jsonify({
            'success': False,
            'message': '已撤銷計劃無法新增資料!'
        })

    data = request.get_json(silent=True) or {}

    res = fhir.addDevice_FHIR(
        data=data,
        study_id=session.get('study_id')
    )

    # addDevice_FHIR 回傳 need_confirm
    if isinstance(res, dict) and res.get("need_confirm"):
        return jsonify(res), 409

    # addDevice_FHIR 回傳錯誤
    if isinstance(res, dict) and not res.get("success"):
        return jsonify(res), res.get("status_code", 400)

    return jsonify({
        "success": True,
        "message": res.get("message", "已新增成功")
    })

@bp.route('/api/update-device-count', methods=['POST'])
def api_update_device_count():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    data = request.get_json()
    print(data)
    study_id = data.get("study_id")

    if not study_id:
        return jsonify({
            "success": False,
            "message": "缺少 study_id"
        }), 400

    result = fhir.getDeviceCount_toSQL(study_id)

    return jsonify({
        "success": True,
        "message": "已開始背景更新"
    })

@bp.route('/api/update-data-count', methods=['POST'])
def api_update_data_count():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    data = request.get_json()
    print(data)
    study_id = data.get("study_id")

    if not study_id:
        return jsonify({
            "success": False,
            "message": "缺少 study_id"
        }), 400

    result = fhir.getDataCount_toSQL(study_id)

    return jsonify({
        "success": True,
        "message": "已開始背景更新"
    })

@bp.route('/api/update-resource-count', methods=['POST'])
def api_update_resource_count():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    data = request.get_json()
    print(data)
    study_id = data.get("study_id")

    if not study_id:
        return jsonify({
            "success": False,
            "message": "缺少 study_id"
        }), 400

    result = fhir.countAllData(study_id)

    return jsonify({
        "success": True,
        "message": "已開始背景更新"
    })

@bp.route('/projectManage')
def projectManage():
    if session['role'] == "ASSISTANT":
        return render_template('error_page.html', message=f"錯誤原因：無此權限"), 403
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    data = fhir.get_Project(session['fhir_practitioner_id'])    
    print(data)
    

    return render_template('projectManage.html', data=data, script_path=url_for('static', filename='Content/Scripts/projectManage.js'))

@bp.route('/api/addProject', methods=['POST'])
def api_addProject():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    data = request.get_json()
    res = fhir.addProject_FHIR(data, session['fhir_practitioner_id'])

    return jsonify(res)

@bp.route('/api/addMember', methods=['POST'])
def api_addMember():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    
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
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    if session['study_status'] == "withdrawn":
        return jsonify({'success': False, 'message': '已撤銷計劃無法新增資料!'})
    file = request.files.get('file')
    file_type = request.form.get('fileType')  
    pat_id = request.form.get('patid')  
    study_id = session['study_id']
    print(file_type)
    if file:
        
        subfilename = file.filename.split('.')[-1]
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = now + '.' + subfilename
        if file_type == 'Consent':
            upload_dir = "./static/data/" + file_type + '/' + study_id + '-' + pat_id
        else:
            upload_dir = "./static/data/" + file_type + '/'

        
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            print(f"建立資料夾: {upload_dir}")

        
        save_path = os.path.join(upload_dir, new_filename)
        file.save(save_path)
        
        file.seek(0)
        
        
        if file_type == 'FHIR':
            try:
                data = json.load(file)
            except Exception:
                return jsonify({
                    "success": False,
                    "message": "JSON 格式錯誤，無法讀取檔案"
                }), 400

            try:
                result, stats = fhir_check.upload_FHIR_mappingID(
                    study_id,
                    data,
                    original_filename=file.filename,
                    saved_filename=new_filename
                )
            except Exception as e:
                return jsonify({
                    "success": False,
                    "message": f"非FHIR格式資料或處理失敗：{str(e)}"
                }), 400

            try:
                fhir_response = result.json()
            except Exception:
                fhir_response = result.text if hasattr(result, "text") else str(result)

            if result.ok:
                return jsonify({
                    "success": True,
                    "message": f"已收到檔案: {file.filename}",
                    "status_code": result.status_code,
                    "response": fhir_response,
                    "stats": stats
                }), result.status_code

            return jsonify({
                "success": False,
                "message": fhir_response,
                "status_code": result.status_code,
                "stats": stats
            }), result.status_code
        elif file_type == 'FHIR_pat':
            data = json.load(file)
            result, stats = fhir_check.upload_FHIR_changeID(
                pat_id,
                data,
                original_filename=file.filename,
                saved_filename=new_filename
            )

            if result.ok:
                return jsonify({
                    "success": True,
                    "message": file.filename,
                    "stats": stats
                })
            else:
                return jsonify({
                    "success": False,
                    "message": result.text,
                    "stats": stats
                })
        
        elif file_type == 'Consent':
            result = fhir.upload_Consent(study_id, pat_id, new_filename) 
            if result.ok:
                return jsonify({"success": True, "message": "已收到同意書: " + file.filename})
            else:
                return jsonify({"success": False, "message": result.text})
        
        elif file_type == 'Watch':
            res, res_status = api_watch.api_trans_watch(
                'Watch',
                study_id,
                save_path
            )

            response_data = flask_response_to_data(res)
            stats = get_stats_from_response(response_data)

            if res_status in [200, 201]:
                return jsonify({
                    "success": True,
                    "message": f"已收到檔案: {file.filename}",
                    "status_code": res_status,
                    "response": response_data,
                    "stats": stats
                })

            return jsonify({
                "success": False,
                "message": response_data,
                "status_code": res_status
            }), res_status


        elif file_type == 'Asus':
            try:
                data = json.load(file)
            except Exception as e:
                return jsonify({
                    "success": False,
                    "message": f"JSON 讀取失敗：{str(e)}"
                }), 400

            fhir_project = request.form.get('fhir_project')

            if not fhir_project:
                return jsonify({
                    "success": False,
                    "message": "缺少 fhir_project"
                }), 400

            res, res_status = api_watch.api_trans_watch(
                fhir_project,
                study_id,
                save_path,
                data
            )

            response_data = flask_response_to_data(res)
            stats = get_stats_from_response(response_data)

            if res_status in [200, 201]:
                return jsonify({
                    "success": True,
                    "message": f"已收到檔案: {file.filename}",
                    "status_code": res_status,
                    "response": response_data,
                    "stats": stats
                })

            return jsonify({
                "success": False,
                "message": response_data,
                "status_code": res_status
            }), res_status

        elif file_type == 'Questionnaire':
            data = json.load(file)
            result, stats = fhir_check.upload_FHIR_changeID(
                pat_id,
                data,
                original_filename=file.filename,
                saved_filename=new_filename
            )
            if result.ok:
                return jsonify({"success": True, "message": "已收到問卷: " + file.filename})
            else:
                return jsonify({"success": False, "message": "上傳失敗"})
        
        
    return jsonify({"success": False, "message": "上傳失敗"})

@bp.route('/api/download', methods=['GET'])
def download_export():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
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

    
    temp_zip = Path(cfg.NDJSON_DIR) / f"{folder_name}.zip"

    
    file_list = []
    relative_list = []

    for root, dirs, files in os.walk(base_path):
        for file in files:
            
            if file == "zip_password.txt":
                continue

            full_path = Path(root) / file
            rel_path = full_path.relative_to(base_path)

            file_list.append(str(full_path))
            relative_list.append(str(rel_path.parent) if str(rel_path.parent) != "." else "")

    if not file_list:
        return {"error": "沒有可壓縮的檔案"}, 400

    
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
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    data = request.get_json()
    result = fhir.get_new_patient_id(data['projectId'])
    print(result)
    return jsonify(f"Patient/{result}")

@bp.route("/api/project_member/save_all", methods=["POST"])
def save_all_project_member():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    data = request.get_json(silent=True) or {}
    rows = data.get("data", [])
    print(rows)

    if not rows:
        return jsonify({"error": "沒有資料"}), 400

    project_id = rows[0].get("project_id")

    if not project_id:
        return jsonify({"error": "缺少 project_id"}), 400

    try:
        existing_members = ProjectMember.query.filter_by(
            project_id=project_id
        ).all()

        existing_map = {
            (m.old_patient_id, m.new_patient_id): m
            for m in existing_members
        }

        incoming_map = {}

        for item in rows:
            old_patient_id = item.get("old_patient_id")
            new_patient_id = item.get("new_patient_id")
            created_at = item.get("created_at")
            Del = int(item.get("Del", 0))

            if not old_patient_id or not new_patient_id:
                continue

            key = (old_patient_id, new_patient_id)

            incoming_map[key] = {
                "old_patient_id": old_patient_id,
                "new_patient_id": new_patient_id,
                "created_at": created_at,
                "Del": Del
            }

        # 前端完全沒送來的既有資料，代表已不存在，也標成 Del=1
        for key, member in existing_map.items():
            if key not in incoming_map:
                member.Del = 1

        for key, item in incoming_map.items():
            old_patient_id = item["old_patient_id"]
            new_patient_id = item["new_patient_id"]
            created_at = item["created_at"]
            Del = item["Del"]

            if key in existing_map:
                member = existing_map[key]
                member.Del = Del

                if created_at:
                    member.created_at = created_at

                continue

            # 如果這筆是刪除狀態，但 DB 原本不存在，可以不用新增
            if Del == 1:
                continue

            PatInfo = fhir.read_FHIR_api(new_patient_id)

            if not PatInfo or PatInfo.get("resourceType") != "Patient":
                data_addPatient = {
                    "pat_id": new_patient_id.replace("Patient/", ""),
                    "gender": "unknown",
                    "start": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "type": "new",
                    "status": "on-study"
                }

                addPatientResult = fhir.addPatient_FHIR(data_addPatient, project_id)
                print(addPatientResult)

            member = ProjectMember(
                project_id=project_id,
                old_patient_id=old_patient_id,
                new_patient_id=new_patient_id,
                created_at=created_at,
                Del=Del
            )

            db.session.add(member)

        db.session.commit()

        return jsonify({"message": "更新成功"}), 200

    except Exception as e:
        db.session.rollback()
        print("錯誤:", e)
        return jsonify({"error": "更新失敗"}), 500
@bp.route("/api/project_member/export", methods=["GET"])
def export_project_member():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401

    study_id = request.args.get("study_id") or session.get("study_id")

    if not study_id:
        return jsonify({
            "success": False,
            "message": "缺少 study_id"
        }), 400

    data = ProjectMember.query.filter_by(
        project_id=study_id
    ).order_by(
        ProjectMember.id.asc()
    ).all()

    output = io.StringIO()
    output.write("\ufeff")  # Excel 開啟中文不亂碼

    writer = csv.writer(output)

    writer.writerow([
        "計畫代碼",
        "原有ID",
        "系統ID",
        "建立日期",
        "刪除狀態"
    ])

    for item in data:
        writer.writerow([
            item.project_id,
            item.old_patient_id,
            item.new_patient_id,
            item.created_at,
            item.Del
        ])

    csv_data = output.getvalue()
    output.close()

    filename = f"project_member_{study_id}.csv"

    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
@bp.route('/api/test', methods=['POST'])
def api_test():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    study_id = 'IRB-2026-001'
    data = request.get_json()
    
    result, stats = fhir_check.upload_FHIR_mappingID(
        study_id,
        data,
        original_filename=file.filename,
        saved_filename=new_filename
    )

    return jsonify(result)

@bp.route("/api/fhir_upload_logs/<study_id>")
def api_fhir_upload_logs(study_id):
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    base_folder = Path(cfg.FHIRUPLOAD_DIR) / study_id

    if not base_folder.exists():
        return jsonify({
            "success": True,
            "data": []
        })

    logs = []

    for folder in base_folder.iterdir():
        if not folder.is_dir():
            continue

        stats_file = folder / "input_result_stats.json"
        result_file = folder / "input_result.json"

        total_resources = "-"
        status = "無統計檔"

        original_filename = folder.name

        if stats_file.exists():
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    stats = json.load(f)

                total_resources = stats.get("total_resources", "-")
                status = "成功"

                upload_file = stats.get("upload_file", {})
                original_filename = upload_file.get("original_filename") or folder.name

            except Exception:
                status = "統計檔讀取失敗"

        logs.append({
            "folder": folder.name,  # 真正資料夾，查詳細結果用
            "original_filename": original_filename,
            "time": folder.name,
            "total_resources": total_resources,
            "status": status,
            "has_stats": stats_file.exists(),
            "has_result": result_file.exists()
        })

    logs.sort(key=lambda x: x["folder"], reverse=True)

    return jsonify({
        "success": True,
        "data": logs
    })

@bp.route("/api/fhir_upload_logs/<study_id>/<log_folder>")
def api_fhir_upload_log_detail(study_id, log_folder):
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    folder = Path(cfg.FHIRUPLOAD_DIR) / study_id / log_folder
    stats_file = folder / "input_result_stats.json"

    if not stats_file.exists():
        return jsonify({
            "success": False,
            "message": "找不到上傳統計檔"
        }), 404

    try:
        with open(stats_file, "r", encoding="utf-8") as f:
            stats = json.load(f)

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        print("[UPLOAD LOG] 讀取失敗:", e)
        return jsonify({
            "success": False,
            "message": "讀取上傳統計失敗"
        }), 500


@bp.route('/api/fhir/devices', methods=['GET'])
def api_fhir_devices():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    try:
        result = fhir.read_FHIR_api("Device?_count=1000")

        devices = []

        for entry in result.get("entry", []):
            resource = entry.get("resource", {})

            if resource.get("resourceType") != "Device":
                continue

            device_id = resource.get("id", "")

            display = device_id

            if resource.get("deviceName"):
                display = resource["deviceName"][0].get("name", device_id)

            elif resource.get("identifier"):
                display = resource["identifier"][0].get("value", device_id)

            devices.append({
                "device_id": device_id,
                "display": display
            })
        print(devices)
        return jsonify({
            "success": True,
            "data": devices
        })

    except Exception as e:
        print("[FHIR DEVICE] 讀取失敗:", e)
        return jsonify({
            "success": False,
            "message": "讀取 FHIR Device 失敗"
        }), 500


@bp.route('/api/project/save_devices', methods=['POST'])
def api_save_project_devices():
    ok, user_id = auth.check_session_or_header_login()

    if not ok:
        return jsonify({
            "success": False,
            "message": "未登入或帳號密碼錯誤"
        }), 401
    data = request.get_json()
    device_list = data.get('device_list',[])

    study_id = session.get('study_id')

    if not study_id:
        return jsonify({
            'success': False,
            'message': '缺少 project_id'
        }), 400

    project = Project.query.filter_by(irb_number=study_id, Del=0).first()

    if not project:
        return jsonify({
            'success': False,
            'message': '找不到專案'
        }), 404

    if device_list == []:
        project.device_list = None
    else:
        project.device_list = json.dumps(device_list, ensure_ascii=False)
    

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '設備更新成功'
    })


@bp.app_errorhandler(500)
def internal_server_error(error):
    error_message = str(error) if current_app.debug else None

    return render_template(
        "errors/500.html",
        error_message=error_message
    ), 500