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


class RenameDirectoryRequest(BaseModel):
    new_name: DirectoryName


class RenameDirectoryResponse(BaseModel):
    directory_id: DirectoryId
    renamed_from: DirectoryName
    renamed_to: DirectoryName


class TagIndexRefreshResponse(BaseModel):
    indexed_files: int
    indexed_tags: int


class TagQueryRequest(BaseModel):
    tags: list[str]
    mode: Literal["and", "or"] = "or"


class TagQueryResponse(BaseModel):
    file_ids: list[FileId]
    total: int
