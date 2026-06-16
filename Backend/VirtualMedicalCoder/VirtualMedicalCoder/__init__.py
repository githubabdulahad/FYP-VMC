try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    # Celery not installed - optional dependency for background tasks
    celery_app = None
    __all__ = ()
