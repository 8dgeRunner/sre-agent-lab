from __future__ import annotations


WEB_APP_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>SRE Agent 靶场</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
  <style>
    :root{--ink:#18201d;--muted:#68716d;--paper:#f5f4ee;--surface:#fffef9;--line:#d9d9d0;--accent:#d84b2a;--accent-dark:#a9341c;--green:#26734d;--amber:#9b6515;--blue:#1e5d88;--shadow:0 18px 50px rgba(31,39,35,.10)}
    *{box-sizing:border-box} body{margin:0;background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans",sans-serif;min-height:100vh}
    button,input,select,textarea{font:inherit} button{cursor:pointer}.mono{font-family:"JetBrains Mono",monospace}
    .shell{max-width:1180px;margin:0 auto;padding:28px}.topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:28px}
    .brand{display:flex;align-items:center;gap:12px;font-weight:700;letter-spacing:-.02em}.mark{width:34px;height:34px;background:var(--ink);color:#fff;display:grid;place-items:center;border-radius:5px;font-family:"JetBrains Mono"}.sub{color:var(--muted);font-size:13px}
    .panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow)}
    dialog{width:min(760px,calc(100% - 28px));max-height:88vh;padding:0;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);box-shadow:var(--shadow)}dialog::backdrop{background:rgba(24,32,29,.55)}.dialog-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:20px 22px;border-bottom:1px solid var(--line)}.dialog-head h2{font-size:20px;margin:0 0 4px}.dialog-body{padding:22px;overflow:auto}.dialog-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}.icon-btn{width:36px;height:36px;border:1px solid var(--line);border-radius:6px;background:#fff;font-size:20px;line-height:1}
    .login-wrap{min-height:72vh;display:grid;place-items:center}.login{width:min(430px,100%);padding:36px}.login h1{font-size:30px;margin:0 0 8px;letter-spacing:-.04em}.login p{margin:0 0 26px;color:var(--muted)}
    label{display:block;font-size:13px;font-weight:600;margin:16px 0 7px}.input{width:100%;border:1px solid var(--line);background:#fff;padding:11px 12px;border-radius:6px;outline:none}.input:focus{border-color:var(--ink);box-shadow:0 0 0 3px rgba(24,32,29,.08)}
    .primary{border:0;background:var(--accent);color:#fff;border-radius:6px;padding:11px 16px;font-weight:700}.primary:hover{background:var(--accent-dark)}.secondary{border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:6px;padding:10px 14px;font-weight:600}.danger{border:1px solid #e7b8ad;background:#fff;color:#a42c20;border-radius:6px;padding:7px 10px;font-weight:600}.ghost{border:0;background:transparent;color:var(--muted);padding:8px}
    .full{width:100%;margin-top:22px}.error{color:#a42c20;background:#fff0ec;border:1px solid #f1c3b8;padding:10px 12px;border-radius:6px;margin-top:14px;font-size:13px}.hidden{display:none!important}
    .workspace{display:grid;grid-template-columns:270px 1fr;gap:18px}.sidebar{padding:20px;height:max-content;position:sticky;top:18px}.sidebar h2{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}.case-card{border:1px solid var(--line);padding:13px;border-radius:7px;background:#fff;margin-bottom:12px}.case-card strong{display:block;margin-bottom:4px}.run-meta{font-size:12px;color:var(--muted);overflow-wrap:anywhere;margin-top:12px}.admin-panel{border-top:1px solid var(--line);margin-top:20px;padding-top:20px}.token-row{display:grid;grid-template-columns:minmax(150px,1fr) auto;gap:12px;font-size:13px;border-bottom:1px solid var(--line);padding:13px 0}.token-row:last-child{border-bottom:0}.token-meta{color:var(--muted);font-size:12px;line-height:1.6}.token-secret{word-break:break-all;background:#17201d;color:#f5f4ee;padding:12px;border-radius:6px;font-family:"JetBrains Mono";font-size:11px;margin-top:10px}.scope-list{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.scope{display:flex;align-items:center;gap:6px;font-size:12px;border:1px solid var(--line);background:#fff;padding:8px 10px;border-radius:6px}.chip{display:inline-block;background:#edf2ef;color:#385247;padding:2px 6px;border-radius:4px;margin:2px 4px 0 0;font-family:"JetBrains Mono";font-size:10px}.token-count{font-size:12px;color:var(--muted);margin-top:8px}
    .main{overflow:hidden}.hero{padding:25px 28px;border-bottom:1px solid var(--line);display:flex;align-items:flex-start;justify-content:space-between;gap:20px}.hero h1{font-size:26px;letter-spacing:-.035em;margin:0 0 6px}.status{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:700;color:var(--green);background:#eaf5ee;padding:6px 9px;border-radius:999px}.dot{width:7px;height:7px;border-radius:50%;background:currentColor}
    .steps{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--line)}.step{padding:14px 18px;border-right:1px solid var(--line);font-size:13px;color:var(--muted)}.step:last-child{border:0}.step.active{color:var(--ink);font-weight:700;box-shadow:inset 0 -3px var(--accent)}
    .content{padding:26px 28px}.empty{padding:70px 20px;text-align:center;color:var(--muted)}.empty strong{display:block;color:var(--ink);font-size:20px;margin-bottom:8px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.card{border:1px solid var(--line);border-radius:8px;background:#fff;padding:17px}.card h3{font-size:14px;margin:0 0 10px}.card p{font-size:13px;color:var(--muted);margin:5px 0}.wide{grid-column:1/-1}
    .toolbar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}.evidence{border-left:3px solid var(--blue);background:#f4f8fb;padding:11px 13px;margin:9px 0;font-size:13px;overflow-wrap:anywhere}.evidence small{color:var(--muted)}
    .form-row{display:grid;grid-template-columns:1fr 1fr;gap:14px}.score-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}.score{padding:16px;border:1px solid var(--line);background:#fff;border-radius:8px}.score b{font-size:24px;display:block}.score span{font-size:12px;color:var(--muted)}
    .notice{border-left:4px solid var(--amber);background:#fff9e9;padding:12px 14px;font-size:13px;margin-bottom:16px}.right{display:flex;gap:8px;align-items:center}.loading{opacity:.55;pointer-events:none}
    @media(max-width:800px){.shell{padding:14px}.workspace{grid-template-columns:1fr}.sidebar{position:static}.steps{grid-template-columns:1fr 1fr}.step:nth-child(2){border-right:0}.grid,.form-row,.score-grid{grid-template-columns:1fr}.hero{padding:20px}.content{padding:20px}}
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar"><div class="brand"><div class="mark">S/</div><div>SRE Agent 靶场<div class="sub">Dataset-backed outage practice</div></div></div><div id="userbar" class="right hidden"><span id="who" class="sub"></span><button class="ghost" onclick="logout()">退出</button></div></header>

    <section id="loginView" class="login-wrap">
      <form class="panel login" onsubmit="login(event)">
        <h1>进入故障演练</h1><p>登录后选择案例，像真实值班一样收集证据并提交诊断。</p>
        <label for="username">用户名</label><input id="username" class="input" autocomplete="username" required>
        <label for="password">密码</label><input id="password" class="input" type="password" autocomplete="current-password" required>
        <button class="primary full" type="submit">登录平台</button><div id="loginError" class="error hidden"></div>
      </form>
    </section>

    <section id="appView" class="workspace hidden">
      <aside class="panel sidebar">
        <h2>演练案例</h2><div id="caseList"></div>
        <button id="startBtn" class="primary full" onclick="startRun()">开始新演练</button>
        <div id="runMeta" class="run-meta">尚未创建 Run</div>
        <section id="adminPanel" class="admin-panel hidden">
          <h2>Agent 接入</h2>
          <button class="secondary full" onclick="openTokenManager()">管理接入 Token</button>
          <div id="tokenCount" class="token-count">正在读取...</div>
        </section>
      </aside>
      <main class="panel main">
        <div class="hero"><div><h1 id="pageTitle">选择一个故障案例</h1><div id="pageSub" class="sub">平台只向参与者展示任务和只读观测数据</div></div><div class="status"><i class="dot"></i><span id="statusText">平台在线</span></div></div>
        <nav class="steps"><div class="step active" data-step="0">1. 领取任务</div><div class="step" data-step="1">2. 收集证据</div><div class="step" data-step="2">3. 提交诊断</div><div class="step" data-step="3">4. 查看评分</div></nav>
        <div id="content" class="content"><div class="empty"><strong>准备好开始了吗？</strong>左侧选择案例，然后点击“开始新演练”。</div></div>
      </main>
    </section>

    <dialog id="tokenDialog" onclose="clearIssuedToken()">
      <div class="dialog-head"><div><h2>Agent 接入 Token</h2><div class="sub">每位同事、每个 Agent 独立签发；Token 不提供集群权限。</div></div><button class="icon-btn" aria-label="关闭" onclick="$('tokenDialog').close()">×</button></div>
      <div class="dialog-body">
        <section id="issueForm">
          <div class="form-row"><div><label for="tokenName">Agent 名称</label><input id="tokenName" class="input" placeholder="alice-sre-agent" maxlength="80"></div><div><label for="tokenOwner">使用人</label><input id="tokenOwner" class="input" placeholder="Alice / alice@example.com" maxlength="120"></div></div>
          <label for="tokenTtl">有效期</label><select id="tokenTtl" class="input"><option value="7">7 天（推荐）</option><option value="1">1 天</option><option value="30">30 天</option><option value="90">90 天</option></select>
          <label>最小权限</label><div class="scope-list"><label class="scope"><input type="checkbox" data-scope="run:create" checked> 创建演练</label><label class="scope"><input type="checkbox" data-scope="evidence:read" checked> 读取本次证据</label><label class="scope"><input type="checkbox" data-scope="answer:submit" checked> 提交答案</label></div>
          <div class="dialog-actions"><button class="primary" onclick="issueToken()">签发 Token</button></div>
        </section>
        <section id="tokenSecret" class="hidden">
          <div class="notice"><b>只显示一次</b><br>把下面两项私下交给对应同事；关闭后平台无法找回明文。</div>
          <label>Base URL</label><div id="issuedBaseUrl" class="token-secret"></div>
          <label>Bearer Token</label><div id="issuedToken" class="token-secret"></div>
          <div class="dialog-actions"><button class="secondary" onclick="copyAgentConfig()">复制 Agent 配置</button><button class="primary" onclick="ackIssuedToken()">已保存，隐藏明文</button></div>
        </section>
        <div style="border-top:1px solid var(--line);margin:22px 0 8px"></div>
        <div class="right" style="justify-content:space-between"><h3 style="margin:0">已签发 Token</h3><button class="ghost" onclick="loadTokens()">刷新</button></div>
        <div id="tokenList"></div>
      </div>
    </dialog>
  </div>
<script>
const state={cases:[],selected:null,run:null,evidence:[],step:0,isAdmin:false,issuedToken:null};
const $=id=>document.getElementById(id);
async function api(path,options={}){const r=await fetch(path,{credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})},...options});let data={};try{data=await r.json()}catch{}if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);return data}
async function boot(){try{const s=await api('/v1/session');showApp(s.user,s.is_admin)}catch{showLogin()}}
function showLogin(){$('loginView').classList.remove('hidden');$('appView').classList.add('hidden');$('userbar').classList.add('hidden')}
async function login(e){e.preventDefault();$('loginError').classList.add('hidden');try{const r=await api('/v1/login',{method:'POST',body:JSON.stringify({username:$('username').value,password:$('password').value})});showApp(r.user,r.is_admin)}catch(err){$('loginError').textContent=err.message;$('loginError').classList.remove('hidden')}}
async function logout(){await api('/v1/logout',{method:'POST',body:'{}'});location.reload()}
async function showApp(user,isAdmin=false){state.isAdmin=!!isAdmin;$('loginView').classList.add('hidden');$('appView').classList.remove('hidden');$('userbar').classList.remove('hidden');$('who').textContent=user;$('adminPanel').classList.toggle('hidden',!state.isAdmin);await loadCases();if(state.isAdmin)await loadTokens()}
function statusLabel(v){return {active:'有效',expired:'已过期',revoked:'已撤销'}[v]||v}
function formatTime(v){return v?new Date(v*1000).toLocaleString():'从未使用'}
async function openTokenManager(){$('tokenDialog').showModal();await loadTokens()}
async function loadTokens(){const r=await api('/v1/admin/tokens');const active=r.tokens.filter(t=>t.status==='active').length;$('tokenCount').textContent=`${active} 个有效 Token`;$('tokenList').innerHTML=r.tokens.map(t=>`<div class="token-row"><div><b>${esc(t.name)}</b> · ${esc(statusLabel(t.status))}<div class="token-meta">使用人：${esc(t.owner||'未填写')}<br>Token ID：<span class="mono">${esc(t.token_id)}</span><br>最后使用：${esc(formatTime(t.last_used_at))} · ${Number(t.use_count||0)} 次<br>到期：${esc(formatTime(t.expires_at))}</div><div>${(t.scopes||[]).map(s=>`<span class="chip">${esc(s)}</span>`).join('')}</div></div><div>${t.status==='active'?`<button class="danger" onclick="revokeToken('${t.token_id}')">撤销</button>`:''}</div></div>`).join('')||'<p class="sub">尚未签发 Token</p>'}
async function issueToken(){const name=$('tokenName').value.trim(),owner=$('tokenOwner').value.trim(),scopes=[...document.querySelectorAll('[data-scope]:checked')].map(x=>x.dataset.scope);if(!name){alert('请输入 Agent 名称');return}if(!owner){alert('请输入对应使用人');return}if(!scopes.length){alert('至少选择一项权限');return}const r=await api('/v1/admin/tokens',{method:'POST',body:JSON.stringify({name,owner,ttl_days:Number($('tokenTtl').value),scopes})});state.issuedToken=r.token;$('issuedBaseUrl').textContent=location.origin;$('issuedToken').textContent=r.token;$('issueForm').classList.add('hidden');$('tokenSecret').classList.remove('hidden');await loadTokens()}
async function copyAgentConfig(){if(!state.issuedToken)return;await navigator.clipboard.writeText(`SRE_LAB_URL=${location.origin}\nSRE_LAB_TOKEN=${state.issuedToken}`)}
function clearIssuedToken(){state.issuedToken=null;$('issuedToken').textContent='';$('issuedBaseUrl').textContent='';$('tokenSecret').classList.add('hidden');$('issueForm').classList.remove('hidden')}
function ackIssuedToken(){clearIssuedToken();$('tokenName').value='';$('tokenOwner').value=''}
async function revokeToken(id){if(!confirm('确定撤销这个 Agent Token？撤销后立即失效。'))return;await api(`/v1/admin/tokens/${id}/revoke`,{method:'POST',body:'{}'});await loadTokens()}
async function loadCases(){const r=await api('/v1/cases');state.cases=r.cases;state.selected=state.selected||r.cases[0]?.case_id;$('caseList').innerHTML=r.cases.map(c=>`<button class="case-card" style="width:100%;text-align:left;cursor:pointer" onclick="selectCase('${c.case_id}')"><strong>${esc(c.case_id)} · ${esc(c.title)}</strong><span class="sub">${c.available_modalities.length} 类观测数据</span></button>`).join('')||'<p class="sub">暂无案例</p>'}
function selectCase(id){state.selected=id;const c=state.cases.find(x=>x.case_id===id);$('pageTitle').textContent=c?.title||id;$('pageSub').textContent=`案例 ${id} · 可用数据：${c?.available_modalities.join(' / ')}`}
function setStep(n){state.step=n;document.querySelectorAll('.step').forEach((el,i)=>el.classList.toggle('active',i===n))}
async function startRun(){if(!state.selected)return;busy(true);try{state.run=await api('/v1/runs',{method:'POST',body:JSON.stringify({case_id:state.selected,agent_id:'web-participant'})});state.evidence=[];setStep(0);$('runMeta').innerHTML=`Run <span class="mono">${state.run.run_id.slice(0,12)}</span><br>状态：running`;renderTask()}catch(e){alert(e.message)}finally{busy(false)}}
function renderTask(){const t=state.run.task;$('pageTitle').textContent=t.alert_title;$('pageSub').textContent=`告警实体：${t.alert_entity.entity_name}`;$('content').innerHTML=`<div class="notice">这是行为等价复现案例。你看不到答案文件、集群凭据或注入参数。</div><div class="grid"><div class="card"><h3>告警</h3><p>${esc(t.alert_title)}</p><p class="mono">${esc(t.alert_entity.entity_name)}</p></div><div class="card"><h3>时间窗口</h3><p>${esc(t.alert_window.start)}</p><p>至 ${esc(t.alert_window.end)}</p></div><div class="card wide"><h3>值班任务</h3><p>${esc(t.prompt_text)}</p></div></div><div style="margin-top:18px"><button class="primary" onclick="renderTools()">开始调查</button></div>`}
function renderTools(){setStep(1);$('content').innerHTML=`<div class="toolbar"><button class="secondary" onclick="tool('get_alerts',{})">告警</button><button class="secondary" onclick="tool('get_topology',{})">拓扑</button><button class="secondary" onclick="tool('list_events',{})">事件</button><button class="secondary" onclick="tool('query_traces',{service:'payment',error_only:true,limit:20})">Payment 错误 Trace</button><button class="secondary" onclick="tool('query_metrics',{entity:'payment',metric:'error_rate',limit:20})">Payment 错误率</button><button class="secondary" onclick="tool('search_logs',{text:'error',limit:20})">错误日志</button></div><div class="right" style="justify-content:space-between;margin-bottom:12px"><span class="sub">已收集 <b id="evCount">${state.evidence.length}</b> 条证据</span><button class="primary" onclick="renderAnswer()">形成诊断</button></div><div id="evidenceList">${evidenceHtml()}</div>`}
async function tool(name,args){busy(true);try{const r=await api(`/v1/runs/${state.run.run_id}/tools`,{method:'POST',body:JSON.stringify({tool:name,arguments:args})});for(const e of r.evidence)if(!state.evidence.some(x=>x.evidence_id===e.evidence_id))state.evidence.push(e);renderTools()}catch(e){alert(e.message)}finally{busy(false)}}
function evidenceHtml(){if(!state.evidence.length)return '<div class="empty">点击上方工具收集证据。</div>';return state.evidence.slice(-40).reverse().map(e=>`<div class="evidence"><label style="margin:0"><input type="checkbox" checked data-evid="${e.evidence_id}"> <b>${esc(e.source)}</b> · ${esc(e.signal||e.entity||'observation')}</label><small class="mono">${e.evidence_id}</small><div>${esc(JSON.stringify(e.payload||e.value||'').slice(0,320))}</div></div>`).join('')}
function evidenceSelectHtml(){if(!state.evidence.length)return '<div class="error">还没有收集证据，请返回“收集证据”并至少调用一个观测工具。</div>';return state.evidence.slice(-40).reverse().map(e=>`<div class="evidence"><label style="margin:0"><input type="checkbox" checked data-answer-evid="${e.evidence_id}"> <b>${esc(e.source)}</b> · ${esc(e.signal||e.entity||'observation')}</label><small class="mono">${e.evidence_id}</small></div>`).join('')}
function renderAnswer(){setStep(2);$('content').innerHTML=`<div class="notice">平台只评分诊断提案，不会执行任何修复动作。</div><form onsubmit="submitAnswer(event)"><div class="form-row"><div><label>根因实体</label><input id="rootEntity" class="input" placeholder="例如 payment" required></div><div><label>故障类型</label><select id="faultType" class="input"><option>httpError5xx</option><option>podRestartFlapping</option><option>networkLatency</option><option>resourcePressure</option><option>configError</option></select></div></div><label>因果传播链（每行一个节点）</label><textarea id="causal" class="input" rows="4" placeholder="payment&#10;checkout&#10;checkout::/oteldemo.CheckoutService/PlaceOrder" required></textarea><label>诊断摘要</label><textarea id="summary" class="input" rows="3" placeholder="说明根因、影响和关键证据"></textarea><label>提交给评分器的证据</label><div style="max-height:260px;overflow:auto">${evidenceSelectHtml()}</div><div class="right" style="margin-top:18px"><button type="button" class="secondary" onclick="fillDemo()">填入示例诊断</button><button type="submit" class="primary">提交并评分</button></div></form>`}
function fillDemo(){$('rootEntity').value='payment';$('faultType').value='httpError5xx';$('causal').value='payment\ncheckout\ncheckout::/oteldemo.CheckoutService/PlaceOrder';$('summary').value='payment 服务出现 5xx，并沿调用链传播至 checkout 操作。'}
async function submitAnswer(e){e.preventDefault();const ids=[...document.querySelectorAll('[data-answer-evid]:checked')].map(x=>x.dataset.answerEvid);if(!ids.length){alert('至少选择一条证据后再提交');return}busy(true);try{const r=await api(`/v1/runs/${state.run.run_id}/answer`,{method:'POST',body:JSON.stringify({root_cause_entities:[$('rootEntity').value.trim()],fault_type:$('faultType').value,causal_steps:$('causal').value.split('\n').map(x=>x.trim()).filter(Boolean),evidence_ids:ids,summary:$('summary').value,remediation_proposal:{}})});renderScore(r)}catch(err){alert(err.message)}finally{busy(false)}}
function renderScore(r){setStep(3);$('statusText').textContent='演练完成';$('runMeta').innerHTML=`Run <span class="mono">${r.run_id.slice(0,12)}</span><br>状态：completed`;$('content').innerHTML=`<div class="score-grid"><div class="score"><b>${num(r.score.total)}</b><span>总分 / 100</span></div><div class="score"><b>${pct(r.score.entity)}</b><span>根因实体</span></div><div class="score"><b>${pct(r.score.fault)}</b><span>故障类型</span></div><div class="score"><b>${pct(r.score.process)}</b><span>证据与过程</span></div></div><div class="grid"><div class="card"><h3>Checkpoint</h3><p>${r.score.matched_checkpoints} / ${r.score.total_checkpoints} 命中</p></div><div class="card"><h3>证据质量</h3><p>Precision ${pct(r.score.evidence_precision)} · Recall ${pct(r.score.evidence_recall)}</p></div><div class="card wide"><h3>运行效率</h3><p>耗时 ${r.metrics.wall_time_seconds}s · 工具调用 ${r.metrics.tool_calls} 次 · 拒绝 ${r.metrics.rejected_calls} 次</p></div></div><div style="margin-top:18px"><button class="primary" onclick="startRun()">再练一次</button></div>`}
function busy(v){document.body.classList.toggle('loading',v)}function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}function pct(v){return `${Math.round((v||0)*100)}%`}function num(v){return Number(v||0).toFixed(1)}
boot();
</script>
</body>
</html>"""
