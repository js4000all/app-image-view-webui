/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeleteImageResponse } from '../models/DeleteImageResponse';
import type { ImagesResponse } from '../models/ImagesResponse';
import type { RenameDirectoryRequest } from '../models/RenameDirectoryRequest';
import type { RenameDirectoryResponse } from '../models/RenameDirectoryResponse';
import type { SubdirectoriesResponse } from '../models/SubdirectoriesResponse';
import type { TagIndexRefreshJobStartResponse } from '../models/TagIndexRefreshJobStartResponse';
import type { TagIndexRefreshJobStatusResponse } from '../models/TagIndexRefreshJobStatusResponse';
import type { TagIndexRefreshResponse } from '../models/TagIndexRefreshResponse';
import type { TagQueryRequest } from '../models/TagQueryRequest';
import type { TagQueryResponse } from '../models/TagQueryResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DefaultService {
    /**
     * Home
     * @returns any Successful Response
     * @throws ApiError
     */
    public static homeGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/',
        });
    }
    /**
     * Delete Image
     * @returns DeleteImageResponse Successful Response
     * @throws ApiError
     */
    public static deleteImage({
        fileId,
    }: {
        fileId: string,
    }): CancelablePromise<DeleteImageResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/image/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Image
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getImage({
        fileId,
    }: {
        fileId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/image/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Head Image
     * @returns any Successful Response
     * @throws ApiError
     */
    public static headImage({
        fileId,
    }: {
        fileId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'HEAD',
            url: '/api/image/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Images
     * @returns ImagesResponse Successful Response
     * @throws ApiError
     */
    public static listImages({
        directoryId,
    }: {
        directoryId: string,
    }): CancelablePromise<ImagesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/images/{directory_id}',
            path: {
                'directory_id': directoryId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Subdirectories
     * @returns SubdirectoriesResponse Successful Response
     * @throws ApiError
     */
    public static listSubdirectories(): CancelablePromise<SubdirectoriesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/subdirectories',
        });
    }
    /**
     * Rename Subdirectory
     * @returns RenameDirectoryResponse Successful Response
     * @throws ApiError
     */
    public static renameSubdirectory({
        directoryId,
        requestBody,
    }: {
        directoryId: string,
        requestBody: RenameDirectoryRequest,
    }): CancelablePromise<RenameDirectoryResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/subdirectories/{directory_id}',
            path: {
                'directory_id': directoryId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Query Tag Index
     * @returns TagQueryResponse Successful Response
     * @throws ApiError
     */
    public static queryTagIndex({
        requestBody,
    }: {
        requestBody: TagQueryRequest,
    }): CancelablePromise<TagQueryResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/tag-index/query',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Refresh Tag Index
     * Backward-compatible synchronous refresh API.
     *
     * New clients should migrate to POST /api/tag-index/refresh-jobs and
     * poll GET /api/tag-index/refresh-jobs/{job_id}. This endpoint currently
     * waits for job completion and returns the final counts.
     * @returns TagIndexRefreshResponse Successful Response
     * @throws ApiError
     */
    public static refreshTagIndex(): CancelablePromise<TagIndexRefreshResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/tag-index/refresh',
        });
    }
    /**
     * Start Tag Index Refresh Job
     * @returns TagIndexRefreshJobStartResponse Successful Response
     * @throws ApiError
     */
    public static startTagIndexRefreshJob(): CancelablePromise<TagIndexRefreshJobStartResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/tag-index/refresh-jobs',
        });
    }
    /**
     * Get Tag Index Refresh Job
     * @returns TagIndexRefreshJobStatusResponse Successful Response
     * @throws ApiError
     */
    public static getTagIndexRefreshJob({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<TagIndexRefreshJobStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/tag-index/refresh-jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Viewer
     * @returns any Successful Response
     * @throws ApiError
     */
    public static viewerViewerGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/viewer',
        });
    }
}
