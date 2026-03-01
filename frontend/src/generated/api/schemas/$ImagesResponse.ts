/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ImagesResponse = {
    properties: {
        directory_id: {
            type: 'string',
            isRequired: true,
        },
        images: {
            type: 'array',
            contains: {
                type: 'ImageEntry',
            },
            isRequired: true,
        },
        subdirectory: {
            type: 'string',
            isRequired: true,
            minLength: 1,
            pattern: '^[^/\\\\]+$',
        },
    },
} as const;
