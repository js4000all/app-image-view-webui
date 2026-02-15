from __future__ import annotations

from pydantic import BaseModel


class DirectoryEntry(BaseModel):
    directory_id: str
    name: str


class ImageEntry(BaseModel):
    file_id: str
    name: str


class SubdirectoriesResponse(BaseModel):
    subdirectories: list[DirectoryEntry]


class ImagesResponse(BaseModel):
    directory_id: str
    subdirectory: str
    images: list[ImageEntry]


class DeleteImageResponse(BaseModel):
    deleted: str
    file_id: str


class RenameDirectoryRequest(BaseModel):
    new_name: str


class RenameDirectoryResponse(BaseModel):
    directory_id: str
    renamed_from: str
    renamed_to: str
