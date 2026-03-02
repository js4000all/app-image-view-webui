/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $TagRegistryResponse = {
    properties: {
        tags: {
            type: 'array',
            contains: {
                type: 'TagRegistryEntry',
            },
            isRequired: true,
        },
    },
} as const;
