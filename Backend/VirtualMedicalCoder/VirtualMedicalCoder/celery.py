"""Celery application configuration for VirtualMedicalCoder."""

import os
import sys

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "VirtualMedicalCoder.settings")

app = Celery("VirtualMedicalCoder")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Windows compatibility: use solo pool instead of prefork
# prefork uses multiprocessing which has issues with Windows IPC
if sys.platform == "win32":
    app.conf.update(worker_pool="solo")