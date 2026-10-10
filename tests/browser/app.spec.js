import {test,expect} from '@playwright/test';
const user={id:'00000000-0000-0000-0000-000000000001',aud:'authenticated',role:'authenticated',email:'qa@example.invalid',app_metadata:{},user_metadata:{},created_at:'2026-10-10T00:00:00Z'};
const spots=[{id:'matadeiro',profile:{nome:'Matadeiro'},experimental:false}];
async function logged(page){
 await page.addInitScript(({user})=>localStorage.setItem('sb-txufklveyvlweiukzdsp-auth-token',JSON.stringify({access_token:'fixture.only.not-a-real-token',refresh_token:'fixture',token_type:'bearer',expires_in:3600,expires_at:Math.floor(Date.now()/1000)+3600,user})),{user});
 await page.route('https://txufklveyvlweiukzdsp.supabase.co/**',route=>route.fulfill({json:route.request().url().includes('/user')?user:[]}));
 await page.route('**/api/bootstrap',route=>route.fulfill({json:{spots,preferences:null,travel:[],admin:false}}));
}
for(const width of [375,768,1280])test(`perfil e janela em ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:950});await logged(page);await page.goto('/');
 await page.getByRole('button',{name:'Meu surf',exact:true}).click();
 await expect(page.locator('#travel-field')).toBeHidden();
 await page.locator('#end').fill('10:30');await page.getByRole('button',{name:'Salvar meu surf'}).click();
 await expect(page.locator('#profile-message')).toContainText('duração');
 await page.locator('#end').fill('14:00');await page.getByRole('button',{name:'Salvar meu surf'}).click();await expect(page.locator('#profile-dialog')).toBeHidden();
 await expect(page.locator('#notice')).toContainText('salvas');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
 await page.reload();await expect(page.getByRole('button',{name:'Encontrar minha janela'})).toBeVisible();
 await page.route('**/api/recommend',route=>route.fulfill({status:503,json:{error:'Serviço indisponível.'}}));
 await page.getByRole('button',{name:'Encontrar minha janela'}).click();await expect(page.locator('#results')).toContainText('indisponível');
});
test('diário não executa conteúdo do parecer e edição continua disponível',async({page})=>{
 await logged(page);await page.route('**/rest/v1/surf_sessions**',route=>route.fulfill({json:[{id:'one',surf_date:'2026-10-11',spot_id:'matadeiro',kind:'planned',notes:'<img src=x onerror=alert(1)>',rating:null}]}));await page.goto('/');await page.getByRole('button',{name:'Diário',exact:true}).click();await expect(page.locator('.notes')).toHaveText('<img src=x onerror=alert(1)>');await expect(page.locator('.notes img')).toHaveCount(0);await page.getByRole('button',{name:'Dar parecer'}).click();await page.locator('#session-kind').selectOption('surfed');await expect(page.locator('#rating-field')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('#session-dialog')).toBeHidden();
});
test('visitante vê acesso por e-mail e nenhum dado pessoal',async({page})=>{await page.goto('/');await expect(page.getByRole('heading',{name:/Encontre sua/})).toBeVisible();await expect(page.locator('#app')).toBeHidden();await expect(page.locator('#nav')).toBeHidden();});
