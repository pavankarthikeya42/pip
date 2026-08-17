import json
import httpx

SYSTEM_PROMPT = '''You are a document validation agent. Compare PDF-derived canonical data with UI-derived canonical data. Never use page number, section position, table row position, or table position as identity. Match by semantic meaning. Different section order, row order, or column order is not automatically a mismatch. Detect PDF sections/fields/table rows missing from UI. Never invent information. If evidence is insufficient return UNCERTAIN. Return JSON only with decision, confidence, reason.'''

class SemanticValidator:
    def __init__(self, base_url="", api_key="", model=""):
        self.base_url=base_url.rstrip("/")
        self.api_key=api_key
        self.model=model
    async def compare(self, pdf_item, ui_item, context=""):
        if not (self.base_url and self.api_key and self.model):
            return {"decision":"UNCERTAIN","confidence":0,"reason":"LLM is not configured"}
        payload={"model":self.model,"messages":[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":json.dumps({"pdf":pdf_item,"ui":ui_item,"context":context})}],"temperature":0}
        headers={"Authorization":f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            r=await client.post(f"{self.base_url}/chat/completions",json=payload,headers=headers)
            r.raise_for_status()
            content=r.json()["choices"][0]["message"]["content"]
            try:return json.loads(content)
            except json.JSONDecodeError:return {"decision":"UNCERTAIN","confidence":0,"reason":content}
