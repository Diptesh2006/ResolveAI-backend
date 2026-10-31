from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Appointment
def slot_available(db: Session, date: str, time: str, exclude: str | None = None):
    q = select(Appointment).where(Appointment.appointment_date == date, Appointment.appointment_time == time, Appointment.status == "BOOKED")
    if exclude: q = q.where(Appointment.id != exclude)
    return db.execute(q).scalars().first() is None
def as_dict(a): return {"appointment_id": a.id, "customer_name": a.customer_name, "service_type": a.service_type, "date": a.appointment_date, "time": a.appointment_time, "status": a.status, "version": a.version}
def validate_slot(date, time):
    d = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    if d.minute not in (0,30) or not 9 <= d.hour < 18: raise ValueError("SLOT_INVALID")
