# Operação da v1 pessoal

Aplicação: https://the-search.phalopes.workers.dev. Acesso fechado por e-mail autorizado. Solicite um link com phalopes@gmail.com. Site URL do Supabase aponta para esse endereço.

## Desenvolvimento e publicação

Use Python 3.12 e uv 0.13: `uv sync --locked`, `uv run pytest`, `uv run ruff check src tests scripts worker/src/entry.py`, `uv run mypy src`. Web: `npm ci`, `npm run build`, `npm test`. O Playwright precisa de Chromium (`npx playwright install chromium`).

Runtime: `python scripts/prepare_worker.py`, `uv sync --directory worker --locked --python 3.13`, `uv run --directory worker --python 3.13 pywrangler dev`. O pacote gerado reaproveita o motor Python. Configuração pública em worker/wrangler.jsonc; credenciais privilegiadas não fazem parte do aplicativo.

Push em codex/the-search-v1 executa validação e publicação pelo GitHub Actions, usando secrets CLOUDFLARE_ACCOUNT_ID e CLOUDFLARE_API_TOKEN. Não é necessário instalar ferramentas no celular. Não há publicação automática de main nesta versão. Migrations Supabase são versionadas e aplicadas separadamente, após revisão; CI não altera o banco.

## Acesso e dados

private.allowed_emails controla entrada. private.personal_owner identifica o único dono dos tempos pessoais; ser admin sozinho não libera deslocamento. public.feature_flags.personal_travel também precisa estar ativa. RLS e servidor verificam acesso. Perfil e diário pertencem ao usuário. Previsão pública é armazenada como snapshot por usuário por até três horas; o registro de escolha conserva a previsão original.

Não adicionar senha do banco, service role ou tokens ao frontend, repositório ou logs. A chave publishable é pública e depende de RLS. Para outros convidados, cadastro na allowlist exige decisão explícita do dono. Cadastro público permanece fechado.

## Novos picos

Comece pelo perfil YAML validado pelo CLI, documente fonte e limitações e registre public.surf_spots com experimental=true. Remova deslocamento pessoal do JSON público. Valide vento, direção, período, maré e nível antes de promover o pico. Esta versão não tem tela administrativa de cadastro de picos. Catálogo inicial: Matadeiro, Campeche, Joaquina, Mole e Barra da Lagoa.

## Reversão e manutenção

Reverta apenas o commit responsável, rode os checks e envie à branch de publicação. O Actions publica nova versão. A versão anterior também fica no histórico de Workers da conta usada pelos secrets. Não reverta migrations com DROP para reverter a interface. Dados pessoais precisam de backup autorizado antes de qualquer operação destrutiva. Não há política de backup paga contratada nesta entrega.

O cache do navegador guarda somente arquivos estáticos. Offline não apresenta previsão antiga. A instalação PWA depende do navegador e não substitui conexão para consultar ou salvar. Auth usa envio padrão do Supabase, sujeito aos limites do serviço; SMTP próprio não foi contratado.

O histórico SQLite anterior permanece local. A estrutura de importação existe, mas a fila está vazia: seis registros aguardam autorização específica para envio de notas e avaliações ao Supabase. Se o dono já tiver conta, importar explicitamente para seu user_id; o gatilho de primeiro cadastro não será novamente executado.

## Acesso por senha — 10/10/2026

Sucede o login por link como rotina. Entrar usa signInWithPassword. Primeiro acesso do dono: botão Primeiro acesso ou esqueci minha senha envia recuperação para a conta existente e abre definição de senha. Senha escolhida pelo usuário, mínimo 12 caracteres, nunca uma senha compartilhada no código. Usuário autenticado pode alterar em Senha, informando a atual.

Para convidar: adicionar o e-mail à allowlist privada, então usar Invite user no painel Supabase Authentication/Users com Site URL do app. O convite cria a conta e seu link abre a definição de senha. Não há cadastro público nem tela de envio de convites nesta v1. Não enviar convite sem autorização para o destinatário. E-mails ficam para convite/recuperação; o SMTP padrão restringe destinatários e volume, então convidados externos exigem SMTP próprio antes de expandir o piloto.

Os seis registros SQLite foram importados com autorização explícita de Pedro: cinco sessões e uma escolha pré-sessão. Campo legacy_id torna a importação repetível sem duplicação. Relatos, notas e horários preservados; previsão original inexistente não é inventada.
