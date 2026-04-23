from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


UploadPurpose = Literal["product-image", "tenant-logo"]


class PresignedUploadRequest(BaseModel):
    purpose: UploadPurpose
    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=128)


class PresignedUploadResponse(BaseModel):
    bucket: str
    file_key: str
    upload_url: str
    download_url: str
    expires_in_seconds: int


class UploadObjectRequest(BaseModel):
    purpose: UploadPurpose
    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=128)
    content_base64: str = Field(..., min_length=1)


class UploadObjectResponse(BaseModel):
    bucket: str
    file_key: str
    file_url: str
