from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import uuid
from extensions import db
from models.user import User
from werkzeug.security import generate_password_hash
import models.fhir as FHIR # 這邊是抓全部FHIR Resource的Class(就是抓全部欄位的內容)
from blueprints import fhir

bp = Blueprint("auth", __name__)

@bp.route('/login')
def login_page():
    if 'username' in session:
        return redirect(url_for('pages.index_page'))
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('auth.login_page'))

@bp.route('/register', methods=['POST'])
def register():
    # 先給他一個預設的uuid
    new_uuid = uuid.uuid4()
    data = request.get_json()
    email = data.get('email')
    full_name = data.get('full_name')
    organization = data.get('organization')
    role = data.get('role')

    if data.get('password'):
        password = data.get('password')
    else:
        password = "Password123!" # 這邊設計如果是從網站來的，是管理員幫忙給他密碼，那就直接用預設的密碼

    # 如果使用者註冊時有指定fhir_practitioner_id就直接抓，沒有就直接帶入uuid
    if data.get('fhir_practitioner_id'):
        fhir_practitioner_id = data.get('fhir_practitioner_id')
    else:
        fhir_practitioner_id = "Practitioner/" + str(new_uuid)

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '帳號已存在'})

    hashed_password = generate_password_hash(password)
    new_user = User(id=new_uuid, password_hash = hashed_password, email = email, full_name = full_name, organization = organization, role = role, fhir_practitioner_id = fhir_practitioner_id)
    db.session.add(new_user)
    db.session.commit()

    # 這邊拚FHIR json
    pra_obj = FHIR.FHIR_Practitioner() # 先建立空物件
    pra_obj.id = fhir_practitioner_id.split("/")[1]
    pra_obj.name = full_name
    result_json = pra_obj.to_fhir() # 把他拚成json
    FHIR_response = fhir.put_FHIR_api(fhir_practitioner_id, result_json)
    
    print(f"[REGISTER] 建立新帳號：{full_name}")
    return jsonify({'success': True, 'message': '註冊成功'})

@bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    # 這邊直接抓full_name當username
    username = user.full_name
    fhir_practitioner_id = user.fhir_practitioner_id
    if user and user.check_password(password):
        session['username'] = username
        session['fhir_practitioner_id'] = fhir_practitioner_id
        print(f"[LOGIN] 成功登入：{username}")
        return jsonify({'success': True, 'redirect': '/selectproject'})
    else:
        print(f"[LOGIN] 登入失敗：{username}")
        return jsonify({'success': False, 'message': '帳號或密碼錯誤'})


@bp.route('/settings')
def settings():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    elif 'study_id' not in session:
        return redirect(url_for('pages.selectproject'))

    users = User.query.all()
    print(users[0].role.name)
    return render_template('settings.html', users=users, script_path=url_for('static', filename='Content/Scripts/settings.js'))
