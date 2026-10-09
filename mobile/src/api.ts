export const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(public status: number, public body: any) {
    super(typeof body?.detail === 'string' ? body.detail : body?.error === 'reap' ? `Reap ${body.status}: ${JSON.stringify(body.response)}` : `HTTP ${status}`);
  }
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(API_URL + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, data);
  return data as T;
}

export type Product = {
  id: string; name: string; merchant?: string; imageUrl?: string; price: number | null;
  variantId?: string; requiresShipping?: boolean;
};
export type ShippingOption = { id: string; name: string; price: number | null; selected: boolean };
export type Quote = {
  quoteId: string; shippingOptions: ShippingOption[]; subtotal: number | null; shipping: number | null;
  tax: number | null; discounts: number; total: number | null; currency: string; expiresAt?: string;
  limit: number; overLimit: boolean; overBy: number;
};
export type Order = { checkoutId: string; orderId?: string; finalAmount: number | null; item?: { name?: string; merchant?: string } | null; at: number };
export type Home = { vaultBalance: number | null; vaultSource: string; cardLast4: string; limit: number; orders: Order[]; enrollmentId?: string };
export type CheckoutStatus = {
  status: string; terminal: boolean; orderId?: string; finalAmount: number | null;
  vaultBefore?: number | null; vaultAfter?: number | null; vaultSource?: string;
};

export const api = {
  home: () => req<Home>('GET', '/api/home'),
  setLimit: (perPurchase: number) => req<{ limit: number }>('PUT', '/api/limit', { perPurchase }),
  intent: (text: string) => req<{ query: string; maxPrice: number | null }>('POST', '/api/intent', { text }),
  search: (query: string, maxPrice: number | null) =>
    req<{ products: Product[]; pickId: string | null }>('POST', '/api/search', { query, maxPrice }),
  quote: (b: { variantId?: string; quoteId?: string; shippingOptionId?: string; requiresShipping?: boolean }) =>
    req<Quote>('POST', '/api/quote', b),
  checkout: (quoteId: string, item: { name?: string; merchant?: string; imageUrl?: string }) =>
    req<{ checkoutId: string; status: string; approvalUrl: string | null }>('POST', '/api/checkout', { quoteId, item }),
  checkoutStatus: (id: string) => req<CheckoutStatus>('GET', `/api/checkout/${id}`),
};
