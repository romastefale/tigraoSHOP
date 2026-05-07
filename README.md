# tigraoSHOP

Bot Telegram agregador de ofertas em modo conservador para Mercado Livre.

Base funcional criada com Python 3.12, aiogram 3.27, FastAPI webhook, SQLite assíncrono, modo inline rápido e arquitetura modular por loja. O foco atual é publicar somente ofertas do Mercado Livre com preço confirmado, sem camada de comissão ou afiliados.

## Modo atual

- Funciona apenas com Mercado Livre.
- Recebe link, ID de produto ou termo de busca do Mercado Livre.
- Funciona no privado com texto comum.
- Funciona em grupo com `/of link`, `/of MLB1234567890` e `/s termo`.
- Aceita reply de foto com `/of link` para usar a imagem respondida como destaque.
- Gera card HTML com o nome do produto em hyperlink.
- Usa botão principal com o nome da loja.
- Usa botão `Copiar link` em estilo azul quando suportado pelo cliente/API.
- Usa botão `Similares` em estilo vermelho quando suportado pelo cliente/API.
- Não usa botão público de remover oferta.
- Tenta apagar o comando original apenas quando o bot for admin e tiver permissão de apagar mensagens.
- Não envia mensagens intermediárias no grupo.
- Tem modo inline com resposta curta e cache.
- Bloqueia publicação quando o preço não for confirmado com segurança.
- Outras lojas ficam desabilitadas até expansão futura com validação própria de preço.

## Regra de preço

O bot só publica card quando consegue obter preço confirmado no Mercado Livre.

Para link sem ID direto, ele tenta ler metadados da página e confirmar a oferta via consulta pública do Mercado Livre. Se houver divergência entre fontes, ausência de preço ou falha de leitura, o card é bloqueado e o usuário recebe aviso.

## Comandos

```text
/start
/help
/of link-ou-id
/s termo de busca
```

Exemplos:

```text
/of https://www.mercadolivre.com.br/produto
/of MLB1234567890
/s air fryer 5l
/s mercado livre fone bluetooth
```

## Inline mode

Ative o inline mode no BotFather.

Depois use:

```text
@SeuBot air fryer
@SeuBot mercado livre fone bluetooth
```

O inline responde apenas com resultados do Mercado Livre que tenham preço disponível.

## Grupo sem admin

O bot funciona sem ser administrador usando comandos normais:

```text
/of link
/s termo
```

Sem permissão de admin, ele não tenta apagar mensagem do usuário. Publica somente o card final quando o preço estiver confirmado.

## Grupo com admin

Quando o bot for admin e tiver `can_delete_messages`, ele tenta apagar o comando original e deixa apenas a oferta final no chat.

## Variáveis de ambiente

Copie `.env.example` para `.env`.

```env
BOT_TOKEN=
BOT_USERNAME=tigraoSHOPBot
OWNER_ID=
ADMIN_LOG_CHAT_ID=

WEBHOOK_BASE_URL=
WEBHOOK_SECRET=replace-this-secret

DATABASE_URL=/app/data/offers.db

REQUEST_TIMEOUT_SECONDS=4
INLINE_TIMEOUT_SECONDS=1.2
INLINE_CACHE_TIME=30
```

## Rodar local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Healthcheck:

```text
/healthz
```

## Railway

1. Crie o projeto no Railway a partir do GitHub.
2. Configure as variáveis do `.env.example`.
3. Use volume em `/app/data` para manter o SQLite persistente.
4. Defina `WEBHOOK_BASE_URL` com a URL pública do Railway.
5. O Dockerfile usa automaticamente `${PORT:-8000}`.

## Testes

```bash
python -m compileall app
pytest -q
```

Também existe workflow em `.github/workflows/ci.yml` para compilar e testar em push e pull request.

## Estrutura

```text
app/
  main.py
  config.py
  bot/
    commands.py
    inline.py
    keyboards.py
    render.py
    router.py
  core/
    metadata.py
    models.py
    parser.py
    permissions.py
    resolver.py
    security.py
  db/
    repo.py
  services/
    offer_service.py
  stores/
    base.py
    mercadolivre.py
    registry.py
tests/
```

## Estado dos adaptadores

- Mercado Livre: habilitado.
- Shopee, Amazon, AliExpress e SHEIN: desabilitados temporariamente para evitar publicação com preço incerto.

## Observação técnica

A base não faz scraping agressivo. Quando não houver confirmação de preço, o bot não publica o card. Isso prioriza precisão sobre quantidade de ofertas.
