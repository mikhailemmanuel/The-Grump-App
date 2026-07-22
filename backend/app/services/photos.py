import uuid
import boto3
import logging
from datetime import datetime, timezone
from app.config import settings
from app.celery_app import celery

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",  # WebP starts with RIFF
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def generate_presigned_url(user_id: uuid.UUID, content_type: str = "image/jpeg") -> dict:
    """Generate a pre-signed S3 upload URL. Returns {upload_url, object_key}."""
    if content_type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported content type: {content_type}")
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[content_type]
    object_key = f"uploads/{user_id}/{datetime.now(timezone.utc).strftime('%Y%m%d')}/{uuid.uuid4()}{ext}"
    s3 = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.aws_s3_bucket,
            "Key": object_key,
            "ContentType": content_type,
            "ContentLength": MAX_FILE_SIZE,  # max size condition
        },
        ExpiresIn=300,
    )
    return {"upload_url": url, "object_key": object_key}


def validate_magic_bytes(data: bytes) -> str | None:
    """Check first bytes of file to verify image type. Returns content_type or None."""
    for magic, content_type in MAGIC_BYTES.items():
        if data[: len(magic)] == magic:
            return content_type
    return None


@celery.task(name="app.services.photos.strip_exif")
def strip_exif(object_key: str):
    """Download image from S3, strip EXIF, re-upload."""
    logger = logging.getLogger(__name__)
    try:
        from PIL import Image
        import io

        s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        response = s3.get_object(Bucket=settings.aws_s3_bucket, Key=object_key)
        image_data = response["Body"].read()
        img = Image.open(io.BytesIO(image_data))
        # Strip EXIF by saving without exif
        clean = io.BytesIO()
        img.save(clean, format=img.format or "JPEG", quality=90)
        clean.seek(0)
        s3.put_object(
            Bucket=settings.aws_s3_bucket,
            Key=object_key,
            Body=clean.read(),
            ContentType=f"image/{(img.format or 'jpeg').lower()}",
        )
        logger.info("Stripped EXIF from %s", object_key)
    except Exception:
        logger.exception("Failed to strip EXIF from %s", object_key)


@celery.task(name="app.services.photos.moderate_image")
def moderate_image(object_key: str):
    """Download image from S3 and run it through AWS Rekognition DetectModerationLabels.

    If any label exceeds the confidence threshold, the object is deleted and the
    task raises an exception so Celery can retry / alert.
    """
    logger = logging.getLogger(__name__)
    CONFIDENCE_THRESHOLD = 75.0  # percent

    try:
        s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        rekognition = boto3.client(
            "rekognition",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        response = rekognition.detect_moderation_labels(
            Image={"S3Object": {"Bucket": settings.aws_s3_bucket, "Name": object_key}},
            MinConfidence=CONFIDENCE_THRESHOLD,
        )

        flagged = response.get("ModerationLabels", [])
        if flagged:
            label_names = [lbl["Name"] for lbl in flagged]
            logger.warning(
                "Moderation: deleting %s — flagged labels: %s", object_key, label_names
            )
            s3.delete_object(Bucket=settings.aws_s3_bucket, Key=object_key)
            raise ValueError(f"Image {object_key} failed moderation: {label_names}")

        logger.info("Moderation: %s passed", object_key)
    except ValueError:
        raise
    except Exception:
        logger.exception("Moderation check failed for %s", object_key)
