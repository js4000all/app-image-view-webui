/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $TagIndexRefreshJobStatusResponse = {
    properties: {
        counters: {
            type: 'TagIndexRefreshJobCounters',
            isRequired: true,
        },
        error: {
            type: 'any-of',
            contains: [{
                type: 'string',
            }, {
                type: 'null',
            }],
        },
        indexed_files: {
            type: 'number',
            isRequired: true,
        },
        indexed_tags: {
            type: 'number',
            isRequired: true,
        },
        job_id: {
            type: 'string',
            isRequired: true,
        },
        processed_files: {
            type: 'number',
            isRequired: true,
        },
        progress_phase: {
            type: 'Enum',
            isRequired: true,
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        total_files: {
            type: 'number',
            isRequired: true,
        },
    },
} as const;
