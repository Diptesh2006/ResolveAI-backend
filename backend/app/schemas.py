from pydantic import BaseModel, Field
class BookingRequest(BaseModel): customer_name: str; service_type: str; date: str; time: str; idempotency_key: str; confirmed: bool = False
class RescheduleRequest(BaseModel): new_date: str; new_time: str; idempotency_key: str; confirmed: bool = False
class CancelRequest(BaseModel): idempotency_key: str; confirmed: bool = False
class ReconcileRequest(BaseModel): expected_date: str | None = None; expected_time: str | None = None
class EscalationRequest(BaseModel): operation_id: str; reason: str = Field(min_length=1, max_length=240)
