import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api, Post } from '../../lib/api';
import { useSession } from '../../lib/session';
import { Screen, Button, s, color } from '../../lib/ui';

type Draft = { title: string; body: string; category: string };

const DRAFT_KEY = 'hp_draft';
const EMPTY_DRAFT: Draft = { title: '', body: '', category: '情绪树洞' };

export default function Compose() {
  const { config } = useSession();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [category, setCategory] = useState(EMPTY_DRAFT.category);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);

  const latestDraft = useRef<Draft>(EMPTY_DRAFT);
  const saveSerial = useRef(Promise.resolve());
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const readyRef = useRef(false);
  const busyRef = useRef(false);
  const skipAutoSave = useRef(false);

  const cancelPendingSave = useCallback(() => {
    if (saveTimer.current !== null) {
      clearTimeout(saveTimer.current);
      saveTimer.current = null;
    }
  }, []);

  const persistDraft = useCallback((draft: Draft) => {
    const operation = saveSerial.current
      .catch(() => undefined)
      .then(() => {
        if (draft.title || draft.body) {
          return AsyncStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
        }
        return AsyncStorage.removeItem(DRAFT_KEY);
      });
    saveSerial.current = operation.catch(() => undefined);
    return saveSerial.current;
  }, []);

  const flushDraft = useCallback(() => {
    cancelPendingSave();
    if (!readyRef.current || busyRef.current || skipAutoSave.current) return;
    void persistDraft(latestDraft.current);
  }, [cancelPendingSave, persistDraft]);

  useEffect(() => {
    if (readyRef.current) return;
    let active = true;
    AsyncStorage.getItem(DRAFT_KEY)
      .then((raw) => {
        if (!active || !raw) return;
        const stored = JSON.parse(raw) as Partial<Draft>;
        const next: Draft = {
          title: typeof stored.title === 'string' ? stored.title.slice(0, 80) : '',
          body: typeof stored.body === 'string' ? stored.body.slice(0, 3000) : '',
          category:
            typeof stored.category === 'string' && config?.categories.includes(stored.category)
              ? stored.category
              : EMPTY_DRAFT.category,
        };
        latestDraft.current = next;
        setTitle(next.title);
        setBody(next.body);
        setCategory(next.category);
      })
      .catch(() => {})
      .finally(() => {
        if (!active) return;
        readyRef.current = true;
        setReady(true);
      });
    return () => {
      active = false;
    };
  }, [config]);

  useEffect(() => {
    if (!ready || busy || skipAutoSave.current) return;
    cancelPendingSave();
    saveTimer.current = setTimeout(() => {
      saveTimer.current = null;
      void persistDraft(latestDraft.current);
    }, 400);
    return cancelPendingSave;
  }, [title, body, category, ready, busy, cancelPendingSave, persistDraft]);

  useFocusEffect(useCallback(() => flushDraft, [flushDraft]));

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextState) => {
      if (nextState !== 'active') flushDraft();
    });
    return () => subscription.remove();
  }, [flushDraft]);

  function updateTitle(value: string) {
    latestDraft.current = { ...latestDraft.current, title: value };
    skipAutoSave.current = false;
    setTitle(value);
  }

  function updateBody(value: string) {
    latestDraft.current = { ...latestDraft.current, body: value };
    skipAutoSave.current = false;
    setBody(value);
  }

  function updateCategory(value: string) {
    latestDraft.current = { ...latestDraft.current, category: value };
    skipAutoSave.current = false;
    setCategory(value);
  }

  async function publish() {
    busyRef.current = true;
    setBusy(true);
    setError('');
    try {
      await api<Post>('/posts', 'POST', { title, body, category });
      skipAutoSave.current = true;
      cancelPendingSave();
      latestDraft.current = { ...latestDraft.current, title: '', body: '' };
      setTitle('');
      setBody('');
      await persistDraft(latestDraft.current);
      router.replace({ pathname: '/', params: { view: 'mine' } });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  function clearDraft() {
    const next = { ...latestDraft.current, title: '', body: '' };
    latestDraft.current = next;
    skipAutoSave.current = false;
    cancelPendingSave();
    setTitle('');
    setBody('');
    void persistDraft(next);
  }

  return (
    <Screen>
      <Text style={s.title}>说点心里话。</Text>
      <Text style={s.muted}>正文会经过审核。草稿仅保存在本机，请勿留下联系方式。</Text>
      <ScrollView horizontal contentContainerStyle={{ gap: 8 }}>
        {(config?.categories || []).map((c) => (
          <Pressable
            key={c}
            style={[s.pill, c === category && s.pillOn]}
            onPress={() => updateCategory(c)}
          >
            <Text style={[s.pillText, c === category && { color: color.bg }]}>{c}</Text>
          </Pressable>
        ))}
      </ScrollView>
      <TextInput
        style={s.input}
        value={title}
        onChangeText={updateTitle}
        maxLength={80}
        placeholder="标题（2—80 字）"
        placeholderTextColor={color.muted}
      />
      <TextInput
        style={[s.input, { minHeight: 220, textAlignVertical: 'top' }]}
        multiline
        value={body}
        onChangeText={updateBody}
        maxLength={3000}
        placeholder="慢慢说，这里有人听。（5—3000 字）"
        placeholderTextColor={color.muted}
      />
      <Text style={s.muted}>{body.length} / 3000 · 本机草稿</Text>
      <View style={s.card}>
        <Text style={s.label}>让经验带着背景</Text>
        <Text style={s.muted}>可自愿补充发生时间、区域或行业、适用条件，区分亲历和转述。不要写详细住址、证件或手机号。</Text>
      </View>
      {!!error && <Text style={s.error}>{error}</Text>}
      <Button
        disabled={busy || title.trim().length < 2 || body.trim().length < 5}
        onPress={() => void publish()}
      >
        {busy ? '提交中…' : '匿名发布，等待审核'}
      </Button>
      <Button secondary onPress={clearDraft}>清空草稿</Button>
    </Screen>
  );
}
