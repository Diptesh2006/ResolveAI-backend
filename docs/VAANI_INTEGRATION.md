# Vaani integration

The backend is ordinary REST and OpenAPI is available at `/openapi.json`. Because Vaani dashboard field names and authentication conventions were not verified in this workspace, map these fields manually in its custom REST tool UI; do not assume Vaani-specific function schema or headers.

Base URL: `https://YOUR-TUNNEL.example` (placeholder). Required header on every customer tool: `X-API-Key: <API_KEY>`.

| Tool | Method/path | Use |
|---|---|---|
| get_appointment | GET `/appointments/{appointment_id}` | After demo customer verification, retrieve authoritative details. |
| check_availability | GET `/slots?date=YYYY-MM-DD&service_type=...` | Before proposing or confirming a slot. |
| create_appointment | POST `/appointments` | Only after explicit confirmation; include customer_name, service_type, date, time, idempotency_key, confirmed=true. |
| reschedule_appointment | POST `/appointments/{appointment_id}/reschedule` | Only after explicit confirmation; include new_date, new_time, stable idempotency_key, confirmed=true. |
| cancel_appointment | POST `/appointments/{appointment_id}/cancel` | Only after explicit confirmation. |
| get_operation_status | GET `/operations/{operation_id}` | After a timeout, never blindly retry. |
| reconcile_operation | POST `/operations/{operation_id}/reconcile` | Verify a durable outcome; UNKNOWN means escalate. |
| create_escalation | POST `/escalations` | Persist unresolved cases with operation_id and reason. |

Example reschedule:

```json
{"new_date":"2026-11-02","new_time":"17:00","idempotency_key":"call-<stable-intent-id>","confirmed":true}
```

Success is `status: SUCCEEDED` with `result_payload`; a lost acknowledgment is a controlled `504` with `ACKNOWLEDGMENT_LOST`, after which the agent calls operation status. `409` means key reuse with a changed payload. `400` means confirmation or slot validation failed. Keep one idempotency key for one confirmed intent and discard an unconfirmed 5 PM intent if the caller changes to 6 PM.

The safest lifecycle is: check availability → obtain explicit confirmation → generate one stable intent key → execute → on transport error query operation status → reconcile → escalate only if UNKNOWN. The backend does not invent a new mutation during recovery.
