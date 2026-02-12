# blueprints/api_w.py
from flask import Blueprint, jsonify, Response, stream_with_context, request, current_app
from pathlib import Path
import time
from API_W_v3 import Export_data, Main_vision_table, Main_aggregate_table  # 依你的實際路徑調整
import requests
from config import BaseConfig as cfg  # ← 關鍵：讀 config
from urllib.parse import quote, quote_plus
import os
from datetime import datetime, timezone


bp = Blueprint("api_w", __name__, url_prefix="/api")

def _ms(t):  # 秒 -> 毫秒（整數）
    return int(round(t * 1000))


#取得 個案歷程 Main2.csv 和 統計報表 age_gender_cross.csv 檔案時間
@bp.route("/data_status", methods=["GET"])
def data_status():
    # 目標檔案路徑（相對於 static）
    static_dir = Path(current_app.static_folder)
    main2_path = static_dir / "data" / "data_ndjson" / "Main2.csv"
    agg_path   = static_dir / "data" / "Agg_tables" / "age_gender_cross.csv"

    def get_file_info(p: Path):
        if p.exists() and p.is_file():
            # 用 UTC ISO 格式回傳，前端再轉本地時間顯示
            ts = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
            return {"exists": True, "mtime_iso": ts, "path": str(p)}
        else:
            return {"exists": False, "mtime_iso": None, "path": str(p)}

    return jsonify({
        "main2": get_file_info(main2_path),
        "agg":   get_file_info(agg_path)
    }), 200


#Export_data
@bp.post("/export", endpoint="export")
def export_ep():
    t0 = time.perf_counter()
    try:
        info = Export_data()  # 可能回「字串路徑」或「dict」

        # 情況 A：Export_data 回 dict（建議的診斷格式）
        if isinstance(info, dict):
            info.setdefault("stage", "export")
            info["duration_ms"] = _ms(time.perf_counter() - t0)
            code = 200 if info.get("ok") else 500
            return jsonify(info), code

        # 情況 B：Export_data 回字串路徑（舊版）
        folder = info
        if not folder:
            return jsonify({
                "ok": False,
                "stage": "export",
                "message": "匯出失敗或無回傳路徑",
                "duration_ms": _ms(time.perf_counter() - t0),
            }), 500

        p = Path(folder)
        ndjson_files = sorted([f.name for f in p.glob("*.ndjson")])
        return jsonify({
            "ok": True,
            "stage": "export",
            "folder": str(p.resolve()),
            "ndjson_count": len(ndjson_files),
            "ndjson_files": ndjson_files[:10],  # 只預覽前 10 筆
            "duration_ms": _ms(time.perf_counter() - t0),
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "stage": "export",
            "message": str(e),
            "duration_ms": _ms(time.perf_counter() - t0),
        }), 500

@bp.post("/main-table", endpoint="main_table")
def main_table_ep():
    t0 = time.perf_counter()
    try:
        # 建議：Main_vision_table() 最後 return 輸出的 CSV 路徑
        csv_path = Main_vision_table()

        rows = None
        cols = None
        try:
            # 若要更精準的數字，可直接讓 Main_vision_table() 回傳 (csv_path, rows, cols)
            import pandas as pd
            import os
            if csv_path and Path(csv_path).is_file():
                df_head = pd.read_csv(csv_path, nrows=5)     # 輕量讀頭幾行
                cols = int(df_head.shape[1])
                # 安全估算列數（僅當檔案不大時可 read；大檔請在函式內回傳 rows 比較好）
                rows = sum(1 for _ in open(csv_path, "r", encoding="utf-8-sig")) - 1
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "stage": "main",
            "csv_path": str(Path(csv_path).resolve()) if csv_path else None,
            "rows": rows,
            "cols": cols,
            "duration_ms": _ms(time.perf_counter() - t0)
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "stage": "main",
            "message": str(e),
            "duration_ms": _ms(time.perf_counter() - t0)
        }), 500

#Main_aggregate_table  
@bp.post("/aggregate", endpoint="aggregate")
def aggregate_ep():
    t0 = time.perf_counter()
    try:
        # ===== Aggregate Table 路徑設定 =====
        DATA_NDJSON_DIR = Path(cfg.BASE_DIR_STAC) / "data" / "data_ndjson"

        # 找出最新的資料夾（若無子資料夾，退回 data_ndjson 自己）
        if DATA_NDJSON_DIR.exists():
            subfolders = [f for f in DATA_NDJSON_DIR.iterdir() if f.is_dir()]
            if subfolders:
                folder_path = str(max(subfolders, key=os.path.getctime))
            else:
                folder_path = str(DATA_NDJSON_DIR)
        else:
            folder_path = str(DATA_NDJSON_DIR)

        # Agg_tables 資料夾（固定輸出到這裡）
        AGGREGATE_TARGET_FOLDER = Path(cfg.BASE_DIR_STAC) / "data" / "Agg_tables"
        AGGREGATE_TARGET_FOLDER.mkdir(parents=True, exist_ok=True)
        target_folder = str(AGGREGATE_TARGET_FOLDER)

        # 執行主程式
        Main_aggregate_table(folder_path, target_folder)

        return jsonify({
            "ok": True,
            "stage": "aggregate",
            "folder_path": folder_path,
            "target_folder": target_folder,
            "message": "統計報表更新 已完成",
            "duration_ms": _ms(time.perf_counter() - t0)
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "stage": "aggregate",
            "message": str(e),
            "duration_ms": _ms(time.perf_counter() - t0)
        }), 500
    

# ---- 取得 token（client credentials）----
def get_token():
    r = requests.post(
        cfg.OAUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": cfg.OAUTH_CLIENT_ID,
            "client_secret": cfg.OAUTH_CLIENT_SECRET,
        },
        timeout=cfg.REQUEST_TIMEOUT,
        verify=getattr(cfg, "VERIFY_TLS", True),
    )
    r.raise_for_status()
    return r.json().get("access_token")

#取得patient資料
@bp.get("/fhir/patient/<pid>", endpoint="fhir_patient")
def fhir_patient(pid: str):
    """伺服器端帶 token 代理取得 Patient JSON"""
    try:
        token = get_token()
    except Exception as e:
        return jsonify({"ok": False, "message": f"取得 token 失敗：{e}"}), 500
    
    url = f"{cfg.FHIR_SERVER_URL.rstrip('/')}/Patient/{quote(pid, safe='')}"

    try:
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/fhir+json"
            },
            timeout=cfg.REQUEST_TIMEOUT,
            verify=getattr(cfg, "VERIFY_TLS", True),
            stream=True,
        )
    except Exception as e:
        return jsonify({"ok": False, "message": f"連線 FHIR 失敗：{e}"}), 502

    # 直接把上游內容串流回前端
    def generate():
        for chunk in r.iter_content(cfg.PROXY_CHUNK_SIZE):
            if chunk:
                yield chunk

    resp = Response(stream_with_context(generate()), status=r.status_code)
    resp.headers["Content-Type"] = r.headers.get("Content-Type", "application/fhir+json; charset=utf-8")
    return resp


#取得condition資料
@bp.get("/fhir/condition/<cid>", endpoint="fhir_condition")
def fhir_condition(cid: str):
    # 取得 token、帶 Authorization 向上游取：
    url = f"{cfg.FHIR_SERVER_URL.rstrip('/')}/Condition/{quote(cid, safe='')}"
    try:
        token = get_token()
    except Exception as e:
        return jsonify({"ok": False, "message": f"取得 token 失敗：{e}"}), 500
    
    try:
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/fhir+json"
            },
            timeout=cfg.REQUEST_TIMEOUT,
            verify=getattr(cfg, "VERIFY_TLS", True),
            stream=True,
        )
    except Exception as e:
        return jsonify({"ok": False, "message": f"連線 FHIR 失敗：{e}"}), 502
    
    def generate():
        for chunk in r.iter_content(cfg.PROXY_CHUNK_SIZE):
            if chunk:
                yield chunk

    resp = Response(stream_with_context(generate()), status=r.status_code)
    resp.headers["Content-Type"] = r.headers.get("Content-Type", "application/fhir+json; charset=utf-8")
    return resp

#取得medication資料
@bp.get("/fhir/medication/<mid>", endpoint="fhir_medication")
def fhir_medication(mid: str):
    # 取得 token、帶 Authorization 向上游取：
    url = f"{cfg.FHIR_SERVER_URL.rstrip('/')}/MedicationRequest/{quote(mid, safe='')}"
    try:
        token = get_token()
    except Exception as e:
        return jsonify({"ok": False, "message": f"取得 token 失敗：{e}"}), 500
    
    try:
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/fhir+json"
            },
            timeout=cfg.REQUEST_TIMEOUT,
            verify=getattr(cfg, "VERIFY_TLS", True),
            stream=True,
        )
    except Exception as e:
        return jsonify({"ok": False, "message": f"連線 FHIR 失敗：{e}"}), 502
    
    def generate():
        for chunk in r.iter_content(cfg.PROXY_CHUNK_SIZE):
            if chunk:
                yield chunk

    resp = Response(stream_with_context(generate()), status=r.status_code)
    resp.headers["Content-Type"] = r.headers.get("Content-Type", "application/fhir+json; charset=utf-8")
    return resp


#取得procedure資料
@bp.get("/fhir/procedure/<pid>", endpoint="fhir_procedure")
def fhir_procedure(pid: str):
    # 取得 token、帶 Authorization 向上游取：
    url = f"{cfg.FHIR_SERVER_URL.rstrip('/')}/Procedure/{quote(pid, safe='')}"
    try:
        token = get_token()
    except Exception as e:
        return jsonify({"ok": False, "message": f"取得 token 失敗：{e}"}), 500
    
    try:
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/fhir+json"
            },
            timeout=cfg.REQUEST_TIMEOUT,
            verify=getattr(cfg, "VERIFY_TLS", True),
            stream=True,
        )
    except Exception as e:
        return jsonify({"ok": False, "message": f"連線 FHIR 失敗：{e}"}), 502
    
    def generate():
        for chunk in r.iter_content(cfg.PROXY_CHUNK_SIZE):
            if chunk:
                yield chunk

    resp = Response(stream_with_context(generate()), status=r.status_code)
    resp.headers["Content-Type"] = r.headers.get("Content-Type", "application/fhir+json; charset=utf-8")
    return resp


#取得Observation資料
@bp.get("/fhir/observation/<pid>", endpoint="fhir_Observation")
def fhir_Observation(pid: str):
    # 取得 token、帶 Authorization 向上游取：
    url = f"{cfg.FHIR_SERVER_URL.rstrip('/')}/Observation/{quote(pid, safe='')}"
    try:
        token = get_token()
    except Exception as e:
        return jsonify({"ok": False, "message": f"取得 token 失敗：{e}"}), 500
    
    try:
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/fhir+json"
            },
            timeout=cfg.REQUEST_TIMEOUT,
            verify=getattr(cfg, "VERIFY_TLS", True),
            stream=True,
        )
    except Exception as e:
        return jsonify({"ok": False, "message": f"連線 FHIR 失敗：{e}"}), 502
    
    def generate():
        for chunk in r.iter_content(cfg.PROXY_CHUNK_SIZE):
            if chunk:
                yield chunk

    resp = Response(stream_with_context(generate()), status=r.status_code)
    resp.headers["Content-Type"] = r.headers.get("Content-Type", "application/fhir+json; charset=utf-8")
    return resp


@bp.post("/fhir/search/patients")
def fhir_search_patients():
    try:
        body = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"ok": False, "message": "請以 JSON 傳入查詢條件"}), 400

    # ===== 讀取查詢條件 =====
    gender         = (body.get("gender") or "").strip()
    by_from        = body.get("birthYearFrom")
    by_to          = body.get("birthYearTo")
    cond_codes     = [c.strip() for c in (body.get("conditionCodes") or []) if str(c).strip()]
    proc_codes     = [c.strip() for c in (body.get("procedureCodes") or []) if str(c).strip()]
    med_codes      = [c.strip() for c in (body.get("medicationCodes") or []) if str(c).strip()]
    cond_from      = (body.get("conditionDateFrom") or "").strip()
    cond_to        = (body.get("conditionDateTo") or "").strip()

    # === 新增：前端分頁參數 ===
    page           = max(1, int(body.get("page") or 1))
    page_size      = max(1, min(100, int(body.get("pageSize") or 10)))  # 最高 100，避免太大
    _count_default = int(body.get("_count") or page_size)               # 兼容舊參數

    # ===== 組查詢 =====
    from urllib.parse import quote_plus
    q = []
    q_count = []

    if gender:
        q.append(f"gender={quote_plus(gender)}")
    if by_from:
        q.append(f"birthdate=ge{quote_plus(str(by_from))}-01-01")
    if by_to:
        q.append(f"birthdate=le{quote_plus(str(by_to))}-12-31")
    if cond_codes:
        q.append(f"_has:Condition:subject:code={quote_plus(','.join(cond_codes), safe=',')}")
        if cond_from:
            q.append(f"_has:Condition:subject:onset-date=ge{quote_plus(cond_from)}")
        if cond_to:
            q.append(f"_has:Condition:subject:onset-date=le{quote_plus(cond_to)}")
    if proc_codes:
        q.append(f"_has:Procedure:subject:code={quote_plus(','.join(proc_codes), safe=',')}")
    if med_codes:
        q.append(f"_has:MedicationRequest:subject:code={quote_plus(','.join(med_codes), safe=',')}")

    # === 分頁：每頁筆數 ===
    q_count = q.copy()
    q.append(f"_count={_count_default}")

    # === 嘗試 offset 分頁（多數伺服器支援） ===
    offset = (page - 1) * _count_default
    if offset > 0:
        # HAPI FHIR 支援 _getpagesoffset；若伺服器不支援，後面會 fallback
        q.append(f"_getpagesoffset={offset}")

    base = f"{cfg.FHIR_SERVER_URL.rstrip('/')}/Patient"
    url = base + "?" + "&".join(q) if q else base

    # 先取總筆數（不取 entry）
    q_count.append(f"_summary=count&_total=accurate")
    url_count = base + "?" + "&".join(q_count) if q_count else base

    # ===== 取得 token =====
    try:
        token = get_token()
    except Exception as e:
        return jsonify({"ok": False, "message": f"取得 token 失敗：{e}"}), 500

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    timeout = getattr(cfg, "REQUEST_TIMEOUT", 30)
    verify  = getattr(cfg, "VERIFY_TLS", True)

    # ===== 1) 取總數 =====
    total_from_fhir = None
    try:
        rc = requests.get(url_count, headers=headers, timeout=timeout, verify=verify)
        rc_bundle = rc.json()
        total_from_fhir = rc_bundle.get("total")
    except Exception:
        total_from_fhir = None

    # ===== 2) 取當頁資料（先用 offset 模式） =====
    try:
        r = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    except Exception as e:
        return jsonify({"ok": False, "message": f"請求 FHIR 失敗：{e}", "request_url": url}), 502

    try:
        bundle = r.json()
    except Exception:
        return jsonify({"ok": False, "message": f"FHIR 非 JSON 回應（HTTP {r.status_code})", "request_url": url}), 502

    # 若伺服器不支援 _getpagesoffset（或被忽略），且 page>1，嘗試沿著 next link 前進
    def _get_next_link(bdl):
        for lk in (bdl.get("link") or []):
            if lk.get("relation") == "next" and lk.get("url"):
                return lk["url"]
        return None

    if page > 1 and offset > 0:
        # 確認我們真的拿到第 page 頁（有些伺服器會忽略 offset）
        # 若偵測不到 offset 生效、且可取得 next，就手動走到指定頁
        # 這裡用簡單策略：如果 bundle.entry 存在但其數量 < offset + 1，或 page>1 但沒有 offset 特徵，就沿 next 前進 page-1 次
        # （注意：大資料量時建議直接依伺服器的 next 分頁）
        reached = True  # 先假定成功
        if r.status_code == 200 and not bundle.get("entry") and _get_next_link(bundle):
            reached = False
        if not reached:
            next_url = base + "?" + "&".join(q[:-1] + [f"_count={_count_default}"])  # 不帶 offset 從第 1 頁開始
            # 逐頁前進
            try:
                for _ in range(page - 1):
                    rr = requests.get(next_url, headers=headers, timeout=timeout, verify=verify)
                    bb = rr.json()
                    nu = _get_next_link(bb)
                    if not nu:
                        bundle = bb
                        break
                    bundle = bb
                    next_url = nu
            except Exception:
                pass  # 若失敗就使用目前 bundle

    # ===== 整理當頁資料 =====
    patients = []
    for ent in bundle.get("entry", []) or []:
        res = ent.get("resource") or {}
        if res.get("resourceType") == "Patient":
            patients.append({
                "id": res.get("id"),
                "gender": res.get("gender"),
                "birthDate": res.get("birthDate"),
                "link": f"/api/fhir/patient/{res.get('id')}"
            })

    total_count = (
        total_from_fhir
        if isinstance(total_from_fhir, int)
        else (bundle.get("total") if isinstance(bundle.get("total"), int) else None)
    )
    if total_count is None:
        total_count = len(patients)  # fallback（極端狀況）

    return jsonify({
        "ok": True,
        "http": r.status_code,
        "request_url": url,
        "request_url_count": url_count,
        "page": page,
        "pageSize": _count_default,
        "total": total_count,   # 全部符合條件的總筆數
        "count": len(patients), # 本頁筆數
        "patients": patients,
        "bundle": bundle,                  # 若太大可移除或改為條件回傳
        "bundleLink": bundle.get("link", []),  # 可選：回傳伺服器的分頁連結供除錯
    })

