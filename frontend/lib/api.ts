import axios from "axios";

const BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: BASE_URL });

// ── Types ────────────────────────────────────────────────────────────────────

export interface ChatRequest {
    message: string;
    session_id?: string;
    customer_id: string;
    channel: string;
}

export interface Product {
    id: string;
    name: string;
    category: string;
    price: number;
    description: string;
    occasionTags: string[];
    rating: number;
    imageUrl: string;
}

export interface CartItem {
    sku_id: string;
    name: string;
    price: number;
    quantity: number;
}

export interface ChatResponse {
    reply: string;
    session_id: string;
    recommended_products: Product[];
    cart: CartItem[];
    payment_status: string;
    fulfillment_status: string;
    intent: string;
}

export interface ProductsResponse {
    products: Product[];
    count: number;
}

export interface ProductFilters {
    category?: string;
    occasion?: string;
    max_price?: number;
    min_price?: number;
}

// ── Functions ────────────────────────────────────────────────────────────────

export async function sendChatMessage(
    req: ChatRequest
): Promise<ChatResponse> {
    if (process.env.NODE_ENV === "development") {
        console.log(`[API] POST ${BASE_URL}/chat`, req);
    }
    try {
        const { data } = await client.post<ChatResponse>("/chat", req);
        return data;
    } catch (err: unknown) {
        const msg =
            axios.isAxiosError(err) && err.response?.data?.detail
                ? err.response.data.detail
                : "Failed to send chat message";
        throw new Error(msg);
    }
}

export async function getProducts(
    filters?: ProductFilters
): Promise<ProductsResponse> {
    const params: Record<string, string | number> = {};
    if (filters?.category) params.category = filters.category;
    if (filters?.occasion) params.occasion = filters.occasion;
    if (filters?.max_price !== undefined) params.max_price = filters.max_price;
    if (filters?.min_price !== undefined) params.min_price = filters.min_price;

    if (process.env.NODE_ENV === "development") {
        console.log(`[API] GET ${BASE_URL}/products`, params);
    }
    try {
        const { data } = await client.get<ProductsResponse>("/products", {
            params,
        });
        return data;
    } catch (err: unknown) {
        const msg =
            axios.isAxiosError(err) && err.response?.data?.detail
                ? err.response.data.detail
                : "Failed to fetch products";
        throw new Error(msg);
    }
}

export async function switchChannel(
    session_id: string,
    new_channel: string
): Promise<void> {
    if (process.env.NODE_ENV === "development") {
        console.log(`[API] POST ${BASE_URL}/chat/switch-channel`, {
            session_id,
            new_channel,
        });
    }
    try {
        await client.post("/chat/switch-channel", { session_id, new_channel });
    } catch (err: unknown) {
        const msg =
            axios.isAxiosError(err) && err.response?.data?.detail
                ? err.response.data.detail
                : "Failed to switch channel";
        throw new Error(msg);
    }
}

export async function getLoyalty(customer_id: string): Promise<unknown> {
    if (process.env.NODE_ENV === "development") {
        console.log(`[API] GET ${BASE_URL}/loyalty/${customer_id}`);
    }
    try {
        const { data } = await client.get(`/loyalty/${customer_id}`);
        return data;
    } catch (err: unknown) {
        const msg =
            axios.isAxiosError(err) && err.response?.data?.detail
                ? err.response.data.detail
                : "Failed to fetch loyalty data";
        throw new Error(msg);
    }
}
