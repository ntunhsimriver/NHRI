from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import uuid
from extensions import db
from models.user import User
from werkzeug.security import generate_password_hash
import models.fhir as FHIR # 這邊是抓全部FHIR Resource的Class(就是抓全部欄位的內容)
from blueprints import fhir
from datetime import datetime, timedelta

bp = Blueprint("auth", __name__)

@bp.route('/login')
def login_page():
    if 'username' in session:
        return redirect(url_for('pages.index_page'))
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('fhir_practitioner_id', None)
    session.pop('study_id', None)
    session.pop('study_name', None)
    session.pop('study_status', None)
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
    status = 'active' # 註冊的人先都給他active

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
    new_user = User(id=new_uuid, password_hash = hashed_password, email = email, status=status, full_name = full_name, organization = organization, role = role, fhir_practitioner_id = fhir_practitioner_id)
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
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    now = datetime.now()

    # 先檢查是否已被鎖定
    lock_until = session.get('lock_until')
    if lock_until:
        try:
            lock_until_dt = datetime.fromisoformat(lock_until)
            if lock_until_dt > now:
                return jsonify({
                    'success': False,
                    'message': '登入失敗過多，請30分鐘後再試'
                })
            else:
                # 已過鎖定時間，清掉
                session.pop('lock_until', None)
                session['fail_count'] = 0
        except Exception:
            session.pop('lock_until', None)
            session['fail_count'] = 0

    user = User.query.filter_by(email=email).first()

    # 帳號存在且密碼正確
    if user and user.check_password(password):
        username = user.full_name
        fhir_practitioner_id = user.fhir_practitioner_id
        role = user.role

        session['username'] = username
        session['fhir_practitioner_id'] = fhir_practitioner_id
        session['role'] = role.value

        # 登入成功，清掉失敗紀錄
        session.pop('fail_count', None)
        session.pop('lock_until', None)

        print(f"[LOGIN] 成功登入：{username}")

        if role.value == "SUPER_ADMIN":
            return jsonify({'success': True, 'redirect': '/settings'})
        else:
            return jsonify({'success': True, 'redirect': '/selectproject'})

    # 登入失敗，累加錯誤次數
    fail_count = session.get('fail_count', 0)
    fail_count += 1
    session['fail_count'] = fail_count

    # 錯誤達 5 次，鎖定 30 分鐘
    if fail_count >= 5:
        lock_time = now + timedelta(minutes=30)
        session['lock_until'] = lock_time.isoformat()
        session['fail_count'] = 0

        print(f"[LOGIN] 登入失敗達5次：{email}")
        return jsonify({
            'success': False,
            'message': '錯誤5次，已鎖定30分鐘'
        })

    print(f"[LOGIN] 登入失敗：{email}")
    return jsonify({
        'success': False,
        'message': f'帳號或密碼錯誤，還可再嘗試 {5 - fail_count} 次'
    })


@bp.route('/settings')
def settings():
    if session['role'] == "ASSISTANT":
        return render_template('error_page.html', message=f"錯誤原因：無此權限"), 403
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    users = User.query.all()
    return render_template('settings.html', users=users, script_path=url_for('static', filename='Content/Scripts/settings.js'))

@bp.route('/change_password')
def change_password():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    
    return render_template('change_password.html', script_path=url_for('static', filename='Content/Scripts/change_password.js'))

@bp.route('/api/change_password', methods=['POST'])
def api_change_password():
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    user = User.query.filter_by(full_name=session['username']).first()

    if user and user.check_password(old_password):
        new_hashed_password = generate_password_hash(new_password)
        user.password_hash = new_hashed_password
        db.session.commit()


        return jsonify({'success': True, 'redirect': '/logout'})
    elif not user.check_password(old_password):
        return jsonify({'success': False, 'message': '原有密碼輸入錯誤'})
    