# SQL migrations / one-off scripts

## 001_kb_vector.sql

Tworzy rozszerzenie `vector` i tabelę `kb_chunks` dla RAG (runbooki i postmortemy). **Uruchom raz** po starcie Postgresa.

### Z repo root

**Opcja A — przez kontener (bez psql na hoście):**

```bash
docker exec -i spaceops-postgres psql -U spaceops -d spaceops < infra/sql/001_kb_vector.sql
```

**Opcja B — z hosta (gdy masz zainstalowane `psql`):**

```bash
# Hasło z .env (POSTGRES_PASSWORD)
psql -h localhost -p 5432 -U spaceops -d spaceops -f infra/sql/001_kb_vector.sql
```

Jeśli w `.env` masz inne `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`, użyj tych wartości w powyższych poleceniach.

### Po uruchomieniu

Zaindeksuj KB: `python -m apps.mcp.kb_server.index_kb` (wymaga `.env` z `OPENAI_API_KEY` i działającego Postgresa).
