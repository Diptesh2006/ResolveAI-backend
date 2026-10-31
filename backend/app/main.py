import asyncio, json, logging, os
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .database import Base, engine, get_db, SessionLocal
from .models import Appointment, Operation, Event, Escalation
from .schemas import BookingRequest, RescheduleRequest, CancelRequest, ReconcileRequest, EscalationRequest
from .security import require_api_key, require_admin
from .services.appointment_service import as_dict, slot_available, validate_slot
from .services.operation_service import fingerprint, existing_or_conflict, new_op, event

logging.basicConfig(level=settings.log_level, format='%(message)s')
app = FastAPI(title="ResolveAI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(engine)

def op_dict(op):
    return {"operation_id":op.operation_id,"operation_type":op.operation_type,"appointment_id":op.appointment_id,"status":op.status,"committed_at":op.committed_at,"result_payload":json.loads(op.result_payload) if op.result_payload else None,"error_code":op.error_code}
def response(op, db, code=200):
    from fastapi.responses import JSONResponse
    return JSONResponse(jsonable_encoder(op_dict(op)), status_code=code)
def mutate(db, typ, apt_id, key, payload, apply):
    fp=fingerprint(payload)
    try: old=existing_or_conflict(db,key,fp)
    except ValueError: raise HTTPException(409,"IDEMPOTENCY_CONFLICT")
    if old: event(db,"DUPLICATE_REQUEST_DETECTED","Duplicate mutation prevented",old.operation_id,apt_id); db.commit(); return old
    op=new_op(db,key,typ,apt_id,payload,fp); db.commit()
    if settings.fault_mode == "FAIL_BEFORE_COMMIT":
        db.refresh(op); op.status="FAILED"; op.error_code="INJECTED_FAILURE"; event(db,"OPERATION_FAILED","Failure before commit",op.operation_id,apt_id,"ERROR"); db.commit(); return op
    try:
        apply(op)
        op.status="SUCCEEDED"; op.committed_at=datetime.now(timezone.utc); event(db,"MUTATION_COMMITTED","Mutation committed",op.operation_id,apt_id,metadata={"commit_count":1}); db.commit()
    except ValueError as e:
        db.rollback(); op=db.get(Operation,op.operation_id); op.status="FAILED"; op.error_code=str(e); event(db,"OPERATION_FAILED",str(e),op.operation_id,apt_id,"WARN"); db.commit()
    return op

@app.get("/health")
def health(db: Session=Depends(get_db)):
    try: db.execute(text("SELECT 1")); connected=True
    except Exception: connected=False
    return {"status":"ok" if connected else "degraded","version":"1.0.0","database_connectivity":connected}

@app.get("/appointments/{appointment_id}", dependencies=[Depends(require_api_key)])
def get_appointment(appointment_id:str, db:Session=Depends(get_db)):
    a=db.get(Appointment,appointment_id)
    if not a: raise HTTPException(404,"Appointment not found")
    event(db,"APPOINTMENT_LOOKUP","Appointment looked up",apt=appointment_id); db.commit(); return as_dict(a)

@app.get("/slots", dependencies=[Depends(require_api_key)])
def slots(date:str, service_type:str|None=None, db:Session=Depends(get_db)):
    out=[]
    for h in range(9,18):
        for m in (0,30):
            t=f"{h:02d}:{m:02d}"
            if slot_available(db,date,t): out.append(t)
    event(db,"AVAILABILITY_CHECK","Availability checked",metadata={"date":date}); db.commit(); return {"date":date,"timezone":settings.demo_timezone,"slots":out}

@app.post("/appointments", dependencies=[Depends(require_api_key)])
def create(req:BookingRequest, db:Session=Depends(get_db)):
    if not req.confirmed: raise HTTPException(400,"CONFIRMATION_REQUIRED")
    try: validate_slot(req.date,req.time)
    except ValueError as e: raise HTTPException(400,str(e))
    payload=req.model_dump()
    def apply(op):
        if not slot_available(db,req.date,req.time): raise ValueError("SLOT_UNAVAILABLE")
        a=Appointment(id="APT-"+os.urandom(4).hex().upper(),customer_name=req.customer_name,customer_reference="DEMO",service_type=req.service_type,appointment_date=req.date,appointment_time=req.time); db.add(a); db.flush(); op.appointment_id=a.id; op.result_payload=json.dumps(as_dict(a))
    op=mutate(db,"CREATE",None,req.idempotency_key,payload,apply); return response(op,db,409 if op.error_code else 200)

@app.post("/appointments/{appointment_id}/reschedule", dependencies=[Depends(require_api_key)])
def reschedule(appointment_id:str, req:RescheduleRequest, db:Session=Depends(get_db)):
    a=db.get(Appointment,appointment_id)
    if not a: raise HTTPException(404,"Appointment not found")
    if not req.confirmed: raise HTTPException(400,"CONFIRMATION_REQUIRED")
    try: validate_slot(req.new_date,req.new_time)
    except ValueError as e: raise HTTPException(400,str(e))
    prior = db.execute(select(Operation).where(Operation.idempotency_key == req.idempotency_key)).scalar_one_or_none()
    def apply(op):
        if a.status != "BOOKED": raise ValueError("APPOINTMENT_NOT_ACTIVE")
        if not slot_available(db,req.new_date,req.new_time,appointment_id): raise ValueError("SLOT_UNAVAILABLE")
        a.appointment_date=req.new_date; a.appointment_time=req.new_time; a.version+=1; a.updated_at=datetime.now(timezone.utc); op.result_payload=json.dumps(as_dict(a))
    op=mutate(db,"RESCHEDULE",appointment_id,req.idempotency_key,req.model_dump(),apply)
    if not prior and settings.fault_mode=="TIMEOUT_AFTER_COMMIT" and op.status=="SUCCEEDED": event(db,"ACKNOWLEDGMENT_LOST","Simulated lost acknowledgment",op.operation_id,appointment_id,"WARN"); db.commit(); raise HTTPException(504,"ACKNOWLEDGMENT_LOST: query operation status")
    return response(op,db,409 if op.error_code=="IDEMPOTENCY_CONFLICT" else 200)

@app.post("/appointments/{appointment_id}/cancel", dependencies=[Depends(require_api_key)])
def cancel(appointment_id:str, req:CancelRequest, db:Session=Depends(get_db)):
    a=db.get(Appointment,appointment_id)
    if not a: raise HTTPException(404,"Appointment not found")
    if not req.confirmed: raise HTTPException(400,"CONFIRMATION_REQUIRED")
    def apply(op):
        if a.status != "BOOKED": raise ValueError("APPOINTMENT_NOT_ACTIVE")
        a.status="CANCELLED"; a.version+=1; op.result_payload=json.dumps(as_dict(a))
    return response(mutate(db,"CANCEL",appointment_id,req.idempotency_key,req.model_dump(),apply),db)

@app.get("/operations/{operation_id}", dependencies=[Depends(require_api_key)])
def operation(operation_id:str, db:Session=Depends(get_db)):
    op=db.get(Operation,operation_id)
    if not op: raise HTTPException(404,"Operation not found")
    event(db,"OPERATION_STATUS_CHECKED","Operation status checked",operation_id,op.appointment_id); db.commit(); return op_dict(op)
@app.get("/appointments/{appointment_id}/operations", dependencies=[Depends(require_api_key)])
def history(appointment_id:str, db:Session=Depends(get_db)): return [op_dict(x) for x in db.execute(select(Operation).where(Operation.appointment_id==appointment_id).order_by(Operation.created_at)).scalars()]
@app.post("/operations/{operation_id}/reconcile", dependencies=[Depends(require_api_key)])
def reconcile(operation_id:str, req:ReconcileRequest, db:Session=Depends(get_db)):
    op=db.get(Operation,operation_id)
    if not op: raise HTTPException(404,"Operation not found")
    if op.status=="SUCCEEDED": final="SUCCEEDED"; verified=True; evidence="Durable operation record and committed result"
    elif op.status=="FAILED": final="FAILED"; verified=True; evidence="Durable failure record"
    else: final="UNKNOWN"; verified=False; evidence="Insufficient authoritative evidence"
    event(db,"RECONCILIATION_SUCCEEDED" if verified else "RECONCILIATION_UNRESOLVED",evidence,operation_id,op.appointment_id); db.commit()
    return {"operation_id":operation_id,"final_status":final,"verified":verified,"evidence":evidence,"recommended_action":"NONE" if verified else "ESCALATE"}
@app.get("/events", dependencies=[Depends(require_api_key)])
def events(appointment_id:str|None=None, operation_id:str|None=None, event_type:str|None=None, db:Session=Depends(get_db)):
    q=select(Event).order_by(Event.timestamp)
    if appointment_id:q=q.where(Event.appointment_id==appointment_id)
    if operation_id:q=q.where(Event.operation_id==operation_id)
    if event_type:q=q.where(Event.event_type==event_type)
    return [{"timestamp":e.timestamp,"operation_id":e.operation_id,"appointment_id":e.appointment_id,"event_type":e.event_type,"severity":e.severity,"message":e.message} for e in db.execute(q).scalars()]
@app.post("/escalations", dependencies=[Depends(require_api_key)])
def escalation(req:EscalationRequest, db:Session=Depends(get_db)):
    e=Escalation(operation_id=req.operation_id,reason=req.reason); db.add(e); db.commit(); return {"id":e.id,"status":"OPEN","operation_id":e.operation_id}

@app.post("/admin/fault-mode", dependencies=[Depends(require_admin)])
def fault_mode(mode:str):
    if mode not in {"NORMAL","FAIL_BEFORE_COMMIT","TIMEOUT_AFTER_COMMIT","SLOW_RESPONSE"}: raise HTTPException(400,"Unsupported fault mode")
    settings.fault_mode=mode; return {"fault_mode":mode}
@app.post("/admin/reset", dependencies=[Depends(require_admin)])
def reset():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); from .seed import seed; seed(); return {"status":"reset"}
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return '<!doctype html><html><head><title>ResolveAI Reliability Console</title><style>body{font:15px system-ui;background:#101827;color:#e5eefb;max-width:1100px;margin:40px auto;padding:0 20px}h1{color:#72e4c1}.card{background:#18243a;padding:18px;border-radius:12px;margin:12px 0}button{padding:8px;background:#72e4c1;border:0;border-radius:6px}table{width:100%;text-align:left}td,th{padding:8px;border-bottom:1px solid #334}</style></head><body><h1>ResolveAI / Reliability Console</h1><div class="card"><h2>Live backend console</h2><p>Use <a href="/docs">OpenAPI</a> with X-API-Key. Dashboard data is intentionally sourced from the same durable API.</p><button onclick="location.reload()">Refresh</button></div><div class="card"><h2>Demo</h2><p>Seeded appointments: APT-1001 (Rahul Sharma, 2026-11-02 15:00), APT-1002, APT-1003.</p><p>Admin fault controls are server-side only; secrets never enter this page.</p></div></body></html>'
