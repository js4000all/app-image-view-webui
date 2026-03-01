/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $TagQueryResponse = {
    properties: {
        file_ids: {
            type: 'array',
            contains: {
                type: 'string',
            },
            isRequired: true,
        },
        total: {
            type: 'number',
            isRequired: true,
        },
    },
} as const;
