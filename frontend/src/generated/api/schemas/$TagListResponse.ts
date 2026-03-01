/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $TagListResponse = {
    properties: {
        tags: {
            type: 'array',
            contains: {
                type: 'TagSummaryEntry',
            },
            isRequired: true,
        },
    },
} as const;
