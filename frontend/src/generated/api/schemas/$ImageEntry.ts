/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ImageEntry = {
    properties: {
        file_id: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
            minLength: 1,
            pattern: '^[^/\\\\]+$',
        },
    },
} as const;
