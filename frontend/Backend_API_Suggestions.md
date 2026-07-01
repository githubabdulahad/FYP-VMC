# Backend API Enhancement Suggestions for VMC

## Overview
This document outlines additional APIs that should be implemented to make VMC a complete, production-ready medical coding platform.

---

## Priority 1: Essential Features (MVP++)

### 1.1 User Management & Profile

#### GET `/api/auth/profile/`
**Purpose:** Get current user's full profile
```json
{
  "id": 1,
  "username": "john_coder",
  "email": "john@hospital.com",
  "full_name": "John Smith",
  "department": "Coding",
  "created_at": "2026-01-15",
  "total_documents_coded": 150,
  "total_approved": 140,
  "total_rejected": 10
}
```

#### PUT `/api/auth/profile/`
**Purpose:** Update user profile
```json
{
  "full_name": "John Smith",
  "department": "Coding"
}
```

#### POST `/api/auth/change-password/`
**Purpose:** Change password
```json
{
  "old_password": "current_password",
  "new_password": "new_secure_password"
}
```

---

### 1.2 Search & Filtering

#### GET `/api/coding/?search=diabetes&status=pending&file_type=pdf`
**Purpose:** Search documents by name, status, type, date range
```json
{
  "count": 5,
  "results": [
    {
      "id": 120,
      "file_name": "diabetes_patient_notes.pdf",
      "file_type": "pdf",
      "review_status": "pending",
      "created_at": "2026-06-24"
    }
  ]
}
```

#### GET `/api/coding/?date_from=2026-06-01&date_to=2026-06-30`
**Purpose:** Filter by date range

#### GET `/api/coding/?assigned_to=john_coder`
**Purpose:** Get documents assigned to specific coder

---

### 1.3 Bulk Operations

#### POST `/api/coding/bulk-approve/`
**Purpose:** Approve multiple documents at once
```json
{
  "document_ids": [120, 121, 122],
  "review_notes": "Batch approved - all correct"
}
```

Response:
```json
{
  "success": true,
  "count": 3,
  "message": "3 documents approved"
}
```

#### POST `/api/coding/bulk-reject/`
**Purpose:** Reject multiple documents
```json
{
  "document_ids": [115, 116],
  "rejection_reason": "Insufficient clinical evidence"
}
```

#### DELETE `/api/coding/bulk-delete/`
**Purpose:** Delete multiple documents
```json
{
  "document_ids": [110, 111, 112]
}
```

---

### 1.4 Statistics & Analytics

#### GET `/api/stats/dashboard/`
**Purpose:** Get personal coding statistics
```json
{
  "total_documents": 150,
  "pending_review": 5,
  "approved": 140,
  "rejected": 5,
  "average_codes_per_document": 8.5,
  "approval_rate": 0.93,
  "documents_this_week": 12,
  "documents_this_month": 45
}
```

#### GET `/api/stats/coding-trends/`
**Purpose:** Get coding statistics over time
```json
{
  "week": [
    {"date": "2026-06-18", "total": 10, "approved": 9, "rejected": 1},
    {"date": "2026-06-19", "total": 12, "approved": 11, "rejected": 1},
    {"date": "2026-06-20", "total": 8, "approved": 8, "rejected": 0}
  ],
  "month": [
    {"month": "June", "total": 150, "approved": 140, "rejected": 10}
  ]
}
```

#### GET `/api/stats/code-distribution/`
**Purpose:** Get which codes are most frequently used
```json
{
  "top_icd_codes": [
    {"code": "E11.9", "count": 45, "frequency": "35%"},
    {"code": "I10", "count": 38, "frequency": "29%"},
    {"code": "J45.901", "count": 22, "frequency": "17%"}
  ],
  "top_cpt_codes": [
    {"code": "99213", "count": 50, "frequency": "38%"},
    {"code": "99214", "count": 35, "frequency": "27%"}
  ]
}
```

#### GET `/api/stats/coder-performance/`
**Purpose:** Admin view - compare coders
```json
{
  "coders": [
    {
      "username": "john_coder",
      "documents_coded": 150,
      "approval_rate": 0.93,
      "average_time_to_approve": "15 minutes",
      "error_rate": 0.07
    }
  ]
}
```

---

### 1.5 Code Management

#### POST `/api/codes/favorites/`
**Purpose:** Save frequently used codes
```json
{
  "code": "E11.9",
  "system": "ICD10",
  "note": "Type 2 diabetes without complications"
}
```

#### GET `/api/codes/favorites/`
**Purpose:** Get user's favorite codes (for quick access)

#### DELETE `/api/codes/favorites/{code}/`
**Purpose:** Remove from favorites

#### GET `/api/codes/search/?q=diabetes&system=ICD10`
**Purpose:** Search code database directly
```json
{
  "results": [
    {
      "code": "E11.9",
      "description": "Type 2 diabetes mellitus without complications",
      "category": "Endocrine diseases"
    }
  ]
}
```

---

### 1.6 Review History & Audit Trail

#### GET `/api/coding/{id}/history/`
**Purpose:** See all changes made to a document
```json
{
  "changes": [
    {
      "timestamp": "2026-06-24T10:30:00",
      "action": "approved",
      "reviewer": "john_coder",
      "codes_added": [],
      "codes_removed": [],
      "notes": ""
    },
    {
      "timestamp": "2026-06-24T10:20:00",
      "action": "code_deleted",
      "reviewer": "john_coder",
      "code_deleted": "J45.901",
      "reason": "Incorrect suggestion"
    }
  ]
}
```

#### GET `/api/audit-logs/?user=john_coder&days=30`
**Purpose:** Admin - see all user actions in date range

---

## Priority 2: Advanced Features (Phase 2)

### 2.1 Code Suggestions Improvement

#### POST `/api/coding/{id}/code-feedback/`
**Purpose:** Tell AI if suggestion was good or bad (for ML training)
```json
{
  "code": "E11.9",
  "feedback_type": "incorrect",
  "correct_code": "E11.65",
  "reason": "Patient had diabetic foot ulcer complications"
}
```

#### GET `/api/coding/{id}/explanation/{code}/`
**Purpose:** Get detailed explanation why AI suggested this code
```json
{
  "code": "E11.9",
  "score": 0.85,
  "supporting_evidence": [
    "Patient has history of type 2 diabetes",
    "No complications mentioned in notes"
  ],
  "similar_codes": [
    {"code": "E11.65", "reason": "If diabetic foot ulcer mentioned"}
  ]
}
```

---

### 2.2 Document Assignment & Workflow

#### POST `/api/coding/{id}/assign/`
**Purpose:** Assign document to specific coder
```json
{
  "assigned_to": "jane_coder",
  "priority": "high",
  "due_date": "2026-06-26"
}
```

#### GET `/api/assignments/?assigned_to=me`
**Purpose:** Get documents assigned to current user

#### POST `/api/assignments/{id}/claim/`
**Purpose:** Coder claims a document (marks as in progress)

#### POST `/api/assignments/{id}/unclaim/`
**Purpose:** Coder returns a document (someone else reviews it)

---

### 2.3 Code Corrections & Mapping

#### POST `/api/coding/{id}/code-corrections/`
**Purpose:** Request code correction from another coder
```json
{
  "code": "J45.901",
  "suggested_correction": "J45.902",
  "reason": "Based on updated clinical evidence",
  "assigned_to": "jane_coder"
}
```

#### POST `/api/codes/map/`
**Purpose:** Map codes between versions (ICD-9 to ICD-10)
```json
{
  "source_code": "786.5",
  "source_system": "ICD9",
  "target_system": "ICD10"
}
```

Response:
```json
{
  "mappings": [
    {
      "target_code": "R01.1",
      "confidence": 0.95,
      "clinical_notes": "Abnormal breath sounds"
    }
  ]
}
```

---

### 2.4 Export & Reports

#### GET `/api/reports/export/?format=csv&date_from=2026-06-01&date_to=2026-06-30`
**Purpose:** Export coding results to CSV
- Document name, codes, status, approval date, coder name

#### GET `/api/reports/export/?format=excel&status=approved`
**Purpose:** Export to Excel with formatting

#### POST `/api/reports/generate-custom/`
**Purpose:** Generate custom report
```json
{
  "title": "June 2026 Coding Summary",
  "date_range": {
    "from": "2026-06-01",
    "to": "2026-06-30"
  },
  "filters": {
    "status": "approved",
    "coder": "john_coder"
  },
  "include": ["stats", "trends", "top_codes"]
}
```

---

## Priority 3: Enterprise Features (Phase 3)

### 3.1 Role-Based Access Control (RBAC)

#### POST `/api/users/create/` (Admin only)
**Purpose:** Create new user with role
```json
{
  "username": "new_coder",
  "email": "coder@hospital.com",
  "password": "secure_password",
  "role": "coder",
  "department": "Coding"
}
```

#### GET `/api/users/` (Admin only)
**Purpose:** List all users

#### PUT `/api/users/{id}/` (Admin only)
**Purpose:** Update user details, role, permissions

#### DELETE `/api/users/{id}/` (Admin only)
**Purpose:** Deactivate user

**Roles:**
- `admin` - Full system access
- `reviewer` - Can approve/reject codes
- `coder` - Can code documents
- `viewer` - Read-only access

---

### 3.2 Notifications

#### GET `/api/notifications/`
**Purpose:** Get user's notifications
```json
{
  "count": 3,
  "notifications": [
    {
      "id": 1,
      "type": "document_assigned",
      "message": "New document assigned to you: patient_xyz.pdf",
      "created_at": "2026-06-24T10:30:00",
      "read": false
    }
  ]
}
```

#### POST `/api/notifications/{id}/mark-read/`
**Purpose:** Mark notification as read

#### POST `/api/notifications/settings/`
**Purpose:** Configure notification preferences
```json
{
  "email_on_new_assignment": true,
  "email_on_approval": false,
  "email_daily_summary": true
}
```

---

### 3.3 Integration APIs

#### POST `/api/integrations/ehr-submit/`
**Purpose:** Submit approved codes to external EHR system
```json
{
  "document_id": 120,
  "ehr_system": "epic",
  "patient_mrn": "MRN-12345",
  "appointment_id": "APT-67890"
}
```

#### GET `/api/integrations/ehr-status/{document_id}/`
**Purpose:** Check if codes were successfully sent to EHR

#### POST `/api/integrations/webhook/subscribe/`
**Purpose:** Register webhook for document completion
```json
{
  "url": "https://hospital-ehr.com/api/coding-complete",
  "events": ["document_approved", "document_rejected"]
}
```

---

### 3.4 Machine Learning Feedback

#### POST `/api/ml/feedback/batch/`
**Purpose:** Submit batch feedback for model improvement
```json
{
  "corrections": [
    {
      "document_id": 120,
      "code": "E11.9",
      "feedback": "incorrect",
      "correct_code": "E11.65"
    }
  ]
}
```

#### GET `/api/ml/model-version/`
**Purpose:** Get current ML model version and accuracy metrics

#### POST `/api/ml/retrain/` (Admin only)
**Purpose:** Trigger model retraining with new feedback

---

## Priority 4: Optimization & Performance

### 4.1 Caching & Performance

#### GET `/api/codes/icd10-cache/`
**Purpose:** Get entire ICD-10 code database (cached)
- Use for offline availability
- Significantly faster than real-time search

#### GET `/api/codes/cpt-cache/`
**Purpose:** Get entire CPT code database (cached)

---

### 4.2 Batch Processing

#### POST `/api/batch/upload/`
**Purpose:** Upload multiple documents at once
```json
{
  "files": [
    {"file_url": "url1", "file_name": "patient1.pdf"},
    {"file_url": "url2", "file_name": "patient2.pdf"}
  ]
}
```

Response:
```json
{
  "batch_id": "BATCH-001",
  "status": "processing",
  "count": 2
}
```

#### GET `/api/batch/{batch_id}/status/`
**Purpose:** Check batch processing progress

#### GET `/api/batch/{batch_id}/results/`
**Purpose:** Get all results from completed batch

---

## Implementation Roadmap

### Phase 1 (Current - MVP Complete)
- ✅ Authentication
- ✅ Upload & Processing
- ✅ Review & Approval
- ✅ PDF Download

### Phase 2 (Weeks 3-6)
- User profile management
- Search & filtering
- Bulk operations
- Statistics & analytics
- Code management (favorites)
- Audit trail
- Code feedback system

### Phase 3 (Weeks 7-12)
- Role-based access control
- Document assignment workflow
- Notifications
- Export/Reports
- Code mapping & corrections
- EHR integration webhooks

### Phase 4 (Months 4-6)
- ML model improvement feedback
- Real-time collaboration
- Advanced analytics dashboard
- Batch processing
- Mobile API (if mobile app planned)

---

## API Best Practices to Follow

### 1. Pagination for Large Results
```
GET /api/coding/?page=1&page_size=20
```

### 2. Filtering Standards
```
GET /api/coding/?status=pending&created_after=2026-06-01
```

### 3. Sorting
```
GET /api/coding/?ordering=-created_at&ordering=status
```

### 4. Partial Responses (if needed)
```
GET /api/coding/?fields=id,file_name,status
```

### 5. Rate Limiting Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1234567890
```

### 6. Error Response Format
```json
{
  "error": "invalid_request",
  "message": "Document not found",
  "status_code": 404,
  "timestamp": "2026-06-24T10:30:00Z"
}
```

### 7. Consistent Response Format
```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150
  }
}
```

---

## Database Schema Additions

### Code Favorites Table
```sql
CREATE TABLE code_favorites (
  id INT PRIMARY KEY,
  user_id INT,
  code VARCHAR(20),
  system VARCHAR(10),  -- "ICD10" or "CPT"
  created_at TIMESTAMP
);
```

### Audit Log Table
```sql
CREATE TABLE audit_logs (
  id INT PRIMARY KEY,
  user_id INT,
  action VARCHAR(50),
  document_id INT,
  changes JSON,
  created_at TIMESTAMP
);
```

### User Statistics Table
```sql
CREATE TABLE user_statistics (
  id INT PRIMARY KEY,
  user_id INT,
  total_documents INT,
  approved INT,
  rejected INT,
  average_time_minutes DECIMAL,
  last_updated TIMESTAMP
);
```

### Code Feedback Table
```sql
CREATE TABLE code_feedback (
  id INT PRIMARY KEY,
  document_id INT,
  suggested_code VARCHAR(20),
  feedback_type VARCHAR(20),  -- "correct" or "incorrect"
  correct_code VARCHAR(20),
  reason TEXT,
  created_at TIMESTAMP
);
```

---

## Security Considerations

### For All New Endpoints:
1. ✅ Check `IsAuthenticated` permission
2. ✅ Check role-based permissions (admin only endpoints)
3. ✅ Verify user owns the document (if personal data)
4. ✅ Rate limiting to prevent abuse
5. ✅ Input validation & sanitization
6. ✅ Log all sensitive operations

### Admin-Only Endpoints Must:
- Require admin role
- Log all actions
- Include audit trail
- Support soft deletes (don't permanently delete users)

---

## Estimated Implementation Time

| Feature | Time | Difficulty |
|---------|------|-----------|
| User Profile APIs | 2-3 hours | Easy |
| Search & Filtering | 3-4 hours | Easy |
| Bulk Operations | 2-3 hours | Easy |
| Statistics APIs | 4-6 hours | Medium |
| Audit Trail | 3-4 hours | Medium |
| RBAC | 8-10 hours | Hard |
| Notifications | 6-8 hours | Medium |
| Export/Reports | 4-6 hours | Medium |
| EHR Integration | 10-15 hours | Hard |
| ML Feedback | 6-8 hours | Medium |

**Total: ~50-70 hours of backend development**

---

## Conclusion

These APIs transform VMC from a working prototype to an enterprise-grade medical coding platform. Implement in phases:
1. **Phase 1 (Current):** Core functionality ✅
2. **Phase 2:** Analytics, search, bulk ops
3. **Phase 3:** Enterprise features (RBAC, notifications)
4. **Phase 4:** Advanced integrations & AI feedback

Start with Phase 2 for maximum user impact.
