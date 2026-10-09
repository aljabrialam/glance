export const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(public status: number, public body: any) {
    super(
      typeof body?.detail === 'string' ? body.detail
        : typeof body?.detail?.message === 'string' ? body.detail.message
        : body?.error === 'reap' ? `Reap ${body.status}: ${JSON.stringify(body.response)}`
        : `HTTP ${status}`,
    );
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

// All money is integer cents in one currency per session (constitution V).
export type Cents = number;

export type LimitDecision = {
  limitCents: Cents; totalCents: Cents; allowed: boolean; overByCents: Cents; remainingCents: Cents;
};
export type Product = {
  id: string; name: string; merchant?: string; imageUrl?: string; priceCents: Cents | null;
  variantId?: string; requiresShipping?: boolean; rank?: number;
};
export type ShippingOption = { id: string; name: string; priceCents: Cents | null; selected: boolean };
export type Quote = {
  quoteId: string; shippingOptions: ShippingOption[]; itemCents: Cents | null; shippingCents: Cents | null;
  taxCents: Cents | null; discountCents: Cents; totalCents: Cents | null; currency: string; expiresAt?: string;
  limit: LimitDecision | null;
};
export type Order = {
  checkoutId: string; orderId?: string; finalAmountCents: Cents | null;
  item?: { name?: string; merchant?: string } | null; deliveryName?: string | null; at: number;
};
export type Home = {
  vaultBalanceCents: Cents | null; vaultSource: 'kwal' | 'mock'; cardLast4: string | null; currency: string;
  limitCents: Cents; orders: Order[]; enrollmentActive: boolean;
};
export type CheckoutStatus = {
  status: string; terminal: boolean; orderId?: string; finalAmountCents: Cents | null; currency: string;
  deliveryName?: string | null; vaultBeforeCents?: Cents | null; vaultAfterCents?: Cents | null; vaultSource?: string;
};

export const api = {
  home: () => req<Home>('GET', '/api/home'),
  setLimit: (perPurchaseCents: Cents) => req<{ limitCents: Cents }>('PUT', '/api/limit', { perPurchaseCents }),
  intent: (text: string) => req<{ query: string; maxPriceCents: Cents | null }>('POST', '/api/intent', { text }),
  search: (query: string, maxPriceCents: Cents | null) =>
    req<{ products: Product[]; pickId: string | null; currency: string }>('POST', '/api/search', { query, maxPriceCents }),
  quote: (b: { variantId?: string; quoteId?: string; shippingOptionId?: string; requiresShipping?: boolean }) =>
    req<Quote>('POST', '/api/quote', b),
  checkout: (quoteId: string, item: { name?: string; merchant?: string; imageUrl?: string }, deliveryName?: string) =>
    req<{ checkoutId: string; status: string; approvalUrl: string | null }>('POST', '/api/checkout', { quoteId, item, deliveryName }),
  checkoutStatus: (id: string) => req<CheckoutStatus>('GET', `/api/checkout/${id}`),
};
