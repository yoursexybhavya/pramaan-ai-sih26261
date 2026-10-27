"""FastAPI API and static reviewer dashboard for PRAMAAN-AI."""
from __future__ import annotations

import json
import base64
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import ai, engines, seed, store

app = FastAPI(title="PRAMAAN-AI", version="0.1.0", description="Evidence-linked AICTE application validation MVP")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
STATIC = Path(__file__).parent / "static"
UPLOADS = Path(os.getenv("PRAMAAN_UPLOADS", "/tmp/pramaan-uploads" if os.getenv("VERCEL") else str(Path(__file__).resolve().parents[1] / "uploads")))
UPLOADS.mkdir(parents=True, exist_ok=True)
TOKENS: Dict[str, str] = {}
TOKEN_SECRET = os.getenv("PRAMAAN_SECRET", "pramaan-ai-demo-secret-change-in-production").encode()


def issue_token(username: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"u": username, "exp": int(time.time()) + 86400}, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(TOKEN_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def token_user(token: str) -> Optional[str]:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(TOKEN_SECRET, payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        padded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode())
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        return str(data["u"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None


@app.on_event("startup")
def startup() -> None:
    seed.seed()


def current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Login required")
    token = authorization.split(" ", 1)[1]
    username = token_user(token) or TOKENS.get(token)
    if not username:
        raise HTTPException(401, "Invalid or expired token")
    row = store.one("SELECT username,display_name,role FROM users WHERE username=?", (username,))
    if not row:
        raise HTTPException(401, "Unknown user")
    return dict(row)


def require(*roles: str):
    def dependency(user: Dict[str, str] = Depends(current_user)) -> Dict[str, str]:
        if roles and user["role"] not in roles:
            raise HTTPException(403, "This action requires: " + ", ".join(roles))
        return user
    return dependency


def _decode_report(report: Dict[str, Any]) -> Dict[str, Any]:
    return report


def _application(row: Any) -> Dict[str, Any]:
    app_id = row["id"]
    report = json.loads(row["report_json"])
    documents = []
    for doc in store.rows("SELECT * FROM documents WHERE application_id=? ORDER BY id", (app_id,)):
        item = dict(doc); item["metadata"] = json.loads(item.pop("metadata_json")); documents.append(item)
    flags = []
    for flag in store.rows("SELECT * FROM flags WHERE application_id=? ORDER BY CASE severity WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END, id", (app_id,)):
        item = dict(flag); item["evidence"] = json.loads(item.pop("evidence_json")); flags.append(item)
    claims = []
    for claim in store.rows("SELECT * FROM claims WHERE application_id=? ORDER BY id", (app_id,)):
        item = dict(claim); item["value"] = json.loads(item.pop("value_json")); item["region"] = json.loads(item.pop("region_json")); claims.append(item)
    audits = []
    for a in store.rows("SELECT * FROM audits WHERE application_id=? ORDER BY id", (app_id,)):
        item = dict(a)
        item["detail"] = json.loads(item.pop("detail_json"))
        audits.append(item)
    return {"id": app_id, "institution": row["institution_name"], "institution_name": row["institution_name"], "app_type": row["app_type"],
            "cycle": row["cycle"], "score": row["score"], "band": row["band"], "created_at": row["created_at"],
            "decision": row["decision"], "decision_by": row["decision_by"], "decision_at": row["decision_at"],
            "report": report, "documents": documents, "flags": flags, "claims": claims, "audit": audits}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.post("/api/login")
def login(payload: Dict[str, str]) -> Dict[str, Any]:
    username, password = payload.get("username", ""), payload.get("password", "")
    row = store.one("SELECT username,display_name,role,password_hash FROM users WHERE username=?", (username,))
    import hashlib
    if not row or hashlib.sha256(password.encode()).hexdigest() != row["password_hash"]:
        raise HTTPException(401, "Invalid demo credentials")
    token = issue_token(username); TOKENS[token] = username
    return {"token": token, "user": {"username": row["username"], "display_name": row["display_name"], "role": row["role"]}}


@app.get("/api/me")
def me(user: Dict[str, str] = Depends(current_user)) -> Dict[str, Any]:
    return user


@app.get("/api/ai/status")
def ai_status(user: Dict[str, str] = Depends(current_user)) -> Dict[str, Any]:
    return ai.status()


@app.get("/api/stats")
def stats(user: Dict[str, str] = Depends(current_user)) -> Dict[str, Any]:
    counts = {row["band"]: row["n"] for row in store.rows("SELECT band,COUNT(*) n FROM applications GROUP BY band")}
    open_flags = store.one("SELECT COUNT(*) n FROM flags WHERE status='Open'")["n"]
    return {"total": sum(counts.values()), "green": counts.get("GREEN", 0), "amber": counts.get("AMBER", 0), "red": counts.get("RED", 0), "open_flags": open_flags, "audit": store.verify_audit()}


@app.get("/api/applications")
def applications(triage: Optional[str] = None, user: Dict[str, str] = Depends(current_user)) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM applications"; params: List[Any] = []
    if triage:
        sql += " WHERE band=?"; params.append(triage.upper())
    rows = store.rows(sql, params)
    order = {"RED": 0, "AMBER": 1, "GREEN": 2}
    return [{"id": r["id"], "institution": r["institution_name"], "app_type": r["app_type"], "cycle": r["cycle"], "score": r["score"], "band": r["band"], "decision": r["decision"], "created_at": r["created_at"]} for r in sorted(rows, key=lambda r: (order.get(r["band"], 9), r["score"]))]


@app.get("/api/applications/{application_id}")
def application(application_id: int, user: Dict[str, str] = Depends(current_user)) -> Dict[str, Any]:
    row = store.one("SELECT * FROM applications WHERE id=?", (application_id,))
    if not row: raise HTTPException(404, "Application not found")
    return _application(row)


@app.post("/api/applications")
async def create_application(
    institution_name: str = Form(...), app_type: str = Form("EoA"), cycle: str = Form("2026"),
    files: List[UploadFile] = File(default=[]), user: Dict[str, str] = Depends(require("Evaluator", "Senior Official", "Admin")),
) -> Dict[str, Any]:
    documents: List[Dict[str, Any]] = []
    for upload in files:
        data = await upload.read()
        filename = upload.filename or "upload.bin"
        text = engines._text_from_bytes(data, filename)
        kind = engines._kind(filename, text)
        documents.append({"name": kind, "kind": kind, "filename": filename, "text": text, "bytes": data, "metadata": {"size_bytes": len(data)}})
        safe = f"{secrets.token_hex(6)}_{Path(filename).name}"
        (UPLOADS / safe).write_bytes(data)
        documents[-1]["path"] = str(UPLOADS / safe)
    if not documents:
        raise HTTPException(400, "Upload at least one document")
    report = engines.build_report(documents, {"source_verified": False})
    report["ai_assist"] = {"provider": ai.status(), "suggested_claims": ai.suggest_claims("\n".join(d.get("text", "") for d in documents)), "advisory_only": True}
    with store.connect() as db:
        cur = db.execute("INSERT INTO applications(institution_name,app_type,cycle,score,band,report_json,created_at) VALUES(?,?,?,?,?,?,?)",
                         (institution_name, app_type, cycle, report["score"], report["band"], json.dumps(report), store.utc_now()))
        app_id = cur.lastrowid
        for doc in documents:
            db.execute("INSERT INTO documents(application_id,name,kind,filename,path,metadata_json) VALUES(?,?,?,?,?,?)", (app_id, doc["name"], doc["kind"], doc["filename"], doc.get("path"), json.dumps(doc.get("metadata", {}))))
        for flag in report["flags"]:
            db.execute("INSERT INTO flags(application_id,code,engine,severity,title,message,evidence_json) VALUES(?,?,?,?,?,?,?)", (app_id, flag["code"], flag["engine"], flag["severity"], flag["title"], flag["message"], json.dumps(flag["evidence"])))
        for claim in report["claims"]:
            db.execute("INSERT INTO claims(application_id,key,value_json,confidence,source_document,page,region_json) VALUES(?,?,?,?,?,?,?)", (app_id, claim["key"], json.dumps(claim["value"]), claim["confidence"], claim["source_document"], claim["page"], json.dumps(claim["region"])))
    store.append_audit(user["username"], "APPLICATION_INGESTED", {"filename_count": len(files), "score": report["score"], "band": report["band"]}, app_id)
    return application(app_id, user)


@app.post("/api/applications/{application_id}/rerun")
def rerun(application_id: int, user: Dict[str, str] = Depends(require("Evaluator", "Senior Official", "Admin"))) -> Dict[str, Any]:
    row = store.one("SELECT * FROM applications WHERE id=?", (application_id,))
    if not row: raise HTTPException(404, "Application not found")
    report = json.loads(row["report_json"])
    report["rerun"] = True
    with store.connect() as db:
        db.execute("UPDATE applications SET report_json=? WHERE id=?", (json.dumps(report), application_id))
    store.append_audit(user["username"], "PIPELINE_RERUN", {"engines": list(report.get("engines", {}))}, application_id)
    return application(application_id, user)


@app.post("/api/applications/{application_id}/flags/{flag_id}")
def resolve_flag(application_id: int, flag_id: int, payload: Dict[str, str], user: Dict[str, str] = Depends(require("Evaluator", "Senior Official", "Admin"))) -> Dict[str, Any]:
    status = payload.get("status", "")
    if status not in ("Accepted", "Overridden"):
        raise HTTPException(400, "Status must be Accepted or Overridden")
    if status == "Overridden" and not payload.get("reason", "").strip():
        raise HTTPException(400, "An override reason is mandatory")
    flag = store.one("SELECT * FROM flags WHERE id=? AND application_id=?", (flag_id, application_id))
    if not flag: raise HTTPException(404, "Flag not found")
    with store.connect() as db:
        db.execute("UPDATE flags SET status=?,resolved_by=?,resolved_at=? WHERE id=?", (status, user["username"], store.utc_now(), flag_id))
    store.append_audit(user["username"], "FLAG_" + status.upper(), {"flag_id": flag_id, "reason": payload.get("reason", "")}, application_id)
    return application(application_id, user)


@app.post("/api/applications/{application_id}/decide")
def decide(application_id: int, payload: Dict[str, str], user: Dict[str, str] = Depends(require("Senior Official"))) -> Dict[str, Any]:
    decision = payload.get("decision", "")
    valid_decisions = ("Approve", "Reject", "Return for cure", "Return for Cure", "Refer to Ground EVC Inspection", "Refer to Priority EVC Ground Inspection")
    if decision not in valid_decisions:
        raise HTTPException(400, f"Decision must be one of: {', '.join(valid_decisions)}")
    if decision != "Approve" and not payload.get("reason", "").strip():
        raise HTTPException(400, "A reason is mandatory for this decision")
    if not store.one("SELECT id FROM applications WHERE id=?", (application_id,)): raise HTTPException(404, "Application not found")
    with store.connect() as db:
        db.execute("UPDATE applications SET decision=?,decision_by=?,decision_at=? WHERE id=?", (decision, user["username"], store.utc_now(), application_id))
    store.append_audit(user["username"], "DECISION_RECORDED", {"decision": decision, "reason": payload.get("reason", "")}, application_id)
    return application(application_id, user)


@app.get("/api/rules")
def rules(user: Dict[str, str] = Depends(current_user)) -> List[Dict[str, Any]]:
    return [dict(row) for row in store.rows("SELECT * FROM rules ORDER BY id")]


@app.get("/api/institutions")
def institutions(user: Dict[str, str] = Depends(current_user)) -> List[Dict[str, Any]]:
    return [dict(row) for row in store.rows("SELECT * FROM institutions ORDER BY name")]


@app.get("/api/audit")
def audit(user: Dict[str, str] = Depends(require("Auditor", "Admin", "Senior Official"))) -> List[Dict[str, Any]]:
    output = []
    for row in store.rows("SELECT * FROM audits ORDER BY id DESC LIMIT 200"):
        item = dict(row); item["detail"] = json.loads(item.pop("detail_json")); output.append(item)
    return output


@app.post("/api/audit/verify")
def audit_verify(user: Dict[str, str] = Depends(current_user)) -> Dict[str, Any]:
    result = store.verify_audit(); store.append_audit(user["username"], "AUDIT_VERIFIED", result); return result


app.mount("/static", StaticFiles(directory=STATIC), name="static")
