# Error handling

All API errors use this body:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Class name is required.",
    "details": {}
  }
}
```

| HTTP | Code | When |
|------|------|------|
| 400 | `VALIDATION_ERROR` | Request body or query fails validation |
| 401 | `UNAUTHENTICATED` | Missing or invalid session |
| 403 | `PERMISSION_DENIED` | Authenticated but not allowed |
| 404 | `NOT_FOUND` | Entity does not exist |
| 409 | `CONFLICT` | Duplicate id or concurrent edit |
| 422 | `BUSINESS_RULE` | Domain rule failed (revoked user, invalid score) |
| 500 | `INTERNAL` | Unexpected failure |

Clients should display `message` and keep `code` for logic.
