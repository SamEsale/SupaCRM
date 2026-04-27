export type ProductImage = {
  id: string;
  tenant_id: string;
  product_id: string;
  position: number;
  file_key: string;
  created_at: string;
  file_url?: string | null;
};

export type Product = {
  id: string;
  tenant_id: string;
  name: string;
  sku: string;
  description: string | null;
  unit_price: string;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  images: ProductImage[];
};

export type ProductListResponse = {
  items: Product[];
  total: number;
};

export type ProductImageInput = {
  position: number;
  file_key: string;
  file_url?: string | null;
};

export type ProductCreateRequest = {
  name: string;
  sku: string;
  description: string | null;
  unit_price: string;
  currency: string;
  is_active: boolean;
  images: ProductImageInput[];
};

export type ProductUpdateRequest = {
  name?: string | null;
  sku?: string | null;
  description?: string | null;
  unit_price?: string | null;
  currency?: string | null;
  is_active?: boolean | null;
  images?: ProductImageInput[] | null;
};

export type ProductDeleteResponse = {
  success: boolean;
  message: string;
};
