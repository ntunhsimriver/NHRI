# routes/fhir_api.py
from flask import Blueprint, request, jsonify

def create_fhir_blueprint(client=None, db=None):
    # 藍圖名稱要叫 fhir_api，模板才可 url_for('fhir_api.*')
    bp = Blueprint('fhir_api', __name__, url_prefix='/fhir')

    # 1) 你原本常用的 Patient 端點（可選）
    @bp.get('/patient/<pid>', endpoint='get_patient')
    def get_patient(pid):
        try:
            return jsonify(client.get_resource('Patient', pid))
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.get('/patient', endpoint='search_patient')
    def search_patient():
        try:
            return jsonify(client.search('Patient', **request.args.to_dict()))
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # 2) 通用端點（滿足 url_for('fhir_api.get_resource') / ('fhir_api.search')）
    # GET/POST 同一路由，同一個 endpoint 名稱
    @bp.route('/resource/<rtype>/<rid>', methods=['GET', 'POST'], endpoint='get_resource')
    def get_resource(rtype, rid):
        try:
            # 若是 POST，可用 body 覆寫 rtype/rid（可選）
            if request.method == 'POST':
                payload = request.get_json(silent=True) or {}
                rtype = (payload.get('resource_type') or rtype).strip()
                rid   = (payload.get('resource_id')   or rid).strip()

            if not rtype or not rid:
                return jsonify({'error': 'missing rtype or rid'}), 400

            data = client.get_resource(rtype, rid)
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # 只用 body 的純 POST 端點（若前端不想帶路徑參數，可用這個）
    @bp.post('/resource', endpoint='get_resource_by_body')
    def get_resource_by_body():
        try:
            payload = request.get_json(force=True) or {}
            rtype = (payload.get('resource_type') or '').strip()
            rid   = (payload.get('resource_id')   or '').strip()
            if not rtype or not rid:
                return jsonify({'error': 'resource_type 和 resource_id 必填'}), 400
            return jsonify(client.get_resource(rtype, rid))
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.get('/resource/<rtype>', endpoint='search')
    def search(rtype):
        try:
            return jsonify(client.search(rtype, **request.args.to_dict()))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    @bp.post('/resource/put', endpoint='put_resource')
    def put_resource():
        try:
            payload = request.get_json(force=True) or {}
            rtype = (payload.get('resource_type') or '').strip()
            rid   = (payload.get('resource_id')   or '').strip()
            resource = payload.get('resource')

            if not rtype or not rid or not isinstance(resource, dict):
                return jsonify({'error': 'resource_type、resource_id 與 resource(物件) 必填'}), 400

            # 嘗試呼叫 FHIRClient 內可能存在的方法名稱
            if hasattr(client, 'put_resource'):
                result = client.put_resource(rtype, rid, resource)
            elif hasattr(client, 'update_resource'):
                result = client.update_resource(rtype, rid, resource)
            elif hasattr(client, 'request') and callable(getattr(client, 'request')):
                # 若你的 FHIRClient 有通用 request(method, path, json=...) 介面
                result = client.request('PUT', f'/{rtype}/{rid}', json=resource)
            else:
                return jsonify({'error': 'FHIRClient 未提供 put/update 方法，請在 mylib.fhir_client 中實作 put_resource(rtype, rid, resource)'}), 501

            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return bp



