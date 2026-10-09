import { useRef } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { WebView } from 'react-native-webview';
import { C, s } from './theme';

type Props = { url: string; returnPrefix: string; onReturn: () => void; onCancel: () => void; busy: boolean };

export default function Approve({ url, returnPrefix, onReturn, onCancel, busy }: Props) {
  const fired = useRef(false);
  const hit = (u: string) => {
    if (!fired.current && (u.startsWith(returnPrefix) || u.startsWith('glance://'))) {
      fired.current = true;
      onReturn();
      return true;
    }
    return false;
  };
  return (
    <View style={{ flex: 1 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <Text style={[s.url, { flex: 1 }]} numberOfLines={1}>🔒 {url.replace(/^https?:\/\//, '')}</Text>
        <Pressable onPress={onCancel} style={{ marginTop: 8, marginRight: 12 }}><Text style={s.link}>Cancel</Text></Pressable>
      </View>
      {busy ? (
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 }}>
          <ActivityIndicator color={C.accent} /><Text style={s.note}>Confirming your payment…</Text>
        </View>
      ) : (
        <WebView
          source={{ uri: url }}
          style={{ flex: 1, marginTop: 8, backgroundColor: C.hosted }}
          onShouldStartLoadWithRequest={(r) => !hit(r.url)}
          onNavigationStateChange={(n) => hit(n.url)}
          startInLoadingState
        />
      )}
    </View>
  );
}
