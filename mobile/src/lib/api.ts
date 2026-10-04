import * as SecureStore from 'expo-secure-store';
export const API=(process.env.EXPO_PUBLIC_API_URL||'http://127.0.0.1:8000').replace(/\/$/,'');
let token='';
export async function restore(){token=await SecureStore.getItemAsync('hp_mobile_token')||'';return token;}
export async function saveToken(value:string){await SecureStore.setItemAsync('hp_mobile_token',value);token=value;}
export async function forget(){await SecureStore.deleteItemAsync('hp_mobile_token');token='';}
export class ApiError extends Error {constructor(public status:number,message:string){super(message);}}
export async function api<T=unknown>(path:string,method='GET',body?:unknown,timeoutMs=15000):Promise<T>{const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeoutMs);try{const response=await fetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body!==undefined?JSON.stringify(body):undefined,signal:controller.signal});const data=await response.json();if(!response.ok){const message=typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((x:{msg:string})=>x.msg).join('；'):'请求失败，请稍后重试';throw new ApiError(response.status,message);}return data;}catch(e){if(e instanceof ApiError)throw e;if((e as Error).name==='AbortError')throw Error('连接超时，请检查网络后重试');throw Error('无法连接服务器，请检查网络和后端地址');}finally{clearTimeout(timer);}}
export type Post={id:string;title:string;body:string;category:string;created:number;status:string;likes:number;replies:number;liked:boolean;mine:boolean;author:string};
export type Reply={id:string;body:string;created:number;status:string;mine:boolean;isOp:boolean;author:string};
export type Page<T>={posts:T[];next_cursor:string|null};
export type Feedback={id:string;kind:string;body:string;status:string;response:string;created:number};
export type Config={terms_version:string;categories:string[];support_email:string;moderation:string;version:string};
