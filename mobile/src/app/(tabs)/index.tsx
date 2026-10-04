import {useCallback,useRef,useState} from 'react';
import {View,Text,TextInput,FlatList,ScrollView,Pressable,RefreshControl} from 'react-native';
import {router,useFocusEffect,useLocalSearchParams} from 'expo-router';
import {api,Post,Page} from '../../lib/api';
import {useSession} from '../../lib/session';
import {Screen,Button,s,color,when} from '../../lib/ui';
const orders=[['latest','最新'],['hot','本周热门'],['unanswered','等待回应']];
const descriptions:Record<string,string>={latest:'按发布时间浏览，看看大家最近在聊什么。',hot:'过去七天内，按共鸣 + 回复 × 2 排序，最多展示 50 条。',unanswered:'还没有公开回复的讨论，给彼此一点回应。'};
export default function Feed(){
  const {config}=useSession(),params=useLocalSearchParams<{view?:string}>();
  const [posts,setPosts]=useState<Post[]>([]),[category,setCategory]=useState(''),[sort,setSort]=useState('latest');
  const [query,setQuery]=useState(''),[q,setQ]=useState(''),[cursor,setCursor]=useState<string|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const serial=useRef(0),lock=useRef(false),cursorRef=useRef<string|null>(null);
  const view=params.view||'all';
  const load=useCallback(async(more=false)=>{
    if(more&&(lock.current||!cursorRef.current))return;
    const ticket=++serial.current;lock.current=true;setBusy(true);setError('');
    if(!more){setPosts([]);setCursor(null);cursorRef.current=null;}
    try{
      const data=await api<Page<Post>>('/posts?'+new URLSearchParams({view,category,q,sort,limit:sort==='hot'?'50':'20',...(more&&cursorRef.current?{cursor:cursorRef.current}:{})}));
      if(ticket!==serial.current)return;
      setPosts(old=>more?[...old,...data.posts.filter(p=>!old.some(x=>x.id===p.id))]:data.posts);
      setCursor(data.next_cursor);cursorRef.current=data.next_cursor;
    }catch(e){if(ticket===serial.current)setError((e as Error).message);}
    finally{if(ticket===serial.current){lock.current=false;setBusy(false);}}
  },[view,category,q,sort]);
  useFocusEffect(useCallback(()=>{void load(false);return()=>{serial.current++;lock.current=false;};},[load]));
  return <Screen scroll={false}><FlatList data={posts} keyExtractor={p=>p.id} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled"
    refreshControl={<RefreshControl refreshing={busy} onRefresh={()=>void load()} tintColor={color.accent}/>}
    ListHeaderComponent={<View style={{gap:14}}>
      <View style={s.row}><Text style={s.title}>沪漂广场</Text><Pressable accessibilityRole="button" onPress={()=>router.push('/guide')}><Text style={{color:color.accent}}>新手指南 →</Text></Pressable></View>
      <Text style={s.muted}>分享生活、互相搭把手。每一句真诚的话，都值得被听见。</Text>
      <View style={s.card}><Text style={s.label}>社区公告 · 内测开放中</Text><Text style={s.muted}>帖子和回复审核后公开。请勿留下手机号、详细住址或他人隐私；遇到问题可举报或提交私密反馈。</Text><Pressable accessibilityRole="button" onPress={()=>router.push('/rules')}><Text style={{color:color.accent}}>查看社区约定与隐私说明 →</Text></Pressable></View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{gap:8}}>{[['all','广场'],['mine','我的帖子'],['liked','我共鸣过的'],['replied','我参与过的']].map(([v,label])=><Pressable accessibilityRole="button" accessibilityState={{selected:view===v}} key={v} style={[s.pill,view===v&&s.pillOn]} onPress={()=>{router.setParams({view:v});setCategory('');setSort('latest');}}><Text style={[s.pillText,view===v&&{color:color.bg}]}>{label}</Text></Pressable>)}</ScrollView>
      <View style={s.row}>{orders.map(([v,label])=><Pressable accessibilityRole="button" accessibilityState={{selected:sort===v}} key={v} style={[s.pill,sort===v&&s.pillOn]} onPress={()=>setSort(v)}><Text style={[s.pillText,sort===v&&{color:color.bg}]}>{label}</Text></Pressable>)}</View>
      <Text style={s.muted}>{descriptions[sort]}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{gap:8}}>{['',...(config?.categories||[])].map(c=><Pressable accessibilityRole="button" accessibilityState={{selected:category===c}} key={c} style={[s.pill,category===c&&s.pillOn]} onPress={()=>setCategory(c)}><Text style={[s.pillText,category===c&&{color:color.bg}]}>{c||'全部版块'}</Text></Pressable>)}</ScrollView>
      <TextInput style={s.input} value={query} onChangeText={setQuery} maxLength={100} placeholder="搜索讨论" accessibilityLabel="搜索讨论" placeholderTextColor={color.muted} returnKeyType="search" onSubmitEditing={()=>setQ(query.trim())}/>
      <View style={s.row}><Button secondary onPress={()=>setQ(query.trim())}>搜索</Button>{!!q&&<Button secondary onPress={()=>{setQ('');setQuery('');}}>清除搜索</Button>}</View>
      {!!error&&<View style={s.card}><Text style={s.error}>{error}</Text><Button secondary onPress={()=>void load()}>重新加载</Button></View>}
    </View>}
    renderItem={({item:p})=><Pressable accessibilityRole="button" accessibilityLabel={p.title} style={s.card} onPress={()=>router.push({pathname:'/post/[id]',params:{id:p.id}})}>
      <View style={s.row}><Text style={{color:color.accent,fontSize:13}}>{p.category}</Text><Text style={s.muted}>{p.author}{p.mine?' · 你':''}</Text></View>
      <Text style={[s.text,{fontWeight:'600',fontSize:18}]}>{p.title}</Text><Text style={s.muted} numberOfLines={3}>{p.body}</Text>
      <Text style={s.muted}>{p.status==='pending'?'待审核 · ':p.status==='hidden'?'已隐藏 · ':''}{when(p.created)}</Text>
      <View style={s.row}><Text style={s.muted}>♡ {p.likes} 共鸣</Text><Text style={s.muted}>↳ {p.replies} 回复</Text>{p.replies===0&&p.status==='active'&&<Text style={{color:color.accent,fontSize:13}}>等待第一份回应</Text>}</View>
    </Pressable>}
    ListEmptyComponent={!busy&&!error?<View style={s.card}><Text style={s.text}>{q||category?'没有符合筛选的讨论':sort==='unanswered'?'暂时没有等待回应的讨论':sort==='hot'?'本周还没有公开讨论':'这里还没有讨论'}</Text><Text style={s.muted}>可以换一个版块，或分享你的经历。自己的审核进度在“我的帖子”查看。</Text><Button onPress={()=>router.push('/compose')}>写下新讨论</Button></View>:null}
    ListFooterComponent={cursor?<Button secondary disabled={busy} onPress={()=>void load(true)}>{busy?'加载中…':'继续逛逛'}</Button>:posts.length?<Text style={s.muted}>{sort==='hot'?'本周热门已展示完，下拉可刷新榜单。':'已经逛到这里了。'}</Text>:null}/></Screen>;
}
