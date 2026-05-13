from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import uuid
from extensions import db
from models.user import User, UserRole, UserSession, LoginFailLog
from werkzeug.security import generate_password_hash
import models.fhir as FHIR # 這邊是抓全部FHIR Resource的Class(就是抓全部欄位的內容)
from blueprints import fhir
from datetime import datetime, timedelta
from config import BaseConfig as cfg
import secrets

bp = Blueprint("auth", __name__)

@bp.route('/login')
def login_page():
    if 'username' in session:
        return redirect(url_for('pages.index_page'))
    return render_template('login.html')

@bp.route('/logout')
def logout():
    token = request.cookies.get('session_token')

    if token:
        user_session = UserSession.query.filter_by(
            session_token=token,
            is_active=True
        ).first()

        if user_session:
            user_session.is_active = False
            db.session.commit()

    session.clear()

    response = redirect(url_for('auth.login_page'))
    response.delete_cookie('session_token')

    return response


@bp.route('/register', methods=['POST'])
def register():
    # 先給他一個預設的uuid
    new_uuid = uuid.uuid4()
    data = request.get_json()

    email = data.get('email')
    full_name = data.get('full_name')
    organization = data.get('organization')
    role = data.get('role')
    status = data.get('active')  # 註冊的人先都給他active
    type = data.get('type')      # 紀錄這次是按註冊還是按編輯

    if data.get('password'):
        password = data.get('password')
    else:
        password = cfg.USER_DEFAULT_PASSWORD  # 管理員新增時給預設密碼

    # 如果使用者註冊時有指定fhir_practitioner_id就直接抓，沒有就直接帶入uuid
    if data.get('fhir_practitioner_id'):
        fhir_practitioner_id = data.get('fhir_practitioner_id')
    else:
        fhir_practitioner_id = "Practitioner/" + str(new_uuid)

    # 新增時，email 已存在就擋掉
    if User.query.filter_by(email=email, Del=0).first() and type == 'new':
        return jsonify({'success': False, 'message': '帳號已存在'})

    # 編輯時：不要新增 user，要找原本的 user 來改
    if type == 'update':
        user = User.query.filter_by(email=email, Del=0).first()

        if not user:
            return jsonify({'success': False, 'message': '找不到使用者'})

        user.status = status
        user.full_name = full_name
        user.organization = organization
        user.role = role
        user.fhir_practitioner_id = fhir_practitioner_id

        # 權限/狀態被修改後，讓這個帳號目前所有登入 session 失效
        UserSession.query.filter_by(
            user_id=user.id,
            is_active=True
        ).update({
            'is_active': False
        })

        db.session.commit()

        message = '更新成功'
        print(f"[REGISTER] 更新帳號：{full_name}")

    else:
        hashed_password = generate_password_hash(password)

        new_user = User(
            id=new_uuid,
            password_hash=hashed_password,
            email=email,
            status=status,
            full_name=full_name,
            organization=organization,
            role=role,
            fhir_practitioner_id=fhir_practitioner_id
        )

        db.session.add(new_user)
        db.session.commit()

        message = '註冊成功'
        print(f"[REGISTER] 建立新帳號：{full_name}")

    # 這邊拚FHIR json
    pra_obj = FHIR.FHIR_Practitioner()  # 先建立空物件
    pra_obj.id = fhir_practitioner_id.split("/")[1]
    pra_obj.name = full_name
    pra_obj.active = status

    result_json = pra_obj.to_fhir()  # 把他拚成json
    print(fhir_practitioner_id)
    print(result_json)
    FHIR_response = fhir.put_FHIR_api(fhir_practitioner_id, result_json)
    print(FHIR_response.text)
    if FHIR_response.ok:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': "FHIR資源新增失敗"})

@bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    now = datetime.now()
    ip = request.remote_addr

    # 先檢查是否已被鎖定：改成查 DB，不用 session
    fail_log = LoginFailLog.query.filter_by(
        email=email,
        ip=ip
    ).first()

    if fail_log and fail_log.lock_until:
        if fail_log.lock_until > now:
            return jsonify({
                'success': False,
                'message': '登入失敗過多，請30分鐘後再試'
            })
        else:
            # 已過鎖定時間，清掉
            fail_log.lock_until = None
            fail_log.fail_count = 0
            db.session.commit()

    user = User.query.filter_by(email=email, Del=0).first()

    # 帳號不存在
    if not user:
        return login_failed(email, now)

    # 停權判斷
    if user.status is False or user.status == "False":
        return jsonify({
            'success': False,
            'message': '您的帳號已停權，請聯絡管理員恢復!!!'
        })

    # 帳號存在且密碼正確
    if user.check_password(password):
        username = user.full_name
        role = user.role
        fhir_practitioner_id = user.fhir_practitioner_id

        # 保留原本給其他頁面用的 session
        session['username'] = username
        session['fhir_practitioner_id'] = fhir_practitioner_id
        session['role'] = role.value


        # 同帳號登入時，讓其他裝置失效
        UserSession.query.filter_by(
            user_id=user.id,
            is_active=True
        ).update({
            'is_active': False
        })

        # 建立新的 session token
        token = secrets.token_urlsafe(64)

        new_session = UserSession(
            id=secrets.token_hex(32),
            user_id=user.id,
            session_token=token,
            last_activity=now,
            is_active=True,
            permission_version=getattr(user, 'permission_version', 1)
        )

        db.session.add(new_session)

        # 登入成功，清掉 DB 裡的失敗紀錄
        fail_log = LoginFailLog.query.filter_by(
            email=email,
            ip=ip
        ).first()

        if fail_log:
            db.session.delete(fail_log)

        db.session.commit()

        print(f"[LOGIN] 成功登入：{username}")

        if role.value == "SUPER_ADMIN":
            redirect_url = '/settings'
        else:
            redirect_url = '/selectproject'

        response = jsonify({
            'success': True,
            'redirect': redirect_url
        })

        response.set_cookie(
            'session_token',
            token,
            max_age=60 * 30,
            httponly=True,
            secure=False,   # 正式 HTTPS 改 True
            samesite='Lax'
        )

        return response

    return login_failed(email, now)

def login_failed(email, now):
    ip = request.remote_addr

    fail_log = LoginFailLog.query.filter_by(
        email=email,
        ip=ip
    ).first()

    if not fail_log:
        fail_log = LoginFailLog(
            email=email,
            ip=ip,
            fail_count=1,
            last_failed_at=now
        )
        db.session.add(fail_log)
    else:
        fail_log.fail_count += 1
        fail_log.last_failed_at = now

    # 錯誤達 5 次，鎖定 30 分鐘
    if fail_log.fail_count >= 5:
        fail_log.lock_until = now + timedelta(minutes=30)
        fail_log.fail_count = 0

        db.session.commit()

        print(f"[LOGIN] 登入失敗達5次：{email}")
        return jsonify({
            'success': False,
            'message': '錯誤5次，已鎖定30分鐘'
        })

    remaining = 5 - fail_log.fail_count

    db.session.commit()

    print(f"[LOGIN] 登入失敗：{email}")
    return jsonify({
        'success': False,
        'message': f'帳號或密碼錯誤，還可再嘗試 {remaining} 次'
    })

@bp.route('/settings')
def settings():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))

    if session.get('role') == "ASSISTANT":
        return render_template('error_page.html', message="錯誤原因：無此權限"), 403

    rolename = session['role']
    if rolename == "SUPER_ADMIN":
        users = User.query.filter(User.Del==0).all()

    elif rolename == "PI":
        users = User.query.filter(
            User.role.in_([UserRole.PI, UserRole.ASSISTANT]), User.Del==0
        ).all()

    else:
        users = User.query.filter(
            User.role == UserRole.ASSISTANT, User.Del==0
        ).all()
    return render_template('settings.html', users=users, script_path=url_for('static', filename='Content/Scripts/settings.js'))

@bp.route('/change_password')
def change_password():
    if 'username' not in session:
        return redirect(url_for('auth.login_page'))
    
    return render_template('change_password.html', script_path=url_for('static', filename='Content/Scripts/change_password.js'))

@bp.route('/api/delete_user', methods=['POST'])
def api_delete_user():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'message': '缺少 email'})

    user = User.query.filter_by(email=email, Del=0).first()

    if not user:
        return jsonify({'success': False, 'message': '找不到使用者'})

    user.Del = 1

    # 如果這個帳號目前有登入，順便強制登出
    UserSession.query.filter_by(
        user_id=user.id,
        is_active=True
    ).update({
        'is_active': False
    })

    db.session.commit()

    return jsonify({'success': True, 'message': '已刪除成功!'})


@bp.route('/api/change_password', methods=['POST'])
def api_change_password():
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    user = User.query.filter_by(full_name=session['username'], Del=0).first()

    if not user:
        return jsonify({'success': False, 'message': '找不到使用者'})

    if user.check_password(old_password):
        new_hashed_password = generate_password_hash(new_password)
        user.password_hash = new_hashed_password
        db.session.commit()

        return jsonify({'success': True, 'redirect': '/logout'})

    return jsonify({'success': False, 'message': '原有密碼輸入錯誤'})
    
@bp.before_app_request
def check_login_session():
    public_paths = [
        '/login',
        '/api/login',
        '/logout',
        '/api/logout',
        '/register',
        '/static',
    ]

    if any(request.path.startswith(path) for path in public_paths):
        return

    token = request.cookies.get('session_token')

    if not token:
        session.clear()
        return redirect(url_for('auth.login_page'))

    user_session = UserSession.query.filter_by(
        session_token=token,
        is_active=True
    ).first()

    if not user_session:
        session.clear()
        response = redirect(url_for('auth.login_page'))
        response.delete_cookie('session_token')
        return response

    # 超過 30 分鐘無動作，強制登出
    now = datetime.now()

    if now - user_session.last_activity > timedelta(minutes=30):
        user_session.is_active = False
        db.session.commit()

        session.clear()

        response = redirect(url_for('auth.login_page'))
        response.delete_cookie('session_token')
        return response

    user = User.query.filter(
        User.id == user_session.user_id,
        User.Del == 0
    ).first()

    if not user:
        user_session.is_active = False
        db.session.commit()

        session.clear()

        response = redirect(url_for('auth.login_page'))
        response.delete_cookie('session_token')
        return response

    if user.status is False or user.status == "False":
        user_session.is_active = False
        db.session.commit()

        session.clear()

        response = redirect(url_for('auth.login_page'))
        response.delete_cookie('session_token')
        return response

    # 沒超過 30 分鐘，就更新最後活動時間
    user_session.last_activity = now
    db.session.commit()