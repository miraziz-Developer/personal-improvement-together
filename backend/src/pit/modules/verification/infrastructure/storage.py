import asyncio
import hashlib
import hmac
import time
from pathlib import Path
from typing import Any, Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class FileStorage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def url(self, key: str, expires_seconds: int = 900) -> str: ...


class S3Storage:
    """Any S3-compatible store (MinIO locally). Files are private; clients get short-lived URLs."""

    def __init__(self, *, endpoint_url: str, bucket: str, access_key: str, secret_key: str) -> None:
        self._bucket = bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def ensure_bucket(self) -> None:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
        except ClientError:
            await asyncio.to_thread(self._client.create_bucket, Bucket=self._bucket)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        def read() -> bytes:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
            return bytes(obj["Body"].read())

        return await asyncio.to_thread(read)

    async def url(self, key: str, expires_seconds: int = 900) -> str:
        return str(
            self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_seconds,
            )
        )


class LocalFileStorage:
    """Local development: files on disk, served by the API through short-lived signed links."""

    def __init__(self, *, root: Path, public_base_url: str, secret: bytes) -> None:
        self._root = root.resolve()
        self._base = public_base_url.rstrip("/")
        self._secret = secret

    def path_for(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("Invalid storage key")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self.path_for(key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(write)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self.path_for(key).read_bytes)

    def sign(self, key: str, expires_at: int) -> str:
        message = f"{key}:{expires_at}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()

    def verify(self, key: str, expires_at: int, signature: str) -> bool:
        fresh = expires_at >= int(time.time())
        return fresh and hmac.compare_digest(self.sign(key, expires_at), signature)

    async def url(self, key: str, expires_seconds: int = 900) -> str:
        expires_at = int(time.time()) + expires_seconds
        signature = self.sign(key, expires_at)
        return f"{self._base}/api/v1/media/{key}?exp={expires_at}&sig={signature}"


class InMemoryStorage:
    """For tests and for running without MinIO."""

    def __init__(self) -> None:
        self.files: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.files[key] = (data, content_type)

    async def get(self, key: str) -> bytes:
        return self.files[key][0]

    async def url(self, key: str, expires_seconds: int = 900) -> str:
        return f"memory://{key}"
