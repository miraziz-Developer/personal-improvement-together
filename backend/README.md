# Personal Improvement Together — backend

FastAPI + DDD modular monolith. Product spec: [`../docs/PRD.md`](../docs/PRD.md).

## Ishga tushirish

```bash
docker compose up -d --wait postgres redis    # loyiha ildizida; portlar 5433 / 6380
cd backend
uv sync
cp .env.example .env                          # PIT_DAILY_CODE_SECRET ni o'zgartiring
uv run alembic upgrade head
```

## Tekshiruvlar

```bash
uv run pytest            # unit + application + Postgres integratsion testlar
uv run mypy              # strict
uv run ruff check .
uv run lint-imports      # DDD arxitektura qoidalari
```

Integratsion testlar `pit_test` bazasidan foydalanadi (compose birinchi ishga tushganda yaratiladi)
va Postgres ishlamasa o'tkazib yuboriladi.

## Tuzilma

```
src/pit/
  shared/            AggregateRoot, DomainEvent, Money, UnitOfWork, MessageBus, SQL repository asosi
  modules/<modul>/
    domain/          sof Python: qoidalar, aggregate'lar, eventlar
    application/     use-case'lar (command/event handler'lar), portlar
    infrastructure/  jadvallar, SQL repository'lar
  infrastructure/    SqlAlchemyUnitOfWork, sxema (barcha jadvallar)
  bootstrap.py       composition root
migrations/          Alembic
```

Modullar: `identity`, `challenges`, `verification`, `wallet`, `ranking`, `planning`.
Bog'liqlik yo'nalishi: `ranking | wallet | verification | planning → challenges → identity`.
