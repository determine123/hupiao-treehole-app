import {useCallback,useRef,useState} from 'react';
import {FlatList,Text,View,RefreshControl} from 'react-native';
import {Redirect,router,useFocusEffect} from 'expo-router';
import {api} from '../lib/api';
import {useSession} from '../lib/session';
import {Screen,Button,s,color,when,Loading} from '../lib/ui';
type Record={id:string;target_id:string;target_type:string;decision:string;reason:string;created:number;title:string;preview:string};
type Result={records:Record[];next_cursor:string|null};
export default function Moderation(){
 const session=useSession();const [rows,setRows]=useState<Record[]>([]),[cursor,setCursor]=useState<string|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const serial=useRef(0),lock=useRef(false),next=useRef<string|null>(null);
 const load=useCallback(async(more=false)=>{
  if(more&&(lock.current||!next.current))return;
  const ticket=++serial.current;lock.current=true;setBusy(true);setError('');
  try{const data=await api<Result>('/moderation'+(more&&next.current?'?cursor='+encodeURIComponent(next.current):''));if(ticket!==serial.current)return;setRows(old=>more?[...old,...data.records.filter(r=>!old.some(x=>x.id===r.id))]:data.records);next.current=data.next_cursor;setCursor(data.next_cursor);}
  catch(e){if(ticket===serial.current)setError((e as Error).message);}
  finally{if(ticket===serial.current){setBusy(false);lock.current=false;}}
 },[]);
 useFocusEffect(useCallback(()=>{if(session.ready&&session.signedIn)void load();return()=>{serial.current++;lock.current=false;};},[load,session.ready,session.signedIn]));
 if(!session.ready)return <Loading/>;
 if(!session.signedIn)return <Redirect href="/welcome"/>;
 return <Screen scroll={false}><FlatList data={rows} keyExtractor={r=>r.id} contentContainerStyle={s.content} refreshControl={<RefreshControl refreshing={busy} onRefresh={()=>void load()} tintColor={color.accent}/>}
 ListHeaderComponent={<View style={{gap:10}}><Text style={s.title}>我的审核记录</Text><Text style={s.muted}>只展示你的帖子与回复。说明由管理员明确填写；内部备注和举报信息不会公开。内容删除后不再展示对应记录。</Text>{!!error&&<View style={s.card}><Text style={s.error}>{error}</Text><Button secondary onPress={()=>void load()}>重新加载</Button></View>}</View>}
 renderItem={({item:r})=><View style={s.card}><Text style={s.muted}>{r.target_type==='comment'?'回复':'帖子'} · {r.decision==='hide'?'已隐藏':'已通过'} · {when(r.created)}</Text><Text style={s.label}>{r.title}</Text><Text style={s.muted}>{r.preview}</Text><Text style={s.text}>{r.reason||'管理员未填写给作者的说明。'}</Text>{r.target_type==='post'&&<Button secondary onPress={()=>router.push({pathname:'/post/[id]',params:{id:r.target_id}})}>查看我的帖子</Button>}</View>}
 ListEmptyComponent={!busy&&!error?<View style={s.card}><Text style={s.text}>还没有审核记录</Text><Text style={s.muted}>待审核内容可以在“我的帖子”查看；有处理结果后会显示在这里。</Text></View>:null}
 ListFooterComponent={cursor?<Button secondary disabled={busy} onPress={()=>void load(true)}>加载更多记录</Button>:rows.length?<Text style={s.muted}>当前审核记录已展示完。</Text>:null}/></Screen>;
}
