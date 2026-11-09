# Event structure

Every important mutation appends an event. Records are not silently overwritten without history.

```json
{
  "id": "uuid",
  "student_id": "FUTA/SS2A/042",
  "type": "STUDENT_UPSERT",
  "payload": {},
  "teacher_id": "admin_ada",
  "device_id": "school-computer",
  "timestamp": 1726850000000,
  "lamport_clock": 42,
  "signature": "base64_signature",
  "status": "APPLIED"
}
```

`status` values: `PENDING_SYNC`, `APPLIED`, `PENDING_APPROVAL`, `REJECTED`, `CONFLICT`.

The school computer maintains a monotonic Lamport clock. Devices send their clock; the school stores `max(local, remote) + 1`.
