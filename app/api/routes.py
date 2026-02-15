from __future__ import annotations

import mimetypes
from email.utils import formatdate, parsedate_to_datetime
from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from app.models.schemas import (
    DeleteImageResponse,
    ImagesResponse,
    RenameDirectoryRequest,
    RenameDirectoryResponse,
    SubdirectoriesResponse,
)
from app.services.image_service import (
    ConflictError,
    ImageService,
    ResourceNotFoundError,
    ServiceError,
    UnsupportedMediaTypeError,
    ValidationError,
)


def create_api_router(service: ImageService) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/subdirectories", response_model=SubdirectoriesResponse)
    def get_subdirectories() -> SubdirectoriesResponse:
        return SubdirectoriesResponse(subdirectories=service.list_subdirectories())

    @router.get("/images/{directory_id}", response_model=ImagesResponse)
    def get_images(directory_id: str) -> ImagesResponse:
        try:
            directory, images = service.list_images(directory_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND) from exc
        return ImagesResponse(directory_id=directory_id, subdirectory=directory.name, images=images)

    def _build_image_response(file_id: str, request: Request, include_body: bool) -> Response:
        try:
            file_path = service.resolve_image(file_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND) from exc
        except UnsupportedMediaTypeError as exc:
            raise HTTPException(status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE) from exc

        try:
            stat_result = file_path.stat()
        except OSError as exc:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR) from exc

        etag = f'W/"{stat_result.st_mtime_ns}-{stat_result.st_size}"'
        last_modified = formatdate(stat_result.st_mtime, usegmt=True)
        cache_headers = {
            "ETag": etag,
            "Last-Modified": last_modified,
            "Cache-Control": "public, max-age=31536000",
        }

        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip() == etag:
            return Response(status_code=HTTPStatus.NOT_MODIFIED, headers=cache_headers)

        if_modified_since = request.headers.get("if-modified-since")
        if if_modified_since:
            try:
                since_timestamp = parsedate_to_datetime(if_modified_since).timestamp()
                if stat_result.st_mtime <= since_timestamp:
                    return Response(status_code=HTTPStatus.NOT_MODIFIED, headers=cache_headers)
            except (TypeError, ValueError, OverflowError):
                pass

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        headers = {**cache_headers, "Content-Length": str(stat_result.st_size)}

        if not include_body:
            return Response(status_code=HTTPStatus.OK, headers=headers, media_type=content_type)

        return FileResponse(path=file_path, media_type=content_type, headers=headers)

    @router.get("/image/{file_id}")
    def get_image(file_id: str, request: Request) -> Response:
        return _build_image_response(file_id=file_id, request=request, include_body=True)

    @router.head("/image/{file_id}")
    def head_image(file_id: str, request: Request) -> Response:
        return _build_image_response(file_id=file_id, request=request, include_body=False)

    @router.delete("/image/{file_id}", response_model=DeleteImageResponse)
    def delete_image(file_id: str) -> DeleteImageResponse:
        try:
            deleted_file = service.delete_image(file_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND) from exc
        except UnsupportedMediaTypeError as exc:
            raise HTTPException(status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE) from exc
        except ServiceError as exc:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR) from exc

        return DeleteImageResponse(deleted=deleted_file.name, file_id=file_id)

    @router.put("/subdirectories/{directory_id}", response_model=RenameDirectoryResponse)
    def rename_subdirectory(directory_id: str, payload: RenameDirectoryRequest) -> RenameDirectoryResponse:
        try:
            new_directory_id, renamed_from, renamed_to = service.rename_subdirectory(directory_id, payload.new_name)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=HTTPStatus.CONFLICT) from exc
        except ServiceError as exc:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR) from exc

        return RenameDirectoryResponse(
            directory_id=new_directory_id,
            renamed_from=renamed_from,
            renamed_to=renamed_to,
        )

    return router
