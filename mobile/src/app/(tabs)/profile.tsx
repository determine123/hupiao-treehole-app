import { appVersion } from '../../lib/version';
import { useCallback, useState } from 'react';
import { Alert, Linking, Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import * as Updates from 'expo-updates';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '../../lib/api';
import { useSession } from '../../lib/session';
import { Button, Screen, s, when } from '../../lib/ui';

type Block = { id: string; created: number };

export default function Profile() {
  const session = useSession();
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);

  const load = useCallback(async () => {
    try {
      setBlocks(await api<Block[]>('/blocks'));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  async function checkForUpdates() {
    if (!Updates.isEnabled) {
      Alert.alert('暂不可检查更新', '当前安装包尚未启用应用内更新。请安装包含 EAS Update 配置的新版本。');
      return;
    }

    setCheckingUpdate(true);
    try {
      const result = await Updates.checkForUpdateAsync();
      if (!result.isAvailable) {
        Alert.alert('已是最新版本', '当前没有可用的应用内更新。');
        return;
      }

      Alert.alert('发现新版本', '下载完成后可立即重启应用，也可以稍后重新打开应用时应用更新。', [
        { text: '暂不更新', style: 'cancel' },
        {
          text: '下载并重启',
          onPress: () => {
            setCheckingUpdate(true);
            void Updates.fetchUpdateAsync()
              .then((download) => {
                if (!download.isNew) {
                  Alert.alert('更新未下载', '服务器没有返回新的兼容版本。');
                  return;
                }
                return Updates.reloadAsync();
              })
              .catch((e: unknown) => {
                Alert.alert('更新失败', (e as Error).message || '请检查网络后重试。');
              })
              .finally(() => setCheckingUpdate(false));
          },
        },
      ]);
    } catch (e) {
      Alert.alert('检查失败', (e as Error).message || '请检查网络后重试。');
    } finally {
      setCheckingUpdate(false);
    }
  }

  function remove() {
    Alert.alert('删除匿名身份和内容？', '你的帖子、回复、共鸣、举报及反馈会从在线数据库删除，凭据被注销。这无法恢复，备份将在保留期结束后清除。', [
      { text: '取消', style: 'cancel' },
      {
        text: '永久删除',
        style: 'destructive',
        onPress: () => {
          setBusy(true);
          session.remove()
            .then(async () => {
              await AsyncStorage.removeItem('hp_draft');
              router.replace('/welcome');
            })
            .catch((e) => setError(e.message))
            .finally(() => setBusy(false));
        },
      },
    ]);
  }

  return (
    <Screen>
      <Text style={s.title}>此刻的你。</Text>
      <Text style={s.muted}>匿名标识按讨论生成。凭据保存在本机安全存储中，没有跨设备恢复功能。</Text>
      <Button secondary onPress={() => router.push({ pathname: '/', params: { view: 'mine' } })}>我的帖子与审核状态</Button>
      <Button secondary onPress={() => router.push('/moderation')}>我的审核记录与说明</Button>
      <Button secondary onPress={() => router.push('/rules')}>社区约定与隐私说明</Button>
      {!!session.config?.support_email && <Button secondary onPress={() => void Linking.openURL(`mailto:${session.config?.support_email}`).catch(() => setError('无法打开邮件应用'))}>联系支持与违规处理</Button>}

      <Text style={s.label}>屏蔽管理</Text>
      {blocks.map((block) => (
        <View style={s.card} key={block.id}>
          <Text style={s.muted}>屏蔽记录 · {when(block.created)}</Text>
          <Button secondary onPress={() => { void api(`/blocks/${block.id}`, 'DELETE').then(load).catch((e) => setError(e.message)); }}>解除屏蔽</Button>
        </View>
      ))}
      {!blocks.length && <Text style={s.muted}>目前没有屏蔽记录。</Text>}
      {!!error && <Text style={s.error}>{error}</Text>}

      <Text style={s.label}>应用更新</Text>
      <Text style={s.muted}>联网检查兼容更新。通过应用商店或安装包升级时仍需安装新版本。</Text>
      <Button secondary disabled={checkingUpdate} onPress={() => void checkForUpdates()}>{checkingUpdate ? '正在检查…' : '检查应用更新'}</Button>

      <Button secondary disabled={busy} onPress={remove}>{busy ? '正在删除…' : '删除匿名身份及所有内容'}</Button>
      <Text style={s.muted}>沪漂树洞 {appVersion} · 内测版本</Text>
    </Screen>
  );
}
