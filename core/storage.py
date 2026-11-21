"""MinIO/S3 Storage and Presigned URLs (Integration Standard Point 7)."""

import os
import boto3
from botocore.client import Config
from core.config import settings


class StorageService:
    def __init__(self):
        self.endpoint = settings.S3_ENDPOINT_URL
        self.bucket = settings.S3_BUCKET_NAME
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )

    def upload_file_bytes(self, data: bytes, object_name: str, content_type: str = "application/octet-stream") -> str:
        if settings.SIMULATION_MODE:
            # Store locally in simulation mode
            local_path = os.path.join("data", "storage", object_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            return f"{settings.BASE_URL}/files/{object_name}"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_name,
                Body=data,
                ContentType=content_type,
            )
            return self.get_presigned_url(object_name)
        except Exception:
            return f"{settings.BASE_URL}/files/{object_name}"

    def get_presigned_url(self, object_name: str, expires_in: int = 3600) -> str:
        if settings.SIMULATION_MODE:
            return f"{settings.BASE_URL}/files/{object_name}"
        try:
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=expires_in,
            )
        except Exception:
            return f"{settings.BASE_URL}/files/{object_name}"


storage = StorageService()
