from __future__ import annotations

from pydantic import BaseModel
from typing import Literal

from app.models.types import DirectoryId, DirectoryName, FileId, FileName


class DirectoryEntry(BaseModel):
    directory_id: DirectoryId
    name: DirectoryName


class ImageEntry(BaseModel):
    file_id: FileId
    name: FileName


class SubdirectoriesResponse(BaseModel):
    subdirectories: list[DirectoryEntry]


class ImagesResponse(BaseModel):
    directory_id: DirectoryId
    subdirectory: DirectoryName
    images: list[ImageEntry]


class DeleteImageResponse(BaseModel):
    deleted: FileName
    file_id: FileId


class ImageMetadataResponse(BaseModel):
    file_id: FileId
    name: FileName
    directory_id: DirectoryId
    directory_name: DirectoryName


class RenameDirectoryRequest(BaseModel):
    new_name: DirectoryName


class RenameDirectoryResponse(BaseModel):
    directory_id: DirectoryId
    renamed_from: DirectoryName
    renamed_to: DirectoryName


class TagIndexRefreshResponse(BaseModel):
    indexed_files: int
    indexed_tags: int


class TagIndexRefreshJobStartResponse(BaseModel):
    job_id: str


class TagIndexRefreshJobCounters(BaseModel):
    added: int
    modified: int
    deleted: int
    reindexed: int


class TagIndexRefreshJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    progress_phase: Literal["queued", "listing", "scanning", "applying", "finalizing", "done", "failed"]
    processed_files: int
    total_files: int
    indexed_files: int
    indexed_tags: int
    counters: TagIndexRefreshJobCounters
    error: str | None = None


class TagQueryRequest(BaseModel):
    tags: list[str]
    mode: Literal["and", "or"] = "or"


class TagQueryResponse(BaseModel):
    file_ids: list[FileId]
    total: int


class TagSummaryEntry(BaseModel):
    tag: str
    count: int


class TagListResponse(BaseModel):
    tags: list[TagSummaryEntry]


class TagRegistryEntry(BaseModel):
    tag: str
    file_ids: list[FileId]


class TagRegistryResponse(BaseModel):
    tags: list[TagRegistryEntry]
