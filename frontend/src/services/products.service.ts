import { apiClient } from "@/lib/api-client";
import type {
    Product,
    ProductCreateRequest,
    ProductDeleteResponse,
    ProductListResponse,
    ProductUpdateRequest,
} from "@/types/product";

export async function getProducts(): Promise<ProductListResponse> {
    const response = await apiClient.get<ProductListResponse>("/products");
    return response.data;
}

export async function getProductById(productId: string): Promise<Product> {
    const response = await apiClient.get<Product>(`/products/${productId}`);
    return response.data;
}

export async function createProduct(
    payload: ProductCreateRequest,
): Promise<Product> {
    const response = await apiClient.post<Product>("/products", payload);
    return response.data;
}

export async function updateProduct(
    productId: string,
    payload: ProductUpdateRequest,
): Promise<Product> {
    const response = await apiClient.put<Product>(`/products/${productId}`, payload);
    return response.data;
}

export async function deleteProduct(
    productId: string,
): Promise<ProductDeleteResponse> {
    const response = await apiClient.delete<ProductDeleteResponse>(`/products/${productId}`);
    return response.data;
}
