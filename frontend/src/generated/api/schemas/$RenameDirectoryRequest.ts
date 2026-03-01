/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RenameDirectoryRequest = {
    properties: {
        new_name: {
            type: 'string',
            isRequired: true,
            minLength: 1,
            pattern: '^[^/\\\\]+$',
        },
    },
} as const;
