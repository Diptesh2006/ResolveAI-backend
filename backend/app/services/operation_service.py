import hashlib, json, uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Operation, Event
def fingerprint(payload): return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def event(db, typ, message, op=None, apt=None, severity="INFO", metadata=None): db.add(Event(event_type=typ, message=message, operation_id=op, appointment_id=apt, severity=severity, metadata_json=json.dumps(metadata or {})))
def existing_or_conflict(db, key, fp):
    op = db.execute(select(Operation).where(Operation.idempotency_key == key)).scalar_one_or_none()
    if op and op.request_fingerprint != fp: raise ValueError("IDEMPOTENCY_CONFLICT")
    return op
def new_op(db, key, typ, apt, payload, fp):
    op = Operation(operation_id="OP-" + uuid.uuid4().hex[:12].upper(), idempotency_key=key, operation_type=typ, appointment_id=apt, request_fingerprint=fp, requested_payload=json.dumps(payload, sort_keys=True), status="PENDING")
    db.add(op); db.flush(); event(db,"OPERATION_CREATED","Operation created",op.operation_id,apt); return op
