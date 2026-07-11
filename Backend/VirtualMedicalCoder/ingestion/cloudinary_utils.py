import logging
from django.conf import settings
import cloudinary.uploader

logger = logging.getLogger(__name__)

def upload_file_to_cloudinary(file_obj):
    """
    Uploads a file-like object to Cloudinary.
    Performs a signed upload if API Key and Secret are configured.
    Otherwise, falls back to unsigned upload using the configured upload preset.
    """
    cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", "")
    api_key = getattr(settings, "CLOUDINARY_API_KEY", "")
    api_secret = getattr(settings, "CLOUDINARY_API_SECRET", "")
    preset = getattr(settings, "CLOUDINARY_UPLOAD_PRESET", "medical_unsigned")

    if api_key and api_secret:
        logger.info("Performing signed Cloudinary upload")
        res = cloudinary.uploader.upload(
            file_obj,
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            resource_type="auto"
        )
    else:
        logger.info(f"Performing unsigned Cloudinary upload with preset: {preset}")
        res = cloudinary.uploader.unsigned_upload(
            file_obj,
            upload_preset=preset,
            cloud_name=cloud_name,
            resource_type="auto"
        )
    
    return res.get("secure_url") or res.get("url")
