# tigraoSHOP

Bot Telegram agregador de ofertas para Shopee, Mercado Livre, Amazon, AliExpress e SHEIN.

Base funcional criada com Python 3.12, aiogram 3.27, FastAPI webhook, SQLite assíncrono, modo inline rápido e arquitetura modular por loja. O foco é buscar, montar e enviar ofertas de forma limpa, sem camada de comissão ou afiliados.

## O que já faz

- Recebe link, ID de produto ou termo de busca.
- Funciona no privado com texto comum.
- Funciona em grupo com `/of link`, `/of ID` e `/s termo`.
- Aceita reply de foto com `/of link` para usar a imagem respondida como destaque.
- Gera card HTML com o nome do produto em hyperlink.
- Usa botões de oferta com `style` verde, azul e vermelho quando suportado pelo cliente/API.
- Usa botão de copiar link com fallback para abrir URL.
- Tenta apagar o comando original apenas quando o bot for admin e tiver permissão de apagar mensagens.
- Não envia mensagens intermediárias no grupo.
- Tem modo inline com resposta curta e cache.
- Usa Mercado Livre por API pública quando possível.
- Usa Shopee, Amazon, AliExpress e SHEIN por link/metadados nesta primeira base.
- Envia sempre o link original/resolvido da loja, sem parâmetros de afiliado.

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
/of B0ABCDEFGH
/s air fryer 5l
```

## Inline mode

Ative o inline mode no BotFather.

Depois use:

```text
@SeuBot air fryer
@SeuBot mercado livre fone bluetooth
```

O inline responde primeiro com cache local. Se não houver cache, faz busca rápida nos adaptadores configurados com timeout curto.

## Grupo sem admin

O bot funciona sem ser administrador usando comandos normais:

```text
/of link
/s termo
```

Sem permissão de admin, ele não tenta apagar mensagem do usuário. Publica somente o card final.

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
    callbacks.py
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
    aliexpress_store.py
    amazon_store.py
    base.py
    generic.py
    mercadolivre.py
    registry.py
    shein_store.py
    shopee_store.py
tests/
```

## Estado dos adaptadores

- Mercado Livre: busca e item via API pública quando possível.
- Amazon: link/ASIN e metadados.
- AliExpress: link/ID e metadados.
- Shopee: link e metadados.
- SHEIN: link e metadados.

## Observação técnica

A base não faz scraping agressivo. Quando uma loja não fornecer dados suficientes por metadados, o card usa fallback seguro com título genérico e link final. Isso evita quebrar o bot em público por bloqueio de página, timeout ou mudança de HTML.
