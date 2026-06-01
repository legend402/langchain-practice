import { LocalStorageTokenStorage } from "./tokenStorage";
import type { TokenStorage } from "./tokenStorage";
import { HttpClient } from "./httpClient";
import { createAuthInterceptors } from "./authInterceptors";

export type { TokenStorage } from "./tokenStorage";
export { HttpException } from "./httpClient";
export type { ApiResponse } from "./httpClient";

export const tokenStorage: TokenStorage = new LocalStorageTokenStorage();

export const httpClient = new HttpClient();

const { requestInterceptor, responseInterceptor } = createAuthInterceptors(tokenStorage);
httpClient.useRequestInterceptor(requestInterceptor);
httpClient.useResponseInterceptor(responseInterceptor);
