/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TagIndexRefreshJobCounters } from './TagIndexRefreshJobCounters';
export type TagIndexRefreshJobStatusResponse = {
    counters: TagIndexRefreshJobCounters;
    error?: (string | null);
    indexed_files: number;
    indexed_tags: number;
    job_id: string;
    processed_files: number;
    progress_phase: TagIndexRefreshJobStatusResponse.progress_phase;
    status: TagIndexRefreshJobStatusResponse.status;
    total_files: number;
};
export namespace TagIndexRefreshJobStatusResponse {
    export enum progress_phase {
        QUEUED = 'queued',
        LISTING = 'listing',
        SCANNING = 'scanning',
        APPLYING = 'applying',
        FINALIZING = 'finalizing',
        DONE = 'done',
        FAILED = 'failed',
    }
    export enum status {
        QUEUED = 'queued',
        RUNNING = 'running',
        SUCCEEDED = 'succeeded',
        FAILED = 'failed',
    }
}

