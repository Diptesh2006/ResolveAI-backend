# 60–90 second demo

1. In `/docs`, call `GET /appointments/APT-1001` and show Rahul Sharma at 15:00.
2. Set admin fault mode to `TIMEOUT_AFTER_COMMIT`.
3. Tell Isha: “Mujhe meri appointment 5 baje shift karni hai.” Confirm the proposed slot, then execute the reschedule tool with one stable idempotency key.
4. The tool returns a controlled 504. Ask the operation-status tool for the same operation/history; it reports `SUCCEEDED`.
5. Re-read the appointment: it is 17:00. Show `/events` and the single `MUTATION_COMMITTED` plus `ACKNOWLEDGMENT_LOST`.
6. Repeat the identical request: the existing result is returned and no second commit appears.

Do not claim a live Vaani interaction passed until the actual configured Vaani interface has been tested.
