import {createContext,useCallback,useContext,useEffect,useState,ReactNode} from 'react';
import {api,restore,saveToken,forget,ApiError,Config} from './api';
const Session=createContext({ready:false,signedIn:false,config:null as Config|null,error:'',refresh:async()=>{},join:async()=>{},remove:async()=>{}});
export function SessionProvider({children}:{children:ReactNode}){const [ready,setReady]=useState(false),[signedIn,setSignedIn]=useState(false),[config,setConfig]=useState<Config|null>(null),[error,setError]=useState('');
const refresh=useCallback(async()=>{try{const t=await restore();setError('');setSignedIn(!!t);const c=await api<Config>('/config','GET',undefined,90000);setConfig(c);if(t){try{await api('/me');}catch(e){if(e instanceof ApiError&&e.status===401){await forget();setSignedIn(false);}else throw e;}}}catch(e){setError((e as Error).message);}finally{setReady(true);}},[]);
useEffect(()=>{let active=true; Promise.resolve().then(()=>{if(active)void refresh();});return()=>{active=false;};},[refresh]);
async function join(){if(!config)throw Error('请先连接后端并加载社区约定');const data=await api<{token:string}>('/session','POST',{accepted_terms:config.terms_version});await saveToken(data.token);setSignedIn(true);}
async function remove(){await api('/me','DELETE');await forget();setSignedIn(false);}
return <Session.Provider value={{ready,signedIn,config,error,refresh,join,remove}}>{children}</Session.Provider>}
export const useSession=()=>useContext(Session);
