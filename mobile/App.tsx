import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, SafeAreaView, ScrollView, Text, TextInput, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import Slider from '@react-native-community/slider';
import { api, API_URL, ApiError, CheckoutStatus, Home, Product, Quote } from './src/api';
import { C, s } from './src/theme';
import Approve from './src/Approve';

type Screen = 'home' | 'ask' | 'results' | 'quote' | 'approve' | 'paid' | 'limit';
const money = (n: number | null | undefined) => (n == null ? '—' : '$' + n.toFixed(2));
const usdc = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(2));

function Btn({ title, onPress, disabled, ghost }: { title: string; onPress: () => void; disabled?: boolean; ghost?: boolean }) {
  return (
    <Pressable accessibilityRole="button" onPress={disabled ? undefined : onPress}
      style={[s.btn, ghost && s.ghost, disabled && { opacity: 0.45 }]}>
      <Text style={[s.btnText, ghost && s.ghostText]}>{title}</Text>
    </Pressable>
  );
}
const Back = ({ to, label, go }: { to: Screen; label: string; go: (s: Screen) => void }) => (
  <Pressable onPress={() => go(to)}><Text style={s.back}>← {label}</Text></Pressable>
);
function Radio({ on }: { on: boolean }) {
  return <View style={[s.radio, on && s.radioOn]}>{on && <View style={s.radioDot} />}</View>;
}
function ErrorBox({ err }: { err: unknown }) {
  if (!err) return null;
  const e = err as ApiError;
  return (
    <View style={s.alert}>
      <Text style={s.alertText}>{e.message || String(err)}</Text>
    </View>
  );
}

export default function App() {
  const [scr, setScr] = useState<Screen>('home');
  const [home, setHome] = useState<Home | null>(null);
  const [limit, setLimit] = useState(150);
  const [text, setText] = useState('Buy Sony WH-1000XM5 headphones, under $150');
  const [busy, setBusy] = useState(0);
  const [products, setProducts] = useState<Product[]>([]);
  const [pick, setPick] = useState<string | null>(null);
  const [agentPick, setAgentPick] = useState<string | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoting, setQuoting] = useState(false);
  const [toast, setToast] = useState('');
  const [err, setErr] = useState<unknown>(null);
  const [checkout, setCheckout] = useState<{ id: string; url: string | null } | null>(null);
  const [paid, setPaid] = useState<CheckoutStatus | null>(null);
  const [paying, setPaying] = useState(false);

  const go = (n: Screen) => { setErr(null); if (n !== 'quote') setToast(''); setScr(n); };
  const product = products.find((p) => p.id === pick);

  const loadHome = useCallback(async () => {
    try { const h = await api.home(); setHome(h); setLimit(h.limit); } catch (e) { setErr(e); }
  }, []);
  useEffect(() => { if (scr === 'home') loadHome(); }, [scr, loadHome]);

  async function find() {
    setErr(null); setBusy(1);
    try {
      const intent = await api.intent(text);
      setBusy(2);
      const r = await api.search(intent.query, intent.maxPrice ?? limit);
      setBusy(3);
      await new Promise((ok) => setTimeout(ok, 500));
      setProducts(r.products); setPick(r.pickId ?? r.products[0]?.id ?? null); setAgentPick(r.pickId);
      setBusy(0);
      go('results');
    } catch (e) { setBusy(0); setErr(e); }
  }

  async function getQuote(shippingOptionId?: string) {
    if (!product) return;
    setErr(null); setQuoting(true);
    try {
      const q = shippingOptionId && quote
        ? await api.quote({ quoteId: quote.quoteId, shippingOptionId })
        : await api.quote({ variantId: product.variantId, requiresShipping: product.requiresShipping ?? true });
      setQuote(q);
    } catch (e) { setErr(e); } finally { setQuoting(false); }
  }

  async function pay() {
    if (!quote || !product) return;
    setErr(null); setPaying(true);
    try {
      const c = await api.checkout(quote.quoteId, { name: product.name, merchant: product.merchant, imageUrl: product.imageUrl });
      setCheckout({ id: c.checkoutId, url: c.approvalUrl });
      if (c.approvalUrl) go('approve'); else await confirm(c.checkoutId);
    } catch (e) { setErr(e); } finally { setPaying(false); }
  }

  async function confirm(id = checkout?.id) {
    if (!id) return;
    setPaying(true);
    try {
      for (let i = 0; i < 30; i++) {
        const st = await api.checkoutStatus(id);
        if (st.terminal) {
          if (st.status === 'COMPLETED') { setPaid(st); go('paid'); }
          else { setToast(`Payment ${st.status.toLowerCase()}. Nothing was charged.`); go('quote'); }
          return;
        }
        await new Promise((ok) => setTimeout(ok, 2000));
      }
      setToast('Still waiting for approval. Try again.'); go('quote');
    } catch (e) { setErr(e); } finally { setPaying(false); }
  }

  const sbar = (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 8 }}>
      <Text style={[s.k, { letterSpacing: 0 }]}>Glance</Text><Text style={[s.k, { letterSpacing: 0 }]}>Sandbox</Text>
    </View>
  );

  let body: React.ReactNode = null;
  let foot: React.ReactNode = null;

  if (scr === 'home') {
    const mock = home?.vaultSource !== 'kwal';
    body = (<>
      <View style={s.vault}>
        <Text style={[s.k, { color: C.accentInk, opacity: 0.8 }]}>USDC vault{mock ? ' · demo balance' : ''}</Text>
        <Text style={s.vaultAmt}>{usdc(home?.vaultBalance)}<Text style={{ fontSize: 15 }}> USDC</Text></Text>
        <Text style={s.vaultMeta}>{mock ? 'Mock balance (Kwal vault pending)' : 'Test funds on Ink Sepolia'} · backs card •••• {home?.cardLast4 ?? '····'}</Text>
      </View>
      <View style={s.rowc}>
        <View><Text style={s.strong}>{money(limit)} per purchase</Text><Text style={s.small}>Glance stops above this</Text></View>
        <Pressable onPress={() => go('limit')}><Text style={s.link}>Change</Text></Pressable>
      </View>
      <Text style={s.k}>Orders</Text>
      {home?.orders.length ? home.orders.map((o) => (
        <View key={o.checkoutId} style={s.rowc}>
          <View style={{ flex: 1 }}>
            <Text style={s.strong} numberOfLines={1}>{o.item?.name ?? 'Order'}</Text>
            <Text style={s.small} numberOfLines={1}>Order {o.orderId ?? o.checkoutId} · {o.item?.merchant ?? ''}</Text>
          </View>
          <Text style={s.strong}>{money(o.finalAmount)}</Text>
        </View>
      )) : (
        <View style={s.empty}><Text style={s.note}>No orders yet. Ask Glance to buy something and it shows up here.</Text></View>
      )}
      <ErrorBox err={err} />
    </>);
    foot = <Btn title="Ask Glance to buy something" onPress={() => go('ask')} />;
  }

  if (scr === 'ask') {
    const lines = ['Reading your request', 'Searching merchants', 'Checking live prices'];
    body = (<>
      <Back to="home" label="Home" go={go} />
      <Text style={s.h}>What should I buy?</Text>
      <TextInput style={s.textarea} multiline value={text} onChangeText={setText} editable={!busy} accessibilityLabel="Your request" />
      {busy > 0 && lines.map((l, i) => {
        const done = i < busy - 1, now = i === busy - 1;
        return (
          <View key={l} style={s.stepRow}>
            {now ? <ActivityIndicator size="small" color={C.accent} style={{ width: 16, height: 16 }} />
              : <View style={[s.stepDot, done && { backgroundColor: C.ok, borderColor: C.ok }]} />}
            <Text style={{ fontSize: 14, color: done || now ? C.ink : C.muted }}>{l}</Text>
          </View>
        );
      })}
      <ErrorBox err={err} />
    </>);
    foot = <Btn title={busy ? 'Working…' : 'Find it'} disabled={!!busy || !text.trim()} onPress={find} />;
  }

  if (scr === 'results') {
    body = (<>
      <Back to="ask" label="Ask" go={go} />
      <Text style={s.h}>{products.length ? `${products.length} match${products.length > 1 ? 'es' : ''} found` : 'No matches'}</Text>
      <Text style={s.sub}>From merchant catalogs via Reap. Prices before shipping and tax.</Text>
      {products.map((p, i) => {
        const on = p.id === pick;
        return (
          <Pressable key={p.id} onPress={() => setPick(p.id)} style={[s.opt, on && s.optOn]} accessibilityRole="radio" accessibilityState={{ checked: on }}>
            <Radio on={on} />
            {p.imageUrl ? <Image source={{ uri: p.imageUrl }} style={s.thumb} resizeMode="contain" /> : null}
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={s.nm} numberOfLines={2}>{p.name}</Text>
              <Text style={s.small}>{p.merchant}</Text>
              {p.id === agentPick ? <Text style={s.pill}>Agent's pick</Text> : null}
            </View>
            <Text style={s.pr}>{money(p.price)}</Text>
          </Pressable>
        );
      })}
      {!products.length && <Text style={s.note}>Try a different product or a higher limit.</Text>}
      <ErrorBox err={err} />
    </>);
    foot = <Btn title="Get the full price" disabled={!product} onPress={() => { setQuote(null); go('quote'); }} />;
  }

  useEffect(() => { if (scr === 'quote' && !quote && product && !quoting) getQuote(); }, [scr]); // eslint-disable-line

  if (scr === 'quote') {
    const q = quote;
    const over = !!q && q.overLimit;
    const total = q?.total ?? 0;
    const pct = q ? Math.min(100, (total / q.limit) * 100) : 0;
    body = (<>
      <Back to="results" label="Results" go={go} />
      {toast ? <View style={s.toast}><Text style={s.toastText}>{toast}</Text></View> : null}
      <Text style={s.h}>{product?.name}</Text>
      <Text style={s.sub}>{product?.merchant}</Text>
      {!q && quoting && <View style={{ padding: 24 }}><ActivityIndicator color={C.accent} /><Text style={[s.note, { textAlign: 'center', marginTop: 8 }]}>Getting the merchant's live price…</Text></View>}
      {q && (<>
        {over && <View style={s.alert}><Text style={s.alertText}>{money(q.overBy)} over your limit. Glance will not check out. Pick cheaper shipping or raise the limit.</Text></View>}
        {q.shippingOptions.length > 0 && <Text style={s.k}>Shipping</Text>}
        {q.shippingOptions.map((o) => (
          <Pressable key={o.id} style={[s.opt, o.selected && s.optOn]} disabled={quoting}
            onPress={() => !o.selected && getQuote(o.id)} accessibilityRole="radio" accessibilityState={{ checked: o.selected }}>
            <Radio on={o.selected} />
            <View style={{ flex: 1 }}><Text style={s.nm}>{o.name}</Text></View>
            <Text style={s.pr}>{money(o.price)}</Text>
          </Pressable>
        ))}
        <View style={s.lines}>
          <View style={s.line}><Text style={s.lineText}>Item</Text><Text style={s.lineText}>{money(q.subtotal)}</Text></View>
          <View style={s.line}><Text style={s.lineText}>Shipping</Text><Text style={s.lineText}>{money(q.shipping)}</Text></View>
          <View style={s.line}><Text style={s.lineText}>Tax</Text><Text style={s.lineText}>{money(q.tax)}</Text></View>
          {q.discounts ? <View style={s.line}><Text style={s.lineText}>Discounts</Text><Text style={s.lineText}>-{money(q.discounts)}</Text></View> : null}
          <View style={[s.line, { borderBottomWidth: 0 }]}><Text style={s.lineTotal}>Total</Text><Text style={s.lineTotal}>{money(q.total)}</Text></View>
        </View>
        <View style={{ gap: 6 }}>
          <View style={s.track}><View style={[s.fill, { width: `${pct}%` }, over && { backgroundColor: C.stop }]} /></View>
          <View style={s.mrow}>
            <Text style={s.small}>{over ? `${money(q.overBy)} over your limit` : `${money(q.limit - total)} under your limit`}</Text>
            <Text style={s.small}>Limit {money(q.limit)}</Text>
          </View>
        </View>
        {q.expiresAt && !over ? <Text style={s.note}>Price held by the merchant until {new Date(q.expiresAt).toLocaleTimeString()}.</Text> : null}
      </>)}
      <ErrorBox err={err} />
    </>);
    foot = (<>
      <Btn title={paying ? 'Starting checkout…' : `Review and pay ${q ? money(q.total) : ''}`} disabled={!q || over || quoting || paying} onPress={pay} />
      {over && <Btn ghost title="Change limit" onPress={() => go('limit')} />}
    </>);
  }

  if (scr === 'approve' && checkout?.url) {
    return (
      <SafeAreaView style={[s.screen, { backgroundColor: C.hosted }]}>
        <StatusBar style="dark" />
        <Approve url={checkout.url} returnPrefix={`${API_URL}/done`} onReturn={() => confirm()} onCancel={() => { setToast('Payment not approved. Nothing was charged.'); go('quote'); }} busy={paying} />
      </SafeAreaView>
    );
  }

  if (scr === 'paid' && paid) {
    const before = paid.vaultBefore ?? home?.vaultBalance ?? null;
    const after = paid.vaultSource === 'kwal' ? paid.vaultAfter : before != null && paid.finalAmount != null ? before - paid.finalAmount : null;
    body = (<>
      <View style={s.doneMark}><Text style={{ color: C.ok, fontSize: 30, fontWeight: '700' }}>✓</Text></View>
      <Text style={[s.h, { textAlign: 'center' }]}>Paid {money(paid.finalAmount)}</Text>
      <Text style={[s.sub, { textAlign: 'center' }]}>From your USDC vault</Text>
      <View style={s.lines}>
        <View style={s.line}><Text style={s.lineText}>Order</Text><Text style={s.lineText} numberOfLines={1}>{paid.orderId ?? '—'}</Text></View>
        <View style={s.line}><Text style={s.lineText}>Item</Text><Text style={[s.lineText, { flex: 1, textAlign: 'right', marginLeft: 12 }]} numberOfLines={1}>{product?.name}</Text></View>
        <View style={s.line}><Text style={s.lineText}>Merchant</Text><Text style={s.lineText}>{product?.merchant}</Text></View>
        <View style={[s.line, { borderBottomWidth: 0 }]}><Text style={s.lineTotal}>Vault balance</Text><Text style={s.lineTotal}>{usdc(after)} USDC</Text></View>
      </View>
      <Text style={s.note}>Sandbox: the checkout is simulated and nothing ships.</Text>
    </>);
    foot = <Btn title="Done" onPress={() => { setQuote(null); setPaid(null); setCheckout(null); go('home'); }} />;
  }

  if (scr === 'limit') {
    body = (<>
      <Back to="home" label="Home" go={go} />
      <Text style={s.h}>Spending limit</Text>
      <Text style={s.sub}>The most Glance can spend on one purchase, shipping and tax included.</Text>
      <Text style={s.bigval}>${limit}</Text>
      <Slider minimumValue={50} maximumValue={300} step={10} value={limit} onValueChange={setLimit}
        minimumTrackTintColor={C.accent} maximumTrackTintColor={C.line} thumbTintColor={C.accent} accessibilityLabel="Per-purchase limit in dollars" />
      <View style={s.mrow}><Text style={s.small}>$50</Text><Text style={s.small}>$300</Text></View>
      <Text style={s.note}>Above this, Glance stops and tells you why. You always approve the charge yourself as well.</Text>
      <ErrorBox err={err} />
    </>);
    foot = <Btn title="Save limit" onPress={async () => {
      try { await api.setLimit(limit); setQuote(null); go(quote ? 'quote' : 'home'); } catch (e) { setErr(e); }
    }} />;
  }

  return (
    <SafeAreaView style={s.screen}>
      <StatusBar style="dark" />
      <View style={{ flex: 1, width: '100%', maxWidth: 480, alignSelf: 'center', backgroundColor: C.bg }}>
        {sbar}
        <ScrollView contentContainerStyle={s.view} keyboardShouldPersistTaps="handled">{body}</ScrollView>
        {foot && <View style={s.foot}>{foot}</View>}
      </View>
    </SafeAreaView>
  );
}
