# Virtual Medical Coder — Backend API Reference
**Last updated:** 2026-07-01  
**Base URL:** `http://localhost:8000`  
**Auth:** HttpOnly JWT cookies (`access_token` + `refresh_token`) — set on login, sent automatically by the browser.  
**Interactive Docs:** `http://localhost:8000/swagger/` | `http://localhost:8000/redoc/`

---

## Authentication — `/api/auth/`

All auth endpoints live in the **`accounts`** app ([views.py](file:///d:/FYP/Backend/VirtualMedicalCoder/accounts/views.py)).

| Method | URL | Auth Required | Description |
|--------|-----|:---:|-------------|
| `POST` | `/api/auth/register/` | ❌ | Register a new coder account |
| `POST` | `/api/auth/login/` | ❌ | Log in — sets `access_token` + `refresh_token` cookies |
| `POST` | `/api/auth/logout/` | ✅ | Log out — clears both auth cookies |
| `POST` | `/api/auth/refresh/` | ❌ | Refresh access token using the refresh cookie |
| `GET`  | `/api/auth/me/` | ✅ | Get the logged-in user's profile *(use this for the profile page)* |
| `PATCH` | `/api/auth/me/` | ✅ | Update profile fields and/or change password |

---

### `POST /api/auth/register/`
Register a new user account. Role defaults to `"coder"`.

**Request Body**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
```

**Response `201`**
```json
{
  "message": "User registered successfully",
  "user": { "id": 1, "username": "john_doe", "email": "john@example.com", "role": "coder" }
}
```

---

### `POST /api/auth/login/`
Authenticate and receive HttpOnly JWT cookies.

**Request Body**
```json
{ "username": "john_doe", "password": "SecurePass123!" }
```

**Response `200`** — cookies are set in the browser automatically
```json
{
  "message": "Login successful.",
  "user": {
    "id": 1, "username": "john_doe", "email": "john@example.com",
    "first_name": "", "last_name": "", "is_staff": false, "role": "coder"
  }
}
```

---

### `POST /api/auth/logout/`
Clears both auth cookies. Requires the `access_token` cookie.

**Response `200`**
```json
{ "message": "Logged out successfully." }
```

---

### `POST /api/auth/refresh/`
Reads the `refresh_token` cookie and issues a new `access_token` cookie.

**Response `200`**
```json
{ "message": "Token refreshed successfully." }
```

---

### `GET /api/auth/me/`
Returns the currently authenticated user's profile.  
**Frontend use:** Profile page display — call this on mount to populate user info.

**Response `200`**
```json
{
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_staff": false,
    "role": "coder"
  }
}
```

---

### `PATCH /api/auth/me/`
Partially update the logged-in user's profile. **All fields are optional** — only send what you want to change.

**Request Body** (all fields optional)
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "newemail@example.com",

  // To change password — all three must be sent together:
  "current_password": "OldPass123!",
  "new_password": "NewPass456!",
  "confirm_new_password": "NewPass456!"
}
```

**Response `200`**
```json
{
  "message": "Profile updated successfully.",
  "user": { "id": 1, "username": "john_doe", "email": "newemail@example.com", ... }
}
```

**Errors `400`** — email already in use, wrong current password, passwords don't match, weak password.

---

## Ingestion — `/api/ingestion/`

Handles clinical document submission and processing status. Lives in the **`ingestion`** app ([views.py](file:///d:/FYP/Backend/VirtualMedicalCoder/ingestion/views.py)).

| Method | URL | Auth Required | Description |
|--------|-----|:---:|-------------|
| `POST` | `/api/ingestion/upload/` | ✅ | Submit a file URL or raw text for AI processing |
| `GET` | `/api/ingestion/upload/<record_id>/` | ✅ | Poll the processing status of an upload |

---

### `POST /api/ingestion/upload/`
The frontend uploads files directly to cloud storage (Cloudinary/S3), then sends the resulting URL here.  
Queues a Celery background job for OCR / STT / PDF parsing + NLP coding.

> [!IMPORTANT]
> Returns `202 Accepted` immediately. Poll `GET /api/ingestion/upload/<id>/` for completion.

**Request Body — File upload**
```json
{
  "file_url": "https://res.cloudinary.com/.../patient_notes.pdf",
  "file_type": "pdf",
  "file_name": "patient_notes.pdf"
}
```

**Request Body — Direct text input**
```json
{
  "file_type": "raw_text",
  "raw_text": "Patient presents with chest pain and shortness of breath...",
  "file_name": "Direct text input"
}
```

**`file_type` values:** `"pdf"` | `"image"` | `"audio"` | `"raw_text"`

**Response `202`**
```json
{
  "id": 42,
  "file_type": "pdf",
  "file_name": "patient_notes.pdf",
  "status": "pending",
  "created_at": "2026-07-01T10:00:00Z"
}
```

---

### `GET /api/ingestion/upload/<record_id>/`
Poll for the processing status of a submitted upload.

**`status` values:**
| Value | Meaning |
|-------|---------|
| `pending` | Received, queued |
| `processing` | OCR / STT / NLP running |
| `completed` | Text extracted, codes generated — coding result is ready |
| `failed` | Something went wrong |

**Response `200`**
```json
{
  "id": 42,
  "file_type": "pdf",
  "file_name": "patient_notes.pdf",
  "status": "completed",
  "error_message": "",
  "created_at": "2026-07-01T10:00:00Z",
  "updated_at": "2026-07-01T10:00:45Z"
}
```

---

## Coding — `/api/coding/`

The core review workflow. Lives in the **`coding`** app ([views.py](file:///d:/FYP/Backend/VirtualMedicalCoder/coding/views.py)).

| Method | URL | Auth Required | Description |
|--------|-----|:---:|-------------|
| `GET` | `/api/coding/` | ✅ | List all coding results for the current user |
| `GET` | `/api/coding/stats/` | ✅ | Dashboard statistics (counts by status + avg confidence) |
| `GET` | `/api/coding/<result_id>/` | ✅ | Get one coding result in full detail |
| `POST` | `/api/coding/<result_id>/review/` | ✅ | Approve, reject, or revise AI-generated codes |
| `POST` | `/api/coding/<result_id>/add-code/` | ✅ | Manually add a single ICD/CPT code |
| `DELETE` | `/api/coding/<result_id>/code/` | ✅ | Delete a single code from a result |
| `POST` | `/api/coding/<result_id>/alternatives/` | ✅ | Get alternative code suggestions from evidence text |
| `GET` | `/api/coding/<result_id>/feedback/` | ✅ | View review feedback / correction history |

---

### `GET /api/coding/`
Returns all coding results belonging to the logged-in user, newest first.

**Response `200`** — array of coding result objects (see Coding Result Object below)

---

### `GET /api/coding/stats/`
Dashboard summary. Single DB query returning aggregate counts.  
**Frontend use:** Power a stats widget / dashboard overview.

**Response `200`**
```json
{
  "total": 12,
  "pending": 4,
  "approved": 6,
  "rejected": 1,
  "revised": 1,
  "avg_confidence": 0.8742
}
```

---

### `GET /api/coding/<result_id>/`
Full detail for one coding result (must belong to the authenticated user).

**Response `200`** — full Coding Result Object (see below)

---

### Coding Result Object
```json
{
  "id": 7,
  "upload_record_id": 42,
  "file_url": "https://...",
  "file_type": "pdf",
  "file_name": "patient_notes.pdf",
  "upload_status": "completed",

  "soap_note": {
    "subjective": "Patient reports chest pain...",
    "objective": "BP 140/90, HR 88...",
    "assessment": "Type 2 Diabetes, Hypertension",
    "plan": "Metformin 500mg, follow-up in 2 weeks"
  },

  "extracted_evidence": { "diagnoses": [...], "procedures": [...], "symptoms": [...] },
  "extracted_diagnoses": [...],

  "icd_codes": [
    { "code": "E11.9", "description": "Type 2 diabetes mellitus without complications",
      "confidence": 0.95, "evidence_text": "...", "flagged": false }
  ],
  "cpt_codes": [
    { "code": "99213", "description": "Office visit, established patient, 20-29 min",
      "confidence": 0.88, "evidence_text": "...", "flagged": false }
  ],

  "summary": "Patient with T2DM and hypertension...",
  "confidence": 0.91,
  "validation_metadata": { "total_codes": 2, "flagged_count": 0, "needs_review": false },
  "validation_log": {},

  "review_status": "pending",
  "review_notes": "",
  "reviewed_by_username": null,
  "reviewed_at": null,

  "created_at": "2026-07-01T10:00:45Z",
  "updated_at": "2026-07-01T10:01:00Z"
}
```

---

### `POST /api/coding/<result_id>/review/`
The human review step — approve, reject, or revise AI-generated codes.

**`review_status` values:** `"approved"` | `"rejected"` | `"revised"`

**Request Body**
```json
{
  "review_status": "revised",

  // Optional — only needed if changing codes
  "icd_codes": [{ "code": "E11.65", "description": "T2DM with hyperglycemia", "confidence": 1.0 }],
  "cpt_codes": [...],
  "summary": "Updated clinical summary...",
  "review_notes": "Changed to more specific ICD code for hyperglycemia.",

  // Required when codes are corrected — for audit/learning
  "feedback_type": "incorrect_code",
  "explanation": "Original code lacked specificity for hyperglycemia."
}
```

**`feedback_type` values:**
| Value | Meaning |
|-------|---------|
| `missing_code` | AI missed a code, reviewer added it |
| `incorrect_code` | Code was wrong, reviewer corrected it |
| `specificity` | Reviewer chose a more specific code |
| `completeness` | Reviewer enhanced overall completeness |
| `conflict_resolved` | Conflicting code removed |
| `source_misidentified` | Source not physician confirmed |
| `unverified_condition_coded` | Patient-statement-only condition coded |
| `historical_incorrectly_coded` | Historical condition coded as current |
| `physician_confirmed_not_coded` | Confirmed diagnosis was missed |
| `patient_reported_coded` | ICD-10-CM violation — patient-only statement |
| `other` | Other reason |

**Response `200`** — updated full Coding Result Object

---

### `POST /api/coding/<result_id>/add-code/`
Explicitly add a **single new code** to a result. Used when the coder wants to add a specific code after rejection or AI miss, without touching the other existing codes.

> [!NOTE]
> Automatically creates a `ReviewFeedback` audit record (type: `missing_code`).
> Duplicate codes (same code value) are rejected with `400`.

**Request Body**
```json
{
  "type": "icd",
  "code": "I10",
  "description": "Essential (primary) hypertension",
  "evidence_text": "Patient has documented hypertension on medication"
}
```

| Field | Required | Values |
|-------|:---:|--------|
| `type` | ✅ | `"icd"` or `"cpt"` |
| `code` | ✅ | The code string, e.g. `"E11.9"` |
| `description` | ✅ | Human-readable label |
| `evidence_text` | ❌ | Clinical evidence supporting the code |

**Response `200`**
```json
{
  "message": "ICD code 'I10' added successfully.",
  "result": { ... }
}
```

---

### `DELETE /api/coding/<result_id>/code/`
Remove a single code from a result's ICD or CPT list.

**Request Body**
```json
{ "code": "E11.9", "type": "icd" }
```

**Response `200`** — updated Coding Result Object

---

### `POST /api/coding/<result_id>/alternatives/`
Get ranked alternative code suggestions for a diagnosis or procedure. Useful in the review UI to help coders pick a replacement code.

**Request Body**
```json
{
  "system": "ICD10",
  "evidence_text": "Type 2 diabetes with chronic kidney disease stage 3"
}
```

**`system` values:** `"ICD10"` | `"CPT"`

**Response `200`**
```json
{
  "candidates": [
    { "code": "E11.22", "description": "T2DM with diabetic CKD", "score": 0.93 },
    { "code": "E11.65", "description": "T2DM with hyperglycemia", "score": 0.81 },
    ...
  ]
}
```

---

### `GET /api/coding/<result_id>/feedback/`
Full correction history for a coding result. Useful for audit trail and continuous improvement tracking.

**Response `200`**
```json
[
  {
    "id": 3,
    "reviewer_username": "john_doe",
    "llm_codes": [{ "code": "E11.9", ... }],
    "corrected_codes": [{ "code": "E11.22", ... }],
    "feedback_type": "specificity",
    "explanation": "Used more specific CKD-linked code.",
    "created_at": "2026-07-01T10:15:00Z"
  }
]
```

---

## Reports — `/api/reports/`

Read-only reporting for approved/revised results. Lives in the **`reports`** app ([views.py](file:///d:/FYP/Backend/VirtualMedicalCoder/reports/views.py)).

| Method | URL | Auth Required | Description |
|--------|-----|:---:|-------------|
| `GET` | `/api/reports/` | ✅ | List all verified reports (approved or revised) |
| `GET` | `/api/reports/<result_id>/` | ✅ | Full report for one coding result |

> [!NOTE]
> Only `approved` and `revised` results appear in reports. Pending and rejected results are excluded.

---

### `GET /api/reports/`
Lists all finalized reports for the logged-in user.

**Response `200`** — array of report summary objects

---

### `GET /api/reports/<result_id>/`
Full report for a single coding result, including extracted text, SOAP note, all codes, and summary.  
**Frontend use:** Render the final report page / export to PDF.

**Response `200`** — full report payload

---

## NLP Engine — `/api/nlp/`

Direct NLP analysis without persistence. Lives in the **`nlp_engine`** app ([views.py](file:///d:/FYP/Backend/VirtualMedicalCoder/nlp_engine/views.py)).

| Method | URL | Auth Required | Description |
|--------|-----|:---:|-------------|
| `POST` | `/api/nlp/analyze/` | ❌ | Run NLP pipeline on raw text, no DB save |

---

### `POST /api/nlp/analyze/`
Runs the full two-stage NLP pipeline (SOAP extraction → ICD/CPT coding) on raw text and returns the result immediately. **Does not save anything to the database.**

> [!TIP]
> Use `/api/ingestion/upload/` with `raw_text` type instead for production flows — that saves results to the DB and creates a coding result for review.

**Request Body**
```json
{
  "raw_text": "Patient presents with fatigue and polyuria...",
  "model": "gemini-pro"
}
```

**Response `200`** — full NLP pipeline output (SOAP + codes + evidence)

---

## Error Response Format

All error responses follow this shape:

```json
{ "error": "Human-readable message." }
```
or for validation errors:
```json
{
  "field_name": ["Error message about this field."],
  "non_field_errors": ["Cross-field validation error."]
}
```

## Standard HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | OK |
| `201` | Created |
| `202` | Accepted (async processing queued) |
| `400` | Bad Request — validation error |
| `401` | Unauthorized — missing or invalid JWT |
| `404` | Not Found |
| `502` | NLP processing failed upstream |
| `503` | Celery task queue unavailable |

---

## Data Models Overview

```
User (accounts)
 └── UploadRecord (ingestion) — one per file/text submission
      └── CodingResult (coding) — one per UploadRecord (1:1)
           └── ReviewFeedback (coding) — many per CodingResult
```

---

## Frontend Integration Quick Reference

| Page | API to call |
|------|-------------|
| **Profile page (display)** | `GET /api/auth/me/` |
| **Profile page (edit)** | `PATCH /api/auth/me/` |
| **Dashboard stats widget** | `GET /api/coding/stats/` |
| **Upload a document** | `POST /api/ingestion/upload/` → poll `GET /api/ingestion/upload/<id>/` |
| **List all coding results** | `GET /api/coding/` |
| **Review a coding result** | `GET /api/coding/<id>/` → `POST /api/coding/<id>/review/` |
| **Manually add a missed code** | `POST /api/coding/<id>/add-code/` |
| **Delete a wrong code** | `DELETE /api/coding/<id>/code/` |
| **Find alternative codes** | `POST /api/coding/<id>/alternatives/` |
| **View correction history** | `GET /api/coding/<id>/feedback/` |
| **Final report page** | `GET /api/reports/<id>/` |
| **Reports list** | `GET /api/reports/` |
