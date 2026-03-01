/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RenameDirectoryResponse = {
    properties: {
        directory_id: {
            type: 'string',
            isRequired: true,
        },
        renamed_from: {
            type: 'string',
            isRequired: true,
            minLength: 1,
            pattern: '^[^/\\\\]+$',
        },
        renamed_to: {
            type: 'string',
            isRequired: true,
            minLength: 1,
            pattern: '^[^/\\\\]+$',
        },
    },
} as const;
