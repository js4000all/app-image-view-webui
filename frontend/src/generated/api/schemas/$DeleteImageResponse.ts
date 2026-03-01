/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $DeleteImageResponse = {
    properties: {
        deleted: {
            type: 'string',
            isRequired: true,
            minLength: 1,
            pattern: '^[^/\\\\]+$',
        },
        file_id: {
            type: 'string',
            isRequired: true,
        },
    },
} as const;
