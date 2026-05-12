import json
from collections import Counter
from models.project import Project, ProjectMember
from blueprints import fhir 

def find_references(obj, target_type, path=""):
    refs = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            if (
                key == "reference"
                and isinstance(value, str)
                and value.startswith(f"{target_type}/")
            ):
                refs.append({
                    "path": current_path,
                    "reference": value
                })

            refs.extend(find_references(value, target_type, current_path))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            refs.extend(find_references(item, target_type, f"{path}[{i}]"))

    return refs


def collect_observation_reference_check(data):
    result = []

    total_observation = 0
    observation_with_patient = 0
    observation_with_device = 0
    observation_with_both = 0
    observation_missing_patient = 0
    observation_missing_device = 0

    for entry_index, entry in enumerate(data.get("entry", [])):
        resource = entry.get("resource", {})

        if resource.get("resourceType") != "Observation":
            continue

        total_observation += 1

        patient_refs = find_references(resource, "Patient")
        device_refs = find_references(resource, "Device")

        has_patient = len(patient_refs) > 0
        has_device = len(device_refs) > 0

        if has_patient:
            observation_with_patient += 1
        else:
            observation_missing_patient += 1

        if has_device:
            observation_with_device += 1
        else:
            observation_missing_device += 1

        if has_patient and has_device:
            observation_with_both += 1

        result.append({
            "entry_index": entry_index,
            "observation_id": resource.get("id"),

            "has_patient_reference": has_patient,
            "patient_reference": patient_refs[0]["reference"] if has_patient else None,
            "patient_reference_path": patient_refs[0]["path"] if has_patient else None,

            "has_device_reference": has_device,
            "device_reference": device_refs[0]["reference"] if has_device else None,
            "device_reference_path": device_refs[0]["path"] if has_device else None,
        })

    summary = {
        "total_observation": total_observation,
        "observation_with_patient": observation_with_patient,
        "observation_with_device": observation_with_device,
        "observation_with_both_patient_and_device": observation_with_both,
        "observation_missing_patient": observation_missing_patient,
        "observation_missing_device": observation_missing_device,
    }

    return summary, result

def upload_FHIR_mappingID(study_id, data):
    ProjectMemberInfo = ProjectMember.query.filter_by(
        project_id=study_id,
        Del=0
    ).all()

    resource_counter = Counter()

    for entry in data.get("entry", []):
        resource = entry.get("resource", {})
        res_type = resource.get("resourceType")

        if res_type:
            resource_counter[res_type] += 1

    # replace 前：每筆 Observation 檢查 Patient / Device reference
    observation_reference_summary_before, observation_reference_logs_before = collect_observation_reference_check(data)

    json_str = json.dumps(data, ensure_ascii=False)
    replace_count = 0

    for row in ProjectMemberInfo:
        if row.old_patient_id and row.new_patient_id:
            old_value = row.old_patient_id
            new_value = row.new_patient_id

            count_before_replace = json_str.count(old_value)

            if count_before_replace > 0:
                replace_count += count_before_replace
                json_str = json_str.replace(old_value, new_value)

    data = json.loads(json_str)

    patient_replace_logs = []
    patient_not_found = []

    # 專門處理 Patient.id
    for entry in data.get("entry", []):
        resource = entry.get("resource", {})

        if resource.get("resourceType") != "Patient":
            continue

        old_id = resource.get("id")

        if not old_id:
            continue

        old_ref = f"Patient/{old_id}"

        matched_row = None

        for row in ProjectMemberInfo:
            if row.old_patient_id in [old_id, old_ref]:
                matched_row = row
                break

        if matched_row:
            new_id = matched_row.new_patient_id.split("/", 1)[-1]

            patient_replace_logs.append({
                "original_id": old_id,
                "original_reference": old_ref,
                "new_patient_id": new_id,
                "new_patient_reference": matched_row.new_patient_id,
                "action": "Patient.id 已替換"
            })

            resource["id"] = new_id

        else:
            patient_not_found.append({
                "original_id": old_id,
                "original_reference": old_ref,
                "action": "找不到對應 ProjectMember，未替換"
            })

    # replace 後：每筆 Observation 檢查 Patient / Device reference
    observation_reference_summary_after, observation_reference_logs_after = collect_observation_reference_check(data)

    stats = {
        "total_resources": sum(resource_counter.values()),
        "resource_count": dict(resource_counter),

        "reference_replace_count": replace_count,

        "observation_reference_summary_before": observation_reference_summary_before,
        "observation_reference_logs_before": observation_reference_logs_before,

        "observation_reference_summary_after": observation_reference_summary_after,
        "observation_reference_logs_after": observation_reference_logs_after,

        "patient_replace_count": len(patient_replace_logs),
        "patient_not_found_count": len(patient_not_found),
        "patient_replace_logs": patient_replace_logs,
        "patient_not_found": patient_not_found
    }

    with open("input_result.json", "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)

    with open("input_result_stats.json", "w", encoding="utf-8") as json_file:
        json.dump(stats, json_file, ensure_ascii=False, indent=2)

    res = fhir.upload_FHIR(data)

    return res, stats

def findReference(data):
    resourceType = data['resourceType']

    if resourceType == 'Patient':
        return  'Patient'
    else:
        query = FHIR.resourceInfo.query.filter(
            FHIR.resourceInfo.ResourceType == resourceType,
            # FHIR.resourceInfo.Type.like('%Reference(%Patient%'),
            FHIR.resourceInfo.MainPatient == '1'

        )

        resource_info = query.first()
        # if not results:
        #     resource_info = None
        # elif len(results) == 1:
        #     resource_info = results[0]
        # else:
        #     resource_info = next(
        #         (r for r in results if r.MainPatient == 1),
        #         results[0] 
        #     )
        # print(resource_info)
        if resource_info is None:
            return  None
        else:
            # print(resource_info)
            Type = resource_info.Type
            Name = resource_info.Name
            Card = resource_info.Card
            if '*' in Card: # 有*字表示，他是多層
                Name = Name + '[*]'

            # print(Type)

            if 'Reference' in Type:
                PathResult = Name + '.reference'
            elif 'canonical' in Type:
                PathResult = Name
            return PathResult

# 這個是補subject用的，(進來的json, 我的fhir路徑 如subject.reference, 要填進去的值 如Patient/test)
def set_nested_value(data, path, value):
    """
    支援路徑中包含 [*] 的自動填充
    範例：path = 'subject[*].reference'
    """
    parts = path.split('.')
    
    current = data
    for i, key in enumerate(parts):
        # 檢查是否包含 [*]
        if '[*]' in key:
            real_key = key.replace('[*]', '')
            # 確保該鍵值存在且是列表
            if real_key not in current or not isinstance(current[real_key], list):
                current[real_key] = [{}] # 至少建立一個空物件
            
            # 剩餘的路徑遞迴處理
            remaining_path = ".".join(parts[i+1:])
            for item in current[real_key]:
                set_nested_value(item, remaining_path, value)
            return data # 陣列處理完畢，直接返回
            
        # 處理最後一層
        if i == len(parts) - 1:
            current[key] = value
        else:
            # 處理中間層
            current = current.setdefault(key, {})
            
    return data
         
def upload_FHIR_changeID(pat_id, data):
    just_id = pat_id
    pat_id = f"Patient/{pat_id}" # 先拼一下Patient得id格式
    BundleInfo = fhir.FHIRData_Handle(None, data, 1, 0)
    resourceType = BundleInfo[0].resourceType # 用第一層看一下這個resources是不是bundle
    
    if resourceType != 'Bundle':
        PathResult = findReference(data)
        if PathResult == 'Patient':
            print(PathResult)
            data['id'] = just_id
            result = data
        elif PathResult is not None:
            result = set_nested_value(data, PathResult, pat_id)
        else:
            result = data

    elif resourceType == 'Bundle':
        for i, row in enumerate(BundleInfo):
            PathResult = findReference(row.BundleResource)
            if PathResult == 'Patient':
                entry = data["entry"][i]

                # request.url
                req = entry.get("request")
                if isinstance(req, dict) and "url" in req:
                    req["url"] = pat_id

                # resource.id
                res = entry.get("resource")
                if isinstance(res, dict) and "id" in res:
                    res["id"] = just_id

                # fullUrl
                full = entry.get("fullUrl")
                if isinstance(full, str) and "Patient" in full:
                    entry["fullUrl"] = full.split("Patient")[0] + pat_id
            elif PathResult is not None:
                data["entry"][i]["resource"] = set_nested_value(row.BundleResource, PathResult, pat_id)
            
        result = data
    with open("input_result.json", "w", encoding='utf-8') as json_file:
        json.dump(result, json_file)  
    # print(result)
    res = upload_FHIR(result)
    print(res.text)
    return res