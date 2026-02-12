# 占位：請放入你原本的 FHIRClient 實作
class FHIRClient:
    def get_resource(self, rtype, rid):
        return {"resourceType": rtype, "id": rid}
    def search(self, rtype, **kwargs):
        return {"resourceType": "Bundle", "entry": [], "params": kwargs}
