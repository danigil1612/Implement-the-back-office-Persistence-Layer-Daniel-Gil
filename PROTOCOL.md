# TCP protocol

The client and server exchange UTF-8 JSON objects, one per line. Each request
receives exactly one response on the same connection. A connection may carry
multiple requests. Messages are limited to 1,048,576 bytes before the newline.
The server handles one connected client at a time with blocking sockets.

## Requests

Every request has an `operation` and an `entity`. Entity names are `driver`,
`car`, `track`, `race`, `tyre`, `race_result`, and `tyre_usage`.

| Operation | Required fields | Result |
| --- | --- | --- |
| `create` | `entity`, `data` object | Created record |
| `read` | `entity`, `id` | One record |
| `update` | `entity`, `id`, `data` object | Updated record |
| `delete` | `entity`, `id` | `{"deleted": true}` |
| `list` | `entity` | Array of records |

The generated `id` is a positive integer for every entity except `tyre_usage`.
For `tyre_usage`, the identifier is `{"result_id": 1, "period": 1}`.
Its two key fields must be present in `data` when creating a record and cannot
be changed by `update`. Unknown fields and read-only identifiers are rejected.
Dates use `YYYY-MM-DD`. Responses include a read-only `last_update` ISO
timestamp, or `null` when the database has not provided one yet.

### Entity fields

| Entity | Writable fields for creation | Optional fields |
| --- | --- | --- |
| `driver` | `name`, `nationality`, `number` | — |
| `car` | `chassis_code`, `engine_supplier`, `power_hp`, `weight_kg`, `driver_id` | — |
| `track` | `name`, `country`, `length_km` | — |
| `race` | `grand_prix_name`, `date`, `season`, `track_id` | — |
| `tyre` | `compound_name` | `description` |
| `race_result` | `final_position`, `driver_id`, `race_id` | `points` (defaults to 0), `total_time` |
| `tyre_usage` | `result_id`, `period`, `tyre_id`, `lap_count`, `use_number` | — |

Optional nullable fields are `description` and `total_time`. `update` accepts
any nonempty subset of an entity's writable fields. IDs referenced by foreign
keys must exist. Deleting a driver, track, or race follows the existing
database cascade/restrict rules.

### Listing and existing repository queries

Without options, `list` returns all records. A single filter may be passed as
`"filter": {"field": "name", "value": "ham"}`. Supported filters are:

| Entity | Filter fields |
| --- | --- |
| `driver` | `number` (exact), `name` (substring), `nationality` (exact) |
| `car` | `chassis_code` (exact), `engine_supplier` (exact) |
| `track` | `country` (exact), `name` (substring) |
| `race` | `season` (exact), `grand_prix_name` (substring) |
| `tyre` | `compound_name` (exact) |
| `race_result` | `driver_id`, `race_id`, `podium_race_id` (top three by position) |

For `race_result`, `list` also accepts both `page` and `page_size` as positive
integers. Pagination cannot be combined with a filter. Creating a `tyre_usage`
record provides the existing operation for adding a tyre to a race result.

## Responses and errors

Successful response: `{"ok": true, "data": ...}`. For example:

```json
{"ok":true,"data":{"id":1,"name":"Alex","nationality":"ES","number":7,"last_update":"2026-10-28T10:00:00"}}
```

Error response: `{"ok": false, "error": {"code": "...", "message": "..."}}`.

| Code | Meaning |
| --- | --- |
| `invalid_frame` | Missing line ending or closed/incomplete frame |
| `invalid_json` | Malformed JSON or invalid UTF-8 |
| `invalid_message` | JSON is not an object |
| `message_too_large` | Frame exceeds the size limit |
| `invalid_request` | Unsupported operation/entity, missing/extra fields, or invalid values |
| `not_found` | Requested ID does not exist |
| `conflict` | Unique or foreign-key constraint failed |
| `server_error` | Unexpected server failure; details are logged server-side |

Malformed or invalid requests do not modify the database. The server closes
the connection after an oversized or incomplete frame because framing cannot
be recovered reliably. Other errors allow the client to send another request.

## Example

Request: `{"operation":"create","entity":"driver","data":{"name":"Alex","nationality":"ES","number":7}}`

Read request: `{"operation":"read","entity":"driver","id":1}`

List request: `{"operation":"list","entity":"race_result","filter":{"field":"podium_race_id","value":1}}`
