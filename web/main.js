import { createClient } from '@supabase/supabase-js';
const sb = createClient('https://txufklveyvlweiukzdsp.supabase.co','sb_publishable_LqU71oWfLxT6deWk_YPcGw_zq78Et9p');
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clock = value => value?.slice(11,16) || '';
const localDate = d => new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(d);
const niceDate = value => new Date(`${value}T12:00:00-03:00`).toLocaleDateString('pt-BR',{weekday:'long',day:'numeric',month:'long'});
const decimal = (n, digits=1) => Number(n).toLocaleString('pt-BR',{minimumFractionDigits:digits,maximumFractionDigits:digits});
let session, bootstrap, preferences, latest, inspected, editingRecommendation = null, sessions = [], busy = false, generation = 0;
const defaults = spots => ({level:'intermediario',start:'10:00',end:'14:00',duration:90,spots:spots.map(s=>s.id),size_min:null,size_max:null,hard_size:false,travel_max:null});
async function api(path, body) {
 const {data} = await sb.auth.getSession();
 if (!data.session) throw new Error('Entre novamente para continuar.');
 const response = await fetch(path,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${data.session.access_token}`,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
 const result = await response.json();
 if (!response.ok) throw new Error(result.error || 'Não foi possível concluir. Tente novamente.');
 return result;
}
const tell = message => { $('notice').textContent=message; };
function checkError(error){if(error)throw error;}
function summary(){ $('profile-summary').textContent=`${{iniciante:'Iniciante',intermediario:'Intermediário',avancado:'Avançado'}[preferences.level]} · ${preferences.start.slice(0,5)}–${preferences.end.slice(0,5)} · ${preferences.duration} min · ${preferences.spots.length} picos`; }
function show(view){ $('ocean').hidden=view!=='ocean';$('history').hidden=view!=='history';$('home-nav').toggleAttribute('aria-current',view==='ocean');$('history-nav').toggleAttribute('aria-current',view==='history');if(view==='ocean')$('home-nav').setAttribute('aria-current','page');else $('history-nav').setAttribute('aria-current','page'); }
async function loadUser(current){
 if(current && session?.user.id===current.user.id && bootstrap){session=current;return;}
 $('query-form').querySelector('button').disabled=true;
 session=current;const version=++generation;$('offline').hidden=true;
 $('login').hidden=!!current;$('app').hidden=true;$('nav').hidden=true;
 if(!current){bootstrap=null;latest=null;preferences=null;$('results').replaceChildren();$('session-list').replaceChildren();return;}
 tell('Carregando seu surf…');
 try{const result=await api('/api/bootstrap');if(version!==generation)return;bootstrap=result;preferences=result.preferences || defaults(result.spots);summary();
 $('spot-checks').innerHTML=result.spots.map(s=>`<label class="check"><input type="checkbox" name="spot" value="${esc(s.id)}">${esc(s.profile.nome)}${s.experimental?' · experimental':''}</label>`).join('');
 $('session-spot').innerHTML=result.spots.map(s=>`<option value="${esc(s.id)}">${esc(s.profile.nome)}</option>`).join('');
 $('travel-field').hidden=!result.admin || !result.travel.length;
 $('app').hidden=false;$('nav').hidden=false;
 $('query-form').querySelector('button').disabled=false;
 tell('');show('ocean');if(passwordSetup)openPassword(true);$('results').innerHTML='<div class="empty"><h2>Vamos olhar o mar?</h2><p>Escolha o dia e consulte as condições. Ajuste sua disponibilidade em Meu surf.</p></div>';
 }catch(e){if(version!==generation)return;if(!navigator.onLine){$('offline').hidden=false;$('login').hidden=true;tell('Sem conexão.');}else{tell(e.message);$('login').hidden=false;}}
}
let passwordSetup = ['invite','recovery'].includes(new URLSearchParams(location.hash.slice(1)).get('type'));
function openPassword(setup=false){passwordSetup=setup;$('password-form').reset();$('current-password-field').hidden=setup;$('current-password').required=!setup;$('password-message').textContent='';if(!$('password-dialog').open)$('password-dialog').showModal();}
$('login-form').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;$('login-message').textContent='Entrando…';
 try{const {error}=await sb.auth.signInWithPassword({email:$('email').value.trim(),password:$('password').value});checkError(error);$('password').value='';$('login-message').textContent='';}
 catch(e){$('login-message').textContent='Não foi possível entrar. Confira e-mail e senha ou use a recuperação de acesso.';}finally{button.disabled=false;}};
$('recover').onclick=async e=>{const email=$('email');if(!email.reportValidity())return;const button=e.currentTarget;button.disabled=true;$('login-message').textContent='Solicitando acesso…';
 try{const {error}=await sb.auth.resetPasswordForEmail(email.value.trim(),{redirectTo:location.origin});checkError(error);$('login-message').textContent='Se esse e-mail tiver acesso, você receberá um link para definir sua senha. Confira também o spam. Depois, entre normalmente com sua senha.';}
 catch(e){$('login-message').textContent='Não foi possível enviar agora. Aguarde alguns minutos e tente novamente.';}finally{button.disabled=false;}};
$('password-nav').onclick=()=>openPassword(false);
$('password-form').onsubmit=async e=>{e.preventDefault();const password=$('new-password').value;if(password!==$('confirm-password').value){$('password-message').textContent='As senhas precisam ser iguais.';return;}const button=e.submitter;button.disabled=true;$('password-message').textContent='Salvando…';
 try{const {error}=await sb.auth.updateUser({password,...(!passwordSetup?{current_password:$('current-password').value}:{})});checkError(error);$('password-form').reset();passwordSetup=false;$('password-dialog').close();tell('Senha salva. Nos próximos acessos, use seu e-mail e senha.');}
 catch(e){$('password-message').textContent='Não foi possível salvar. Confira a senha atual, use pelo menos 12 caracteres ou solicite um novo link de recuperação.';}finally{button.disabled=false;}};
$('retry').onclick=()=>loadUser(session);
$('logout').onclick=async()=>{await sb.auth.signOut();tell('Você saiu.');};
$('home-nav').onclick=()=>show('ocean');
$('history-nav').onclick=async()=>{show('history');await loadHistory();};
function openProfile(){if(!preferences)return;for(const [id,key] of [['level','level'],['start','start'],['end','end'],['duration','duration'],['size-min','size_min'],['size-max','size_max'],['travel-max','travel_max']])$(id).value=preferences[key]??'';
 $('hard-size').checked=preferences.hard_size;document.querySelectorAll('[name=spot]').forEach(input=>input.checked=preferences.spots.includes(input.value));$('profile-message').textContent='';$('profile-dialog').showModal();}
$('profile-nav').onclick=openProfile;
document.querySelectorAll('[data-close]').forEach(button=>button.onclick=()=>$(button.dataset.close).close());
$('profile-form').onsubmit=async e=>{e.preventDefault();const value=id=>$(id).value===''?null:Number($(id).value);const p={level:$('level').value,start:$('start').value,end:$('end').value,duration:value('duration'),spots:[...document.querySelectorAll('[name=spot]:checked')].map(i=>i.value),size_min:value('size-min'),size_max:value('size-max'),hard_size:$('hard-size').checked,travel_max:$('travel-field').hidden?null:value('travel-max')};
 const minutes=t=>Number(t.slice(0,2))*60+Number(t.slice(3,5));let error='';
 if(!p.spots.length)error='Escolha pelo menos um pico.';
 else if(p.start<'06:00'||p.end>'18:00'||minutes(p.end)-minutes(p.start)<p.duration)error='A janela entre 06h e 18h precisa comportar a duração mínima.';
 else if(p.size_min!==null&&p.size_max!==null&&p.size_min>p.size_max)error='A ondulação mínima deve ser menor ou igual à máxima.';
 else if(p.hard_size&&p.size_min===null&&p.size_max===null)error='Defina pelo menos um limite de ondulação.';
 if(error){$('profile-message').textContent=error;return;}e.submitter.disabled=true;
 try{const {error}=await sb.from('surf_profiles').upsert({user_id:session.user.id,preferences:p,updated_at:new Date().toISOString()});checkError(error);preferences=p;summary();latest=null;$('results').innerHTML='<div class="empty"><h2>Seu surf foi atualizado.</h2><p>Consulte o mar para comparar as novas preferências.</p></div>';$('profile-dialog').close();tell('Preferências salvas.');}
 catch(e){$('profile-message').textContent='Não foi possível salvar. Tente novamente.';}finally{e.submitter.disabled=false;}};
$('query-form').onsubmit=async e=>{e.preventDefault();if(busy||!preferences)return;if(!navigator.onLine){tell('Você está offline. Conecte-se para consultar uma previsão atualizada.');return;}busy=true;e.submitter.disabled=true;tell('Consultando swell, vento e nível do mar…');$('results').setAttribute('aria-busy','true');latest=null;
 try{latest=await api('/api/recommend',{date:$('surf-date').value,preferences});inspected=latest.results.find(r=>r.windows.length)?.spot_id || latest.results[0]?.spot_id;render();tell('');}
 catch(e){$('results').innerHTML='<div class="empty"><h2>O mar ficou indisponível por aqui.</h2><p>Confira a conexão e tente consultar novamente. Nenhuma previsão antiga será apresentada como atual.</p></div>';tell(e.message);}
 finally{busy=false;e.submitter.disabled=false;$('results').removeAttribute('aria-busy');}};
function chart(hours,key,title,unit,window){
 const points=hours.filter(h=>clock(h.at)>='06:00'&&clock(h.at)<='18:00');if(!points.length)return '';
 const values=points.map(h=>h[key]);const lo=Math.min(...values),hi=Math.max(...values);const pad=Math.max((hi-lo)*.15,.1);const min=lo-pad,max=hi+pad;
 const x=t=>44+(Number(t.slice(11,13))+Number(t.slice(14,16))/60-6)/12*288;
 const y=v=>110-(v-min)/(max-min)*88;
 // Split missing-hour segments; never draw an interpolated line across absent data.
 const segments=[];let segment=[];let previous=-2;for(const p of points){const hour=Number(p.at.slice(11,13));if(hour!==previous+1&&segment.length){segments.push(segment);segment=[];}segment.push(`${x(p.at)},${y(p[key])}`);previous=hour;}if(segment.length)segments.push(segment);
 return `<figure class="chart"><figcaption>${title} <span class="hint">(${unit})</span></figcaption><svg viewBox="0 0 348 144" role="img" aria-label="${title}, entre 06h e 18h. Dados completos na tabela abaixo.">${window?`<rect x="${x(window.start)}" y="12" width="${Math.max(0,x(window.end)-x(window.start))}" height="102"/>`:''}<line x1="44" y1="114" x2="332" y2="114"/>${segments.map(s=>`<polyline points="${s.join(' ')}"/>`).join('')}<text x="0" y="24">${decimal(max)}</text><text x="0" y="112">${decimal(min)}</text>${[6,9,12,15,18].map(h=>`<text x="${44+(h-6)/12*288}" y="136" text-anchor="middle">${h}h</text>`).join('')}</svg></figure>`;
}
function render(){
 if(!latest)return;const chosen=latest.results.find(r=>r.spot_id===inspected);if(!chosen)return;const best=chosen.windows[0];const h=chosen.hours.find(h=>h.at===best?.start);const overall=latest.results.find(r=>r.windows.length);
 let html=`<p class="eyebrow">${esc(niceDate(latest.date))}</p>`;
 if(!overall)html+='<div class="empty"><h2>Hoje não encontramos uma janela.</h2><p>Ajuste sua disponibilidade ou os picos em Meu surf. Dados indisponíveis não contam como condição ruim.</p></div>';
 if(best&&h){html+=`<section class="recommendation" aria-labelledby="recommended-name"><p class="eyebrow">${chosen.spot_id===overall?.spot_id?'MELHOR ENCAIXE NA SUA CONSULTA':'OUTRA OPÇÃO PARA SUA SESSÃO'}</p><div class="rec-top"><h2 id="recommended-name">${esc(chosen.name)}</h2><div class="index">${decimal(best.score)}<small>índice / 100</small></div></div><div class="window">${clock(best.start)}–${clock(best.end)}</div><p>${preferences.duration} minutos de janela completa${chosen.experimental?' · Pico experimental':''}.</p><div class="metrics"><div class="metric"><strong>${decimal(h.swell_m)} m · ${decimal(h.period_s)} s</strong><span>Swell · ${Math.round(h.swell_direction)}°</span></div><div class="metric"><strong>${decimal(h.wind_kmh)} km/h</strong><span>Vento · ${Math.round(h.wind_direction)}°</span></div><div class="metric"><strong>${decimal(h.sea_level_m,2)} m</strong><span>Nível do mar MSL · ${esc(h.phase)}</span></div></div><p class="hint">Condições na entrada; acompanhe a evolução nos gráficos.</p><button class="primary" id="choose">Vou nesse pico</button></section>`;}
 html+=`<section aria-labelledby="evidence-title"><h2 id="evidence-title">O que sustenta a escolha</h2><p>${esc(chosen.name)} · a faixa amarela indica a janela selecionada.</p>${chosen.hours.length?`<div class="charts">${chart(chosen.hours,'swell_m','Swell','m',best)}${chart(chosen.hours,'wind_kmh','Vento','km/h',best)}${chart(chosen.hours,'sea_level_m','Nível do mar MSL','m',best)}</div><details><summary>Ver números por hora e direções</summary><div class="table-scroll" tabindex="0" role="region" aria-label="Dados horários"><table><caption>Horários de Florianópolis · ${esc(chosen.name)}</caption><thead><tr><th scope="col">Hora</th><th scope="col">Swell m</th><th scope="col">Período s</th><th scope="col">Swell °</th><th scope="col">Vento km/h</th><th scope="col">Vento °</th><th scope="col">Nível MSL m</th><th scope="col">Índice</th></tr></thead><tbody>${chosen.hours.filter(h=>clock(h.at)>='06:00'&&clock(h.at)<='18:00').map(h=>`<tr><th scope="row">${clock(h.at)}</th><td>${decimal(h.swell_m)}</td><td>${decimal(h.period_s)}</td><td>${Math.round(h.swell_direction)}</td><td>${decimal(h.wind_kmh)}</td><td>${Math.round(h.wind_direction)}</td><td>${decimal(h.sea_level_m,2)}</td><td>${decimal(h.score)}</td></tr>`).join('')}</tbody></table></div></details>`:`<p>${esc(chosen.reason)}</p>`}
 ${h?`<details><summary>Entender o índice de encaixe</summary><p>Índice da janela: média ponderada pela duração de cada hora. Encaixe técnico ${decimal(best.technical_score)}/100. ${preferences.size_min!==null||preferences.size_max!==null?'Preferência de tamanho: 90% técnico + 10% tempo dentro da faixa.':''}</p><ul>${h.factors.fatores.map(f=>`<li>${esc(f.nome)} · peso ${f.peso*100}% · ${esc(f.explicacao)}</li>`).join('')}</ul><p class="hint">Fatores acima referem-se à hora de entrada. A altura usada pelo motor é swell em mar aberto.</p></details>`:''}
 <p class="source">${esc(latest.source)}${chosen.collected_at?` · Coletado ${esc(new Date(chosen.collected_at).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'}))}. Reutilização por até 3 horas.`:''}<br>${esc(chosen.provenance)}</p><p class="hint warning">${esc(latest.limits)}</p></section><section><h2>Compare os picos</h2>${latest.results.map(r=>`<div class="ranking"><div><h3>${esc(r.name)}</h3><p>${r.windows.length?`${clock(r.windows[0].start)}–${clock(r.windows[0].end)} · ${decimal(r.windows[0].score)}/100`:esc(r.reason)}</p>${r.experimental?'<span class="hint">Experimental</span>':''}</div><button data-inspect="${esc(r.spot_id)}" aria-label="Ver dados de ${esc(r.name)}">Ver dados</button></div>`).join('')}</section>`;
 $('results').innerHTML=html;
 document.querySelectorAll('[data-inspect]').forEach(b=>b.onclick=()=>{inspected=b.dataset.inspect;render();$('evidence-title').scrollIntoView({block:'start'});$('evidence-title').setAttribute('tabindex','-1');$('evidence-title').focus({preventScroll:true});});
 if($('choose'))$('choose').onclick=()=>openSession(null,chosen,best);
}
function openSession(row=null,spot=null,window=null){editingRecommendation=row?.recommendation || (spot?{date:latest.date,spot_id:spot.spot_id,window,source:latest.source,collected_at:spot.collected_at,preferences,hours:spot.hours,snapshot:spot.snapshot}:null);$('session-id').value=row?.id || '';$('session-spot').value=row?.spot_id || spot?.spot_id || bootstrap.spots[0].id;$('session-date').value=row?.surf_date || latest?.date || localDate(new Date());$('session-time').value=row?.starts_at?.slice(0,5)||clock(window?.start);$('session-kind').value=row?.kind || (spot?'planned':'surfed');$('session-rating').value=row?.rating??'';$('session-notes').value=row?.notes||'';$('session-message').textContent='';ratingVisibility();$('session-dialog').showModal();}
function ratingVisibility(){$('rating-field').hidden=$('session-kind').value!=='surfed';}
$('session-kind').onchange=ratingVisibility;$('add-session').onclick=()=>openSession();
$('session-form').onsubmit=async e=>{e.preventDefault();e.submitter.disabled=true;const kind=$('session-kind').value;const payload={user_id:session.user.id,spot_id:$('session-spot').value,surf_date:$('session-date').value,starts_at:$('session-time').value||null,kind,rating:kind==='surfed'&&$('session-rating').value!==''?Number($('session-rating').value):null,notes:$('session-notes').value,recommendation:editingRecommendation};
 try{const id=$('session-id').value;const {error}=id?await sb.from('surf_sessions').update(payload).eq('id',id):await sb.from('surf_sessions').insert(payload);checkError(error);$('session-dialog').close();tell('Registro salvo no seu diário.');if(!$('history').hidden)await loadHistory();}
 catch(e){$('session-message').textContent='Não foi possível salvar. Confira a conexão e tente novamente.';}finally{e.submitter.disabled=false;}};
async function loadHistory(){$('session-list').textContent='Carregando seu diário…';try{const {data,error}=await sb.from('surf_sessions').select('*').order('surf_date',{ascending:false}).limit(200);checkError(error);sessions=data;$('session-list').innerHTML=data.length?data.map(r=>`<article class="session-row"><div><h2>${esc(bootstrap.spots.find(s=>s.id===r.spot_id)?.profile.nome||r.spot_id)}</h2><p>${esc(niceDate(r.surf_date))}${r.starts_at?' · '+esc(r.starts_at.slice(0,5)):''}</p><p>${r.kind==='planned'?'Escolha antes de sair':'Sessão realizada'}${r.rating!==null?' · Nota '+decimal(r.rating)+'/5':''}</p><p class="notes">${esc(r.notes)}</p>${r.recommendation?(r.recommendation.legacy_id?'<span class="hint">Importado do histórico local; previsão original indisponível.</span>':'<span class="hint">Consulta original preservada com este registro.</span>'):''}</div><button data-edit="${esc(r.id)}">${r.kind==='planned'?'Dar parecer':'Editar'}</button></article>`).join(''):'<div class="empty"><h2>Seu diário começa na próxima sessão.</h2><p>Registre uma escolha ou conte como foi o surf.</p></div>';document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>openSession(sessions.find(r=>r.id===b.dataset.edit)));}catch(e){$('session-list').textContent='Não foi possível carregar o diário. Toque em Diário para tentar novamente.';}}
let installEvent;window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installEvent=e;$('install').hidden=false;});$('install').onclick=async()=>{await installEvent?.prompt();$('install').hidden=true;};
window.addEventListener('offline',()=>tell('Você está offline. Conecte-se para consultar ou salvar; previsões antigas não são mostradas como atuais.'));window.addEventListener('online',()=>tell('Conexão restabelecida. Você já pode consultar o mar.'));
const today=new Date();$('surf-date').min=localDate(today);$('surf-date').max=localDate(new Date(today.getTime()+2*86400000));$('surf-date').value=localDate(new Date(today.getTime()+86400000));
// SDK handles implicit email callback; credentials are removed from the URL afterwards.
sb.auth.onAuthStateChange((event,current)=>{if(event==='PASSWORD_RECOVERY')passwordSetup=true;setTimeout(async()=>{await loadUser(current);if(current&&passwordSetup)openPassword(true);},0);});
const {data,error}=await sb.auth.getSession();if(error)tell('Link inválido ou vencido. Solicite um novo acesso.');await loadUser(data.session);if(location.hash.includes('access_token'))history.replaceState({},'',location.pathname);
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
