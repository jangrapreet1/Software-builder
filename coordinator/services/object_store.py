"""
Object storage abstraction with S3/MinIO primary backend and local filesystem fallback.
"""
from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

try:
    import boto3  # type: ignore
    from botocore.client import Config as BotoConfig  # type: ignore
    _HAS_BOTO3 = True
except Exception:  # pragma: no cover
    _HAS_BOTO3 = False


@dataclass
class ObjectLocation:
    bucket: str
    key: str


class BaseObjectStore:
    def ensure_bucket(self) -> None:
        raise NotImplementedError

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> ObjectLocation:
        raise NotImplementedError

    def open_read(self, key: str) -> io.BufferedReader:
        raise NotImplementedError

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> Optional[str]:
        return None

    def delete_object(self, key: str) -> None:
        raise NotImplementedError


class LocalObjectStore(BaseObjectStore):
    """Local filesystem fallback store under .sb_artifacts/objects"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.bucket = "local"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def ensure_bucket(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        key = key.lstrip("/")
        return self.base_dir / key

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> ObjectLocation:
        path = self._key_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return ObjectLocation(bucket=self.bucket, key=key)

    def open_read(self, key: str) -> io.BufferedReader:
        path = self._key_path(key)
        return open(path, "rb")

    def delete_object(self, key: str) -> None:
        path = self._key_path(key)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


class S3ObjectStore(BaseObjectStore):
    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
        use_path_style: bool = True,
    ) -> None:
        if not _HAS_BOTO3:
            raise RuntimeError("boto3 is not installed; cannot use S3ObjectStore")
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=BotoConfig(s3={"addressing_style": "path" if use_path_style else "virtual"}),
        )

    def ensure_bucket(self) -> None:
        # Try head, else create
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> ObjectLocation:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return ObjectLocation(bucket=self.bucket, key=key)

    def open_read(self, key: str) -> io.BufferedReader:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        body = obj["Body"].read()
        return io.BufferedReader(io.BytesIO(body))

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> Optional[str]:
        try:
            return self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_seconds,
            )
        except Exception:
            return None

    def delete_object(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            pass


def build_store_from_env(artifact_root: Path, settings) -> BaseObjectStore:
    """Create an object store from Settings; fall back to local store if misconfigured."""
    endpoint = getattr(settings, "object_store_endpoint", None)
    bucket = getattr(settings, "object_store_bucket", None)
    access_key = getattr(settings, "object_store_access_key", None)
    secret_key = getattr(settings, "object_store_secret_key", None)
    region = getattr(settings, "object_store_region", None)
    use_path_style = getattr(settings, "object_store_use_path_style", True)

    if _HAS_BOTO3 and endpoint and bucket and access_key and secret_key:
        try:
            s3 = S3ObjectStore(
                endpoint_url=endpoint,
                bucket=bucket,
                access_key=access_key,
                secret_key=secret_key,
                region=region,
                use_path_style=use_path_style,
            )
            s3.ensure_bucket()
            return s3
        except Exception:
            # Fallback to local store if S3 init fails
            pass

    return LocalObjectStore(artifact_root / "objects")


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()
