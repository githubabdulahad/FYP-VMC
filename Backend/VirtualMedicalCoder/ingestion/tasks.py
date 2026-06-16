"""
ingestion/tasks.py

Celery task for asynchronous upload processing.
The task handles both uploaded files and raw text submissions, then updates
the UploadRecord so the frontend can poll progress from the API.
"""

import logging

try:
    from celery import shared_task
except ImportError:
    # Celery not installed - create a dummy decorator
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_upload_async(self, record_id: int):
    """
    Background task: extracts text and runs NLP on an UploadRecord.

    bind=True           → gives access to `self` so we can retry
    max_retries=3       → retry up to 3 times if it fails
    default_retry_delay → wait 10 seconds between retries

    Called like this in the view (non-blocking):
        process_upload_async.delay(record.id)
    """
    from ingestion.extractors import route_and_extract
    from ingestion.models import UploadRecord
    from ingestion.views import _run_nlp_and_save

    try:
        record = UploadRecord.objects.get(id=record_id)
    except UploadRecord.DoesNotExist:
        logger.error(f"UploadRecord {record_id} not found — task aborted.")
        return

    logger.info(f"[Task] Processing UploadRecord {record_id} | type={record.file_type}")

    # Mark as processing before any expensive work begins.
    record.status = UploadRecord.Status.PROCESSING
    record.error_message = ""
    record.save(update_fields=["status", "error_message"])

    # Extract text from the uploaded file, or reuse raw text directly.
    try:
        if record.file_type == UploadRecord.FileType.RAW_TEXT:
            extracted_text = (record.raw_text or "").strip()
            if not extracted_text:
                raise ValueError("No raw text was provided for processing.")
        else:
            extracted_text = route_and_extract(record.file_url, record.file_type)
    except Exception as exc:
        logger.error(f"[Task] Extraction failed for record {record_id}: {exc}")
        try:
            # Retry the task
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            record.status = UploadRecord.Status.FAILED
            record.error_message = str(exc)
            record.save(update_fields=["status", "error_message"])
        return

    record.extracted_text = extracted_text
    record.save(update_fields=["extracted_text"])

    # NLP analysis
    try:
        _run_nlp_and_save(record, record.user)
        record.status = UploadRecord.Status.COMPLETED
        record.error_message = ""
    except Exception as exc:
        logger.error(f"[Task] NLP failed for record {record_id}: {exc}")
        record.status = UploadRecord.Status.FAILED
        record.error_message = str(exc)

    record.save(update_fields=["status", "error_message"])
    logger.info(f"[Task] UploadRecord {record_id} finished with status: {record.status}")
