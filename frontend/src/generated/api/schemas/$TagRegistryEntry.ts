/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $TagRegistryEntry = {
    properties: {
        file_ids: {
            type: 'array',
            contains: {
                type: 'string',
            },
            isRequired: true,
        },
        tag: {
            type: 'string',
            isRequired: true,
        },
    },
} as const;
