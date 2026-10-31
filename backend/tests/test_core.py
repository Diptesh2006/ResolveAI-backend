import os, tempfile
os.environ["DATABASE_URL"]="sqlite:///./test_resolveai.db"
from fastapi.testclient import TestClient
from app.main import app, settings
from app.database import Base, engine
from app.seed import seed
Base.metadata.drop_all(engine); Base.metadata.create_all(engine); seed()
client=TestClient(app); H={"X-API-Key":settings.api_key}
def test_lookup_and_slots():
    assert client.get('/appointments/APT-1001',headers=H).status_code==200
    assert '15:00' not in client.get('/slots?date=2026-11-02',headers=H).json()['slots']
def test_reschedule_idempotent_and_reconcile():
    settings.fault_mode='TIMEOUT_AFTER_COMMIT'
    r=client.post('/appointments/APT-1001/reschedule',headers=H,json={'new_date':'2026-11-02','new_time':'17:00','idempotency_key':'demo-1','confirmed':True}); assert r.status_code==504
    op=client.get('/appointments/APT-1001/operations',headers=H).json()[0]
    assert op['status']=='SUCCEEDED'
    assert client.post(f"/appointments/APT-1001/reschedule",headers=H,json={'new_date':'2026-11-02','new_time':'17:00','idempotency_key':'demo-1','confirmed':True}).status_code==200
    assert client.get('/appointments/APT-1001',headers=H).json()['time']=='17:00'
    settings.fault_mode='NORMAL'
def test_auth_and_confirmation():
    assert client.get('/appointments/APT-1001').status_code==401
    assert client.post('/appointments',headers=H,json={'customer_name':'X','service_type':'Consultation','date':'2026-11-05','time':'10:00','idempotency_key':'x','confirmed':False}).status_code==400
def test_conflict():
    settings.fault_mode='NORMAL'
    p={'new_date':'2026-11-02','new_time':'16:00','idempotency_key':'conflict','confirmed':True}
    assert client.post('/appointments/APT-1001/reschedule',headers=H,json=p).status_code==200
    p['new_time']='16:30'; assert client.post('/appointments/APT-1001/reschedule',headers=H,json=p).status_code==409
