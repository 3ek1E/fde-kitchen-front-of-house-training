const $ = id => document.getElementById(id);
let me;
const labels = {orders:'出品与交接',wiki:'团队知识 Wiki',chat:'从知识中找到依据',admin:'管理与审计'};
function element(tag, text, className) { const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el; }
function action(text, fn) {const b=element('button',text);b.type='button';b.onclick=()=>run(fn);return b;}
function note(text) {$('status').textContent=text;}
async function api(path, method='GET', data) {
 const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-Requested-With':'kitchen'},body:data===undefined?undefined:JSON.stringify(data)});
 const value=await r.json();if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:'请检查输入内容');return value;
}
async function run(fn) {note('');try {await fn();}catch(e){note(e.message);}}
async function view(name) {
 ['login',...Object.keys(labels)].forEach(k=>$(k).hidden=k!==name);$('heading').textContent=labels[name]||'让每次交接都有依据';
 document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));
 if(name==='orders')await loadOrders();if(name==='wiki')await loadWiki();if(name==='admin')await loadAdmin();
}
async function initialize() {
 try {me=await api('/auth/me');}catch{me=null;}
 $('nav').hidden=!me;$('logout').hidden=!me;
 if(!me){await view('login');return;}
 $('who').textContent=`${me.email} · ${me.role}`;
 $('tenant-admin').hidden=me.role!=='platform_admin';$('tenant-field').hidden=me.role!=='platform_admin';
 $('role-options').replaceChildren(...(me.role==='platform_admin'?['tenant_admin']:['editor','member']).map(r=>{const o=element('option',r);o.value=r;return o;}));
 const canEdit=['tenant_admin','editor'].includes(me.role);
 ['save-page','publish-page','new-page'].forEach(id=>$(id).hidden=!canEdit);
 $('page-title').readOnly=!canEdit;$('page-content').readOnly=!canEdit;
 await view(me.role==='platform_admin'?'admin':'orders');
}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>run(()=>view(b.dataset.view)));
$('login-form').onsubmit=e=>{e.preventDefault();run(async()=>{await api('/auth/login','POST',Object.fromEntries(new FormData(e.target)));await initialize();});};
$('logout').onclick=()=>run(async()=>{await api('/auth/logout','POST',{});await initialize();});
async function loadOrders(){
 const data=await api('/orders');$('order-list').replaceChildren();$('event-list').replaceChildren();
 for(const o of data.orders){const d=element('div',undefined,'item');d.append(element('strong',`${o.order_no} / ${o.line_no} · v${o.version} · ${o.state}`),element('p',o.remark),element('small',o.updated_at));
 if(me.station==='kitchen')d.append(action('登记出品',async()=>{await api(`/orders/${o.id}/status`,'POST',{state:'已出品'});await loadOrders();}));
 if(me.station==='front')d.append(action('登记送达',async()=>{await api(`/orders/${o.id}/status`,'POST',{state:'已送达'});await loadOrders();}));$('order-list').append(d);}
 if(!data.orders.length)$('order-list').append(element('p','还没有订单，先登记一条演示事件。','empty'));
 for(const ev of data.events){const d=element('div',undefined,'item');d.append(element('strong',`${ev.event_id} · ${ev.source} · ${ev.outcome}`),element('p',`${ev.order_no}/${ev.line_no} v${ev.version} · ${ev.remark}`),element('small',`前厅 ${ev.front_ack?'已确认':'待确认'} / 后厨 ${ev.kitchen_ack?'已确认':'待确认'}`));
 if(['front','kitchen'].includes(me.station)&&ev.outcome==='applied')d.append(action('确认已接收',async()=>{await api(`/events/${ev.id}/ack`,'POST',{});await loadOrders();}));
 if(['editor','tenant_admin'].includes(me.role)&&ev.outcome==='conflict')d.append(action('核对后采用此事件',async()=>{await api(`/events/${ev.id}/resolve`,'POST',{});await loadOrders();}));$('event-list').append(d);}
}
$('event-form').onsubmit=e=>{e.preventDefault();run(async()=>{const d=Object.fromEntries(new FormData(e.target));d.version=Number(d.version);const v=await api('/events','POST',d);note(`事件处理结果：${v.outcome}`);await loadOrders();});};
async function loadWiki(){const pages=await api('/wiki');$('wiki-list').replaceChildren(...pages.map(p=>{const d=element('div',undefined,'item');d.append(action(p.title,async()=>{const r=await api(`/wiki/${p.id}`);$('page-id').value=p.id;$('page-title').value=r.title;$('page-content').value=r.content;$('revision').textContent=`当前修订 v${r.version} · ${r.published_id?'已有发布版本':'草稿'}`;}));return d;}));}
$('new-page').onclick=()=>{$('wiki-form').reset();$('revision').textContent='新建草稿';};
$('wiki-form').onsubmit=e=>{e.preventDefault();run(async()=>{const id=$('page-id').value;const r=await api(id?`/wiki/${id}`:'/wiki',id?'PUT':'POST',{title:$('page-title').value,content:$('page-content').value});if(!id)$('page-id').value=r.id;note('修订已保存，发布后可用于问答。');await loadWiki();});};
$('publish-page').onclick=()=>run(async()=>{const id=$('page-id').value;if(!id)throw Error('请先保存草稿');await api(`/wiki/${id}/publish`,'POST',{});note('发布成功，检索将使用当前版本。');await loadWiki();});
$('chat-form').onsubmit=e=>{e.preventDefault();run(async()=>{const b=e.target.querySelector('button');b.disabled=true;try {const r=await api('/chat','POST',Object.fromEntries(new FormData(e.target)));$('answer').textContent=r.notice+'\n\n'+r.answer;$('sources').replaceChildren(...r.sources.map((s,i)=>action(`[${i+1}] ${s.title}`,async()=>{const result=await fetch(s.url);if(!result.ok)throw Error('来源已更新或无权访问');const doc=await result.json();$('sources').append(element('pre',`${doc.title} · v${doc.version}\n${doc.content}`));})));}finally{b.disabled=false;}});};
async function loadAdmin(){
 if(!['platform_admin','tenant_admin'].includes(me.role))throw Error('请使用管理员账号');
 const users=await api('/users');$('user-list').replaceChildren(...users.map(u=>{const d=element('div',`${u.email} · ${u.role} · ${u.enabled?'启用':'停用'}`,'item');if(me.role==='tenant_admin'&&u.role!=='tenant_admin')d.append(action(u.enabled?'停用':'启用',async()=>{await api(`/users/${u.id}`,'PATCH',{enabled:!u.enabled});await loadAdmin();}));return d;}));
 if(me.role==='platform_admin'){const tenants=await api('/platform/tenants');$('tenant-list').replaceChildren(...tenants.map(t=>{const d=element('div',`#${t.id} ${t.name}`,'item');d.append(action(t.enabled?'停用租户':'启用租户',async()=>{await api(`/platform/tenants/${t.id}`,'PATCH',{enabled:!t.enabled});await loadAdmin();}));return d;}));$('audit-list').textContent='请使用租户管理员账号查看租户操作记录。';}
 else {const rows=await api('/audit');$('audit-list').replaceChildren(...rows.map(r=>element('div',`${r.created_at} · ${r.actor}\n${r.action} · ${r.target}`,'item')));}
}
$('tenant-form').onsubmit=e=>{e.preventDefault();run(async()=>{await api('/platform/tenants','POST',Object.fromEntries(new FormData(e.target)));e.target.reset();await loadAdmin();});};
$('user-form').onsubmit=e=>{e.preventDefault();run(async()=>{const d=Object.fromEntries(new FormData(e.target));d.tenant_id=d.tenant_id?Number(d.tenant_id):null;await api('/users','POST',d);e.target.reset();note('用户已创建');await loadAdmin();});};
initialize().catch(e=>note(e.message));
