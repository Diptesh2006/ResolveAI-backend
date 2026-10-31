from .database import Base, engine, SessionLocal
from .models import Appointment
def seed():
    db=SessionLocal()
    if not db.query(Appointment).count():
        db.add_all([Appointment(id="APT-1001",customer_name="Rahul Sharma",customer_reference="DEMO-1001",service_type="Consultation",appointment_date="2026-11-02",appointment_time="15:00"),Appointment(id="APT-1002",customer_name="Priya Mehta",customer_reference="DEMO-1002",service_type="Consultation",appointment_date="2026-11-03",appointment_time="11:00"),Appointment(id="APT-1003",customer_name="Aman Verma",customer_reference="DEMO-1003",service_type="Consultation",appointment_date="2026-11-04",appointment_time="16:00")]); db.commit()
    db.close()
if __name__ == "__main__": Base.metadata.create_all(engine); seed()
