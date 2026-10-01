import json

text = """<a2a_datapart_json>{"kind": "data", "metadata": {"mimeType": "application/json+a2ui"}, "data": {"surfaceUpdate": {}}}</a2a_datapart_json>"""

if text.startswith("<a2a_datapart_json>") and text.endswith("</a2a_datapart_json>"):
    inner = json.loads(text[19:-20])
    print("Inner:", inner)
