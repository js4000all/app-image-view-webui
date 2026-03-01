/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type TagQueryRequest = {
    mode?: TagQueryRequest.mode;
    tags: Array<string>;
};
export namespace TagQueryRequest {
    export enum mode {
        AND = 'and',
        OR = 'or',
    }
}

