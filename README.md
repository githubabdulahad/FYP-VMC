# Virtual Medical Coder (FYP)

AI-assisted clinical coding: ingest text/PDF/image/audio, run the NLP pipeline, validate ICD-10/CPT codes, human review, and verified reports.

## Project layout

| Path | Description |
|------|-------------|
| `Backend/VirtualMedicalCoder/` | Django REST API |
| `Frontend/` | React + Vite UI |

## Backend

```bash
cd Backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt

cd VirtualMedicalCoder
copy .env.example .env    # edit credentials
python manage.py migrate
python manage.py runserver
```

- API base: `http://127.0.0.1:8000/api/`
- **Swagger UI**: [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/)
- **ReDoc**: [http://127.0.0.1:8000/redoc/](http://127.0.0.1:8000/redoc/)

Start Redis + Celery for async uploads:

```bash
celery -A VirtualMedicalCoder worker -l info
```

## Frontend

```bash
cd Frontend
copy .env.example .env    # Cloudinary + optional API URL
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` to Django.

### Environment (Frontend `.env`)

- `VITE_CLOUDINARY_CLOUD_NAME` / `VITE_CLOUDINARY_UPLOAD_PRESET` — direct file upload before calling ingestion API
- Leave `VITE_API_BASE_URL` empty in dev to use the proxy

Auth uses **HttpOnly cookies** (`credentials: include`).

## App flow (UI)

1. **Dashboard** — stats and recent submissions  
2. **New submission** — text, PDF, image, or audio  
3. **Processing** — live pipeline stages (normalize → LLM → validate → review)  
4. **Review queue** — approve / revise / reject flagged codes  
5. **Results** — SOAP + ICD/CPT detail  
6. **Reports** — verified outputs with download/print  
