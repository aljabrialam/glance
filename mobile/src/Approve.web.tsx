import { useEffect, useRef } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { C, s } from './theme';

type Props = { url: string; returnPrefix: string; onReturn: () => void; onCancel: () => void; busy: boolean };

// Web preview: Reap's hosted page is opened in a popup; the backend /done page posts back when approval finishes.
export default function Approve({ url, onReturn, onCancel, busy }: Props) {
  const win = useRef<Window | null>(null);
  const fired = useRef(false);
  const fire = () => { if (!fired.current) { fired.current = true; onReturn(); } };
  useEffect(() => {
    win.current = window.open(url, 'reap-approval', 'width=480,height=760');
    const onMsg = (e: MessageEvent) => { if (e.data?.glance === 'done') { win.current?.close(); fire(); } };
    window.addEventListener('message', onMsg);
    const iv = setInterval(() => { if (win.current?.closed) { clearInterval(iv); fire(); } }, 800);
    return () => { window.removeEventListener('message', onMsg); clearInterval(iv); };
  }, [url]); // eslint-disable-line
  return (
    <View style={{ flex: 1, width: '100%', maxWidth: 480, alignSelf: 'center' }}>
      <Text style={s.url} numberOfLines={1}>🔒 {url.replace(/^https?:\/\//, '')}</Text>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 14, padding: 24 }}>
        <ActivityIndicator color={C.accent} />
        <Text style={[s.h, { fontSize: 20, textAlign: 'center' }]}>{busy ? 'Confirming your payment…' : 'Approve on Reap’s secure page'}</Text>
        <Text style={[s.note, { textAlign: 'center' }]}>Card details never reach Glance or the agent.</Text>
        {!busy && <Pressable onPress={() => window.open(url, 'reap-approval', 'width=480,height=760')}><Text style={s.link}>Reopen approval page</Text></Pressable>}
        {!busy && <Pressable onPress={fire}><Text style={s.link}>I’ve approved it</Text></Pressable>}
        {!busy && <Pressable onPress={onCancel}><Text style={[s.link, { color: C.muted }]}>Cancel</Text></Pressable>}
      </View>
    </View>
  );
}
