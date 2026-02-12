from flask import Blueprint, jsonify, request, current_app, session
from services.csv_loader import load_timeline_from_csv, load_relative_from_csv
from services.mysql_pool import get_conn
from services.json_loader import (
    load_list_from_json, load_list_from_json_path,
    list_presets, preset_path, save_preset
)
from services.project_config import (
    save_project_config, list_project_configs,
    get_project_config, latest_project_config
)
from services.template_store import (
    list_template_names, list_template_versions,
    save_template, get_template
)
from services.selection_store import (
    save_selection, list_selections, get_selection
)
from werkzeug.utils import secure_filename
import uuid, os ,json, hashlib

def _resolve_list_path():
    """決定目前使用的 JSON：優先順序：使用者上傳覆寫 > 已選預設 > 系統預設"""
    # 1) 使用者上傳覆寫（session 存檔的實體路徑）
    override_path = session.get("json_list_override")
    if override_path and os.path.isfile(override_path):
        return override_path, "uploaded", os.path.basename(override_path)

    # 2) 已選預設（session 存『名稱』）
    preset_name = session.get("json_preset")
    if preset_name:
        try:
            p = preset_path(preset_name)
            if os.path.isfile(p):
                return p, "preset", preset_name
        except Exception:
            # 名稱失效就略過
            pass

    # 3) 系統預設
    return current_app.config["JSON_LIST_PATH"], "default", os.path.basename(current_app.config["JSON_LIST_PATH"])

# 取得某模板最新 selection 的 id（依 created_at 由新到舊排序）
def _latest_selection_id(tpl: str):
    lst = list_selections(tpl)  # 期望回傳 [{"id": "...", "created_at": 1710000000, ...}, ...]
    if not lst:
        return None
    # 若後端原本未排序，這裡強制以 created_at 排序；沒有 created_at 則當 0
    lst = sorted(lst, key=lambda r: r.get("created_at", 0), reverse=True)
    return lst[0].get("id")

bp = Blueprint("api_data", __name__)

@bp.route('/timelineOutput')
def timelineOutput():
    data = load_timeline_from_csv()
    # 無論有無資料都回 200，Console 不會紅字
    return jsonify(data)  # data 為 [] 時也是 200

@bp.route('/relativeOutput')
def relativetimeOutput():
    data = load_relative_from_csv()
    # 無論有無資料都回 200，Console 不會紅字
    return jsonify(data)  # data 為 [] 時也是 200

# /projects?limit=100&offset=0
@bp.route("/projects", methods=["GET"])
def get_projects():
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    query = "SELECT * FROM fhirmappingview2.projects LIMIT %s OFFSET %s"
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, (limit, offset))
            rows = cur.fetchall()
        return jsonify({"limit": limit, "offset": offset, "count": len(rows), "data": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@bp.route("/project_resource_count/<int:pro_id>", methods=["GET"])
def project_resource_count(pro_id: int):
    query = """
        SELECT COUNT(*) AS cnt
        FROM fhirmappingview2.resourcecatogory_mapping
        WHERE Pro_Id = %s
    """
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, (pro_id,))
            row = cur.fetchone()
        return jsonify({"Pro_Id": pro_id, "count": (row or {}).get("cnt", 0)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

# 取得目前有效的 JSON list（若 session 有覆寫就用覆寫）
@bp.get("/json_list", endpoint="get_json_list")
def get_json_list():
    try:
        path, source, label = _resolve_list_path()
        items = load_list_from_json_path(path)
        return jsonify({"count": len(items), "items": items, "source": source, "label": label})
    except FileNotFoundError:
        return jsonify({"error": f"找不到 JSON 檔案：{current_app.config['JSON_LIST_PATH']}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# # 上傳使用者自訂 JSON list（內容必須是 list）
# @bp.post("/json_list/upload", endpoint="upload_json_list")
# def upload_json_list():
#     try:
#         if 'file' not in request.files:
#             return jsonify({"error": "請附上檔案欄位 file"}), 400
#         f = request.files['file']
#         if f.filename == "":
#             return jsonify({"error": "未選擇檔案"}), 400

#         # 僅允許 .json
#         filename = secure_filename(f.filename)
#         if not filename.lower().endswith(".json"):
#             return jsonify({"error": "僅支援 .json 檔"}), 400

#         # 先讀入記憶體驗證內容
#         raw = f.read()
#         try:
#             import json
#             data = json.loads(raw.decode("utf-8"))
#         except Exception:
#             return jsonify({"error": "JSON 格式錯誤，請確認編碼為 UTF-8 且內容為合法 JSON"}), 400

#         if not isinstance(data, list):
#             return jsonify({"error": "JSON 內容必須是 list"}), 400

#         # 存檔
#         uid = uuid.uuid4().hex
#         save_name = f"{os.path.splitext(filename)[0]}_{uid}.json"
#         save_path = os.path.join(current_app.config["JSON_UPLOAD_DIR"], save_name)
#         with open(save_path, "w", encoding="utf-8") as out:
#             json.dump(data, out, ensure_ascii=False, indent=2)

#         # 設定本次 session 覆寫
#         session["json_list_override"] = save_path

#         return jsonify({
#             "message": "上傳成功，已切換為使用此 JSON",
#             "path": save_path,
#             "count": len(data),
#             "source": "uploaded"
#         })
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

  
    
#串接字串
@bp.post("/join_strings", endpoint="join_strings")
def join_strings():
    try:
        payload = request.get_json(force=True) or {}
        items = payload.get("items") or []
        sep = payload.get("sep", ",")
        if not isinstance(items, list):
            return jsonify({"error": "items 必須為 list"}), 400
        # 將元素都轉字串再 join
        joined = str(sep).join([str(x) for x in items])
        return jsonify({"joined": joined, "count": len(items), "sep": sep})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

    # === 預設清單 ===
@bp.get("/json_list/presets", endpoint="list_json_presets")
def list_json_presets():
    names = list_presets()
    current = session.get("json_preset")
    return jsonify({"presets": names, "current": current})

@bp.post("/json_list/preset/select", endpoint="select_json_preset")
def select_json_preset():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name 必填"}), 400
    try:
        p = preset_path(name)
        if not os.path.isfile(p):
            return jsonify({"error": f"預設 '{name}' 不存在"}), 404
        # 選擇預設時，清掉使用者上傳的覆寫
        session.pop("json_list_override", None)
        session["json_preset"] = name
        return jsonify({"message": f"已切換為預設：{name}", "source": "preset", "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.post("/json_list/preset/create", endpoint="create_json_preset")
def create_json_preset():
    """建立新的命名預設：multipart/form-data，含 name 與 file（.json，內容為 list）"""
    if 'file' not in request.files:
        return jsonify({"error": "請附上檔案欄位 file"}), 400
    name = (request.form.get("name") or "").strip()
    overwrite = (request.form.get("overwrite") or "").lower() in ("1", "true", "yes", "on")
    if not name:
        return jsonify({"error": "name 必填"}), 400

    f = request.files['file']
    if f.filename == "":
        return jsonify({"error": "未選擇檔案"}), 400
    filename = secure_filename(f.filename)
    if not filename.lower().endswith(".json"):
        return jsonify({"error": "僅支援 .json 檔"}), 400

    # 驗證 JSON
    try:
        raw = f.read()
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, list):
            return jsonify({"error": "JSON 內容必須是 list"}), 400
    except Exception:
        return jsonify({"error": "JSON 格式錯誤，請確認 UTF-8 與合法內容"}), 400

    try:
        path = save_preset(name, data, overwrite=overwrite)
        # 切換到剛建立的預設，並清掉上傳覆寫
        session.pop("json_list_override", None)
        session["json_preset"] = name
        return jsonify({"message": f"已建立並切換預設：{name}", "source": "preset", "name": name, "path": path, "count": len(data)})
    except FileExistsError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# === 沿用原有 upload/reset，但 reset 也清掉預設 ===
@bp.post("/json_list/upload", endpoint="upload_json_list")
def upload_json_list():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "請附上檔案欄位 file"}), 400
        f = request.files['file']
        if f.filename == "":
            return jsonify({"error": "未選擇檔案"}), 400

        filename = secure_filename(f.filename)
        if not filename.lower().endswith(".json"):
            return jsonify({"error": "僅支援 .json 檔"}), 400

        raw = f.read()
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return jsonify({"error": "JSON 格式錯誤，請確認 UTF-8 與合法內容"}), 400
        if not isinstance(data, list):
            return jsonify({"error": "JSON 內容必須是 list"}), 400

        uid = uuid.uuid4().hex
        save_name = f"{os.path.splitext(filename)[0]}_{uid}.json"
        save_path = os.path.join(current_app.config["JSON_UPLOAD_DIR"], save_name)
        with open(save_path, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=False, indent=2)

        # 上傳匿名覆寫時，清掉選擇的預設
        session["json_list_override"] = save_path
        session.pop("json_preset", None)

        return jsonify({"message": "上傳成功，已切換為此次 JSON", "path": save_path, "count": len(data), "source": "uploaded"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/json_list/reset", endpoint="reset_json_list")
def reset_json_list():
    session.pop("json_list_override", None)
    session.pop("json_preset", None)
    return jsonify({"message": "已恢復為系統預設 JSON", "source": "default"})

#project_cfg project_config.py
# 儲存目前選取為一份設定檔
@bp.post("/project_cfg/save", endpoint="save_project_cfg")
def save_project_cfg():
    payload = request.get_json(force=True) or {}
    project_id = (payload.get("project_id") or "").strip()
    name = (payload.get("name") or "").strip()
    items = payload.get("items") or []
    sep = payload.get("sep", ",")
    source = payload.get("source") or {}  # 可傳 {type,label} 等

    if not project_id:
        return jsonify({"error": "project_id 必填"}), 400
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "items 必須為非空 list"}), 400

    meta = {"sep": sep, "source": source}
    try:
        saved = save_project_config(project_id, items, name=name, meta=meta)
        return jsonify({"message": "已儲存設定", **saved})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 列出某專案所有設定（新→舊）
@bp.get("/project_cfg/list", endpoint="list_project_cfg")
def list_project_cfg():
    project_id = (request.args.get("project_id") or "").strip()
    if not project_id:
        return jsonify({"error": "project_id 必填"}), 400
    try:
        data = list_project_configs(project_id)
        return jsonify({"project_id": project_id, "configs": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 讀取指定設定
@bp.get("/project_cfg/get", endpoint="get_project_cfg")
def get_project_cfg():
    project_id = (request.args.get("project_id") or "").strip()
    cfg_id = (request.args.get("id") or "").strip()
    if not project_id or not cfg_id:
        return jsonify({"error": "project_id 與 id 必填"}), 400
    try:
        data = get_project_config(project_id, cfg_id)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "找不到設定"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 取得此專案最新的一份設定（用來「下次自動載入上次勾選」）
@bp.get("/project_cfg/latest", endpoint="latest_project_cfg")
def latest_project_cfg():
    project_id = (request.args.get("project_id") or "").strip()
    if not project_id:
        return jsonify({"error": "project_id 必填"}), 400
    try:
        data = latest_project_config(project_id)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "此專案尚無設定"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    


# ===== 模板 API =====

# 列出所有模板名稱
@bp.get("/tpl/names", endpoint="tpl_names")
def tpl_names():
    return jsonify({"names": list_template_names()})

# 列出某模板的歷史版本（新→舊）
@bp.get("/tpl/list", endpoint="tpl_list")
def tpl_list():
    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name 必填"}), 400
    return jsonify({"name": name, "versions": list_template_versions(name)})

# 取得模板內容（可帶 id，未帶則取最新）
@bp.get("/tpl/get", endpoint="tpl_get")
def tpl_get():
    name = (request.args.get("name") or "").strip()
    cfg_id = (request.args.get("id") or "").strip() or None
    if not name:
        return jsonify({"error": "name 必填"}), 400
    try:
        data = get_template(name, cfg_id)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "找不到模板或尚無版本"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 上傳 JSON 檔建立新版本（multipart：name + file）
@bp.post("/tpl/upload", endpoint="tpl_upload")
def tpl_upload():
    if 'file' not in request.files:
        return jsonify({"error": "請附上檔案欄位 file"}), 400
    name = (request.form.get("name") or "").strip()
    message = (request.form.get("message") or "").strip()
    if not name:
        return jsonify({"error": "name 必填"}), 400
    f = request.files['file']
    if f.filename == "":
        return jsonify({"error": "未選擇檔案"}), 400
    if not f.filename.lower().endswith(".json"):
        return jsonify({"error": "僅支援 .json 檔"}), 400
    try:
        raw = f.read().decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, list):
            return jsonify({"error": "JSON 內容必須是 list"}), 400
        saved = save_template(name, data, message=message)
        return jsonify({"message": "已建立新版本", **saved})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 直接以 JSON 儲存（可用於編輯後存檔）
@bp.post("/tpl/save", endpoint="tpl_save")
def tpl_save():
    payload = request.get_json(force=True) or {}
    name = (payload.get("name") or "").strip()
    fields = payload.get("fields") or []
    message = (payload.get("message") or "").strip()
    if not name:
        return jsonify({"error": "name 必填"}), 400
    if not isinstance(fields, list) or not fields:
        return jsonify({"error": "fields 必須為非空 list"}), 400
    try:
        saved = save_template(name, fields, message=message)
        return jsonify({"message": "已儲存為新版本", **saved})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ===== 選取紀錄 API =====

# 儲存一份選取紀錄：groups = [{text1, text2, text3}, ...]
@bp.post("/sel/save", endpoint="sel_save")
def sel_save():
    payload = request.get_json(force=True) or {}
    tpl = (payload.get("template") or "").strip()
    groups = payload.get("groups") or []
    meta = payload.get("meta") or {}
    if not tpl:
        return jsonify({"error": "template 必填"}), 400
    if not isinstance(groups, list) or not groups:
        return jsonify({"error": "groups 必須為非空 list"}), 400
    try:
        saved = save_selection(tpl, groups, meta=meta)
        return jsonify({"message": "已儲存選取紀錄", **saved})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 列出某模板的選取歷史
@bp.get("/sel/list", endpoint="sel_list")
def sel_list():
    tpl = (request.args.get("template") or "").strip()
    if not tpl:
        return jsonify({"error": "template 必填"}), 400
    return jsonify({"template": tpl, "records": list_selections(tpl)})

# 取得選取紀錄：id 可選；不帶 id 則回傳最新
@bp.get("/sel/get", endpoint="sel_get")
def sel_get():
    tpl = (request.args.get("template") or "").strip()
    rid = (request.args.get("id") or "").strip()

    if not tpl:
        return jsonify({"error": "template 必填"}), 400

    # 沒帶 id -> 取最新
    if not rid:
        rid = _latest_selection_id(tpl)
        if not rid:
            return jsonify({"error": "此模板尚無選取紀錄"}), 404

    try:
        data = get_selection(tpl, rid)  # 期望回傳 {"groups":[...], ...}
        # 補上識別資訊，方便前端使用
        if isinstance(data, dict):
            data.setdefault("template", tpl)
            data.setdefault("id", rid)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "找不到選取紀錄"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 相容別名：/sel/latest -> 等同於 /sel/get（不帶 id）
@bp.get("/sel/latest", endpoint="sel_latest")
def sel_latest():
    tpl = (request.args.get("template") or "").strip()
    if not tpl:
        return jsonify({"error": "template 必填"}), 400

    rid = _latest_selection_id(tpl)
    if not rid:
        return jsonify({"error": "此模板尚無選取紀錄"}), 404

    try:
        data = get_selection(tpl, rid)
        if isinstance(data, dict):
            data.setdefault("template", tpl)
            data.setdefault("id", rid)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "找不到選取紀錄"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
# # 取得某筆選取紀錄
# @bp.get("/sel/get", endpoint="sel_get")
# def sel_get():
#     tpl = (request.args.get("template") or "").strip()
#     rid = (request.args.get("id") or "").strip()
#     if not tpl or not rid:
#         return jsonify({"error": "template 與 id 必填"}), 400
#     try:
#         data = get_selection(tpl, rid)
#         return jsonify(data)
#     except FileNotFoundError:
#         return jsonify({"error": "找不到選取紀錄"}), 404
#     except Exception as e:
#         return jsonify({"error": str(e)}), 400
    

# # 取得某模板的「最新」選取紀錄（groups）
# @bp.get("/sel/latest", endpoint="sel_latest")
# def sel_latest():
#     tpl = (request.args.get("template") or "").strip()
#     if not tpl:
#         return jsonify({"error": "template 必填"}), 400
#     try:
#         lst = list_selections(tpl)
#         if not lst:
#             return jsonify({"error": "此模板尚無選取紀錄"}), 404
#         latest_id = lst[0]["id"]
#         data = get_selection(tpl, latest_id)
#         return jsonify(data)
#     except FileNotFoundError:
#         return jsonify({"error": "找不到選取紀錄"}), 404
#     except Exception as e:
#         return jsonify({"error": str(e)}), 400


# 上傳 JSON，依樣板最新一筆 groups 產生 IDn:"<hash>-text2-text3"
# multipart/form-data: file=<json> , template=<模板名稱> [, sel_id=<特定紀錄ID(可省略取最新)>]
@bp.post("/apply/compose", endpoint="apply_compose")
def apply_compose():
    template = (request.form.get("template") or "").strip()
    sel_id = (request.form.get("sel_id") or "").strip()
    f = request.files.get("file")

    if not template:
        return jsonify({"error": "template 必填"}), 400
    if not f or f.filename == "":
        return jsonify({"error": "請附上檔案欄位 file"}), 400
    if not f.filename.lower().endswith(".json"):
        return jsonify({"error": "僅支援 .json 檔"}), 400

    # 解析上傳 JSON（需為 list[object,...]）
    try:
        raw = f.read().decode("utf-8")
        data = json.loads(raw)
    except Exception:
        return jsonify({"error": "JSON 格式錯誤或編碼非 UTF-8"}), 400
    if not isinstance(data, list):
        return jsonify({"error": "上傳 JSON 須為陣列(list)；每筆為物件(dict)"}), 400

    # 取得要用的 groups（指定 sel_id，沒給就拿最新）
    try:
        if sel_id:
            sel = get_selection(template, sel_id)
        else:
            lst = list_selections(template)
            if not lst:
                return jsonify({"error": "此模板尚無選取紀錄"}), 404
            sel = get_selection(template, lst[0]["id"])
    except FileNotFoundError:
        return jsonify({"error": "找不到選取紀錄"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    groups = sel.get("groups") or []

    # 預先把 groups 解析成 (gid, fields[], t2, t3)
    parsed = []
    for g in groups:
        gid = str(g.get("id") or "").strip()
        t1 = str(g.get("text1") or "")
        fields = [s.strip() for s in t1.split(",") if s.strip()]
        t2 = str(g.get("text2") or "")
        t3 = str(g.get("text3") or "")
        if gid and fields:
            parsed.append((gid, fields, t2, t3))

    # 定義雜湊：把欄位值用 '|' 連接後做 SHA256，取前 12 碼（可調）
    def make_hash(values):
        joined = "|".join([str(v) for v in values])
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()#[:12]

    # 轉換每一筆資料
    out = []
    for row in data:
        row_out = dict(row) if isinstance(row, dict) else {"__value__": row}
        for gid, fields, t2, t3 in parsed:
            vals = [row.get(f, "") if isinstance(row, dict) else "" for f in fields]
            h = make_hash(vals)
            composed = f"{h}-{t2}-{t3}" if (t2 or t3) else h
            row_out[gid] = composed
        out.append(row_out)

    # 回傳（前端可顯示預覽並提供下載）
    return jsonify({
        "template": template,
        "selection_id": sel.get("id"),
        "groups": len(parsed),
        "count": len(out),
        "data": out
    })