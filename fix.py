import json

def rewrite():
    with open("frontend/main.py", "r") as f:
        lines = f.read().splitlines()
    
    start = -1
    end = -1
    for i, l in enumerate(lines):
        if l.startswith("def _extract_parts"):
            start = i
        if start != -1 and l.startswith("@app.post(\"/chat\")"):
            end = i
            break
            
    new_func = """def _extract_parts(parts) -> list[dict]:
    out: list[dict] = []
    for p in parts:
        if p.HasField("text") and p.text:
            out.append({"kind": "text", "text": p.text})
        elif p.HasField("data"):
            from google.protobuf.json_format import MessageToDict
            struct_dict = MessageToDict(p.data)
            mime = struct_dict.get("metadata", {}).get("mimeType")
            if mime == "application/json+a2ui" and "data" in struct_dict:
                out.append({"kind": "a2ui", "data": struct_dict["data"]})
            elif mime == "application/json+a2ui":
                out.append({"kind": "a2ui", "data": struct_dict})
            elif mime == "text/plain" and "data" in struct_dict:
                text = struct_dict["data"]
                if isinstance(text, str):
                    if text.startswith("<a2a_datapart_json>") and text.endswith("</a2a_datapart_json>"):
                        import json
                        inner = json.loads(text[19:-20])
                        if inner.get("kind") == "data" and "data" in inner:
                            out.append({"kind": "a2ui", "data": inner["data"]})
                    else:
                        out.append({"kind": "text", "text": text})
        elif p.HasField("url"):
            if p.url:
                out.append({"kind": "text", "text": p.url})
    return out

"""
    lines = lines[:start] + new_func.splitlines() + lines[end:]
    with open("frontend/main.py", "w") as f:
        f.write("\n".join(lines) + "\n")

rewrite()
