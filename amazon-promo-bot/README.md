# Amazon Promo Bot

Backend em FastAPI para gerenciar uma V1 manual de livros monitorados da Amazon. O sistema mantém uma lista fixa de produtos BookTok/BookGram, ajuda a validar ASINs manualmente, gera links afiliados e monta mensagens prontas para copiar.

## A V1 Consulta A Amazon Real?

Não por padrão.

A V1 atual usa uma lista fixa/manual em `data/manual_products_seed.json`. Produtos com ASIN têm link afiliado, mas produto com link afiliado não significa promoção. Sem Creators API ativa, o preço aparece como `Preço não verificado` ou `Preço: consultar no link`.

O projeto não usa scraping, não pede login/senha da Amazon, não usa navegador automatizado e não consulta preço real por HTML. Preços reais e descontos dependem de integração futura com API oficial da Amazon.

## Stack

- Python 3.11+
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite
- Pydantic
- python-dotenv
- Jinja2
- pytest

## Instalar

```powershell
cd C:\Users\gabri\Documents\GitHub\Sexo\Bot\amazon-promo-bot
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configurar

Crie um `.env` local a partir do exemplo:

```powershell
copy .env.example .env
```

Exemplo:

```env
AMAZON_ASSOCIATE_TAG=sua-tag-aqui
AMAZON_SOURCE=manual_fixed
DATABASE_URL=sqlite:///./data/promos.db

AMAZON_CREATORS_API_ENABLED=false
AMAZON_CREATORS_API_PUBLIC_KEY=
AMAZON_CREATORS_API_PRIVATE_KEY=
AMAZON_CREATORS_API_PARTNER_TAG=
AMAZON_MARKETPLACE=www.amazon.com.br
AMAZON_REGION=br
AMAZON_LIVE_PRICE_LIMIT=20
```

Não commite o `.env`. A private key futura da Creators API nunca deve ir para o GitHub.

## Rodar No Windows Sem Ativar Venv

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Testes:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Interface Web

Abra:

```text
http://127.0.0.1:8000/
```

Docs:

```text
http://127.0.0.1:8000/docs
```

Fluxo:

1. Importe o seed.
2. Vá em `Pendentes de validação`.
3. Abra a busca da Amazon.
4. Copie a URL correta do produto.
5. Cole a URL ou ASIN no painel.
6. Salve o ASIN.
7. O produto passa a ter `Link pronto`.
8. Copie link ou mensagem.
9. Exporte CSV/JSON se quiser.

## Top livros e promoções

O topo do dashboard mostra sugestões por categoria. Quando a Creators API ainda não está ativa, essa área aparece como `Top livros para checar hoje`: são livros com link afiliado pronto para você abrir e conferir manualmente na Amazon.

Quando houver preços oficiais verificados no futuro, a mesma área passa a mostrar `Top promoções de livros para hoje`. Passar o mouse sobre um card compacto mostra detalhes, link afiliado e ações rápidas para abrir a Amazon, copiar link ou ver/copiar a mensagem.

Preços, preços antigos e descontos só aparecem quando forem verificados por fonte oficial. O sistema não inventa promoção.

## Como Saber Se A Consulta Real Está Ativa?

Veja no dashboard, na seção `Status da Amazon`, ou use:

```powershell
curl.exe http://127.0.0.1:8000/integrations/amazon/status
```

Se `can_fetch_live_prices=false`, o sistema não está buscando preço real.

Estado esperado nesta V1:

```json
{
  "real_amazon_enabled": false,
  "can_fetch_live_prices": false,
  "can_detect_real_promotions": false,
  "safe_mode": true
}
```

## Endpoints Principais

```text
GET  /health
GET  /
GET  /docs
POST /manual-products/import-seed
GET  /manual-products
GET  /manual-products/ready
GET  /manual-products/{id}/message
PATCH /manual-products/{id}/asin
PATCH /manual-products/{id}/active
GET  /dashboard/summary
GET  /integrations/amazon/status
POST /prices/refresh
POST /prices/refresh/{id}
GET  /promotions
GET  /dynamic-products
GET  /exports/ready.json
GET  /exports/ready.csv
```

## Preços E Promoções

`Link pronto` significa apenas:

- produto ativo;
- ASIN preenchido;
- link afiliado gerado;
- mensagem pública disponível.

`Promoção verificada` só aparece quando houver:

- preço atual real;
- data/hora de verificação;
- desconto, valor de desconto ou badge de oferta vindo de fonte oficial.

Sem Creators API, `/prices/refresh` não inventa preço:

```powershell
curl.exe -X POST http://127.0.0.1:8000/prices/refresh `
  -H "Content-Type: application/json" `
  -d "{\"only_ready\":true,\"limit\":20}"
```

Resposta esperada na V1:

```json
{
  "live_prices_enabled": false,
  "updated": 0,
  "skipped": 7,
  "errors": [
    "Preço real não consultado: Creators API ainda não configurada/implementada."
  ]
}
```

## Exportações

Exporta produtos com link afiliado. Campos de preço só aparecem quando forem verificados por API oficial.

```powershell
curl.exe http://127.0.0.1:8000/exports/ready.json
curl.exe http://127.0.0.1:8000/exports/ready.csv
```

## Como Será A Integração Futura Com Creators API

Será necessário ter credenciais oficiais da Amazon e configurar:

- `AMAZON_CREATORS_API_ENABLED=true`
- `AMAZON_CREATORS_API_PUBLIC_KEY`
- `AMAZON_CREATORS_API_PRIVATE_KEY`
- `AMAZON_CREATORS_API_PARTNER_TAG`

A integração real deve usar somente documentação oficial da Amazon. Quando ativa, ela poderá preencher `current_price`, `discount_percent`, `availability`, `deal_badge` e `last_price_checked_at`.

O arquivo `app/amazon_live_prices.py` já existe como placeholder seguro. Ele não chama API real, não faz scraping e não simula preço.

## SQLite Local

O app tenta adicionar automaticamente as novas colunas de preço no SQLite local. Se um banco antigo ficar inconsistente durante desenvolvimento, apague `data/promos.db`, suba a API novamente e importe o seed:

```powershell
curl.exe -X POST http://127.0.0.1:8000/manual-products/import-seed
```

## Limitações

- Catálogo fixo/manual.
- Sem consulta real de preço nesta etapa.
- Sem detecção real de promoção nesta etapa.
- Sem Creators API real ainda.
- Sem PA-API.
- Sem scraping.
- Sem Instagram.
- Sem login de usuário.
