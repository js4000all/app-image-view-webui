/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $SubdirectoriesResponse = {
    properties: {
        subdirectories: {
            type: 'array',
            contains: {
                type: 'DirectoryEntry',
            },
            isRequired: true,
        },
    },
} as const;
