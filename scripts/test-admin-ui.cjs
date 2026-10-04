// Execute the real inline admin script against controlled, delayed network responses.
const {readFileSync}=require('node:fs');
const {resolve}=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
class Element {
 constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.textContent='';this.classList={toggle(){}};this.listeners={};}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 setAttribute(){}
 addEventListener(name,fn){this.listeners[name]=fn;}
 querySelectorAll(tag){return this.children.flatMap(c=>[...(c.tag===tag?[c]:[]),...c.querySelectorAll(tag)]);}
}
const elements=Object.fromEntries(['key','logout','list','message','filter','filter-wrap','audit-target','audit-wrap','audit-more','audit-find'].map(id=>[id,new Element()]));
elements.key.value='test-only-admin-key';elements.filter.value='all';
const navigation=['queue','reports','feedback'].map(kind=>{const button=new Element('button');button.dataset.kind=kind;return button;});
const pending=[];
const context=vm.createContext({document:{querySelector:s=>elements[s.slice(1)],querySelectorAll:()=>navigation,createElement:tag=>new Element(tag)},AbortController,URLSearchParams,setTimeout,clearTimeout,console,confirm:()=>true,fetch:(url,options)=>new Promise(resolve=>pending.push({url,options,resolve}))});
const html=readFileSync(resolve(__dirname,'../backend/app/admin.html'),'utf8');
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const finish=(request,data)=>request.resolve({ok:true,status:200,json:async()=>data});
async function run(){
 const old=context.load('queue');assert.equal(pending.length,1);
 elements.logout.onclick();assert.equal(pending[0].options.signal.aborted,true);
 finish(pending[0],[{id:'secret',type:'post',title:'Private pending content',body:'Must stay invisible'}]);
 await old;assert.equal(elements.list.children.length,0);assert.equal(elements.key.value,'');assert.match(elements.message.textContent,/已退出/);
 elements.key.value='test-only-admin-key';
 const first=context.load('queue');const second=context.load('reports');
 finish(pending[2],[{id:'new',type:'post',target_id:'target',body:'Newest selected tab',reason:'Report'}]);
 await second;const current=elements.list.children[0];assert.ok(current);
 finish(pending[1],[{id:'old',type:'post',title:'Stale tab',body:'Old response'}]);
 await first;assert.equal(elements.list.children.length,1);assert.equal(elements.list.children[0],current);
 assert.match(current.children.map(c=>c.textContent).join(' '),/Newest selected tab/);
 elements['audit-target'].value='a'.repeat(36);
 const history=context.load('audit');
 assert.equal(new URL(pending[3].url,'https://example.test').searchParams.get('target'),'a'.repeat(36));
 finish(pending[3],{records:[{id:'audit-1',target_id:'a'.repeat(36),target_type:'post',decision:'hide',reason:'Author explanation',note:'Internal only',created:1}],next_cursor:'next-page'});
 await history;assert.equal(elements.list.children.length,1);assert.equal(elements['audit-more'].hidden,false);
 elements['audit-target'].value='b'.repeat(36); // Typing a new filter must not alter the active paginated search.
 const more=context.load('audit',true);
 assert.equal(new URL(pending[4].url,'https://example.test').searchParams.get('target'),'a'.repeat(36));
 finish(pending[4],{records:[{id:'audit-2',target_id:'a'.repeat(36),target_type:'post',decision:'approve',reason:'',note:'Reviewed',created:0}],next_cursor:null});
 await more;assert.equal(elements.list.children.length,2);assert.equal(elements['audit-more'].hidden,true);
 elements.logout.onclick();assert.equal(elements.list.children.length,0);
 console.log('Admin UI: logout cancels requests; late responses and stale tabs stay hidden.');
}
run().catch(error=>{console.error(error);process.exitCode=1;});
