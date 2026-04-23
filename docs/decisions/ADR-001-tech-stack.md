# ADR-001 — Seleção do Tech Stack

## Contexto

É necessário selecionar as tecnologias para construir a solução IAM RetailCorp que:

- Cumpra todos os requisitos do TP (OIDC, TOTP, JML, auditoria)
- Seja reproduzível via `docker compose up`
- Permita uma demo eficaz em 10 minutos
- Seja implementável dentro do prazo (entrega 28 mai 2026)
- Não contenha secrets em código

---

## Decisões

### Identity Provider: Keycloak 26.2

**Escolhido porque:**
- Requisito explícito do enunciado do TP
- Fornece out-of-the-box: OIDC, TOTP, Admin REST API, Event Logging
- Imagem Docker oficial (`quay.io/keycloak/keycloak`)
- Suporte a import/export de realm para reprodutibilidade

**Versão 26.2:** última versão estável no início do projeto (março 2026)

### Base de Dados: PostgreSQL 16

**Escolhido porque:**
- Suporte de produção para o Keycloak (alternativa ao H2 in-memory)
- Necessário para persistência entre reinicios
- Imagem Alpine disponível (menor footprint)
- Requerido para `docker compose up` ser totalmente reproduzível

### Aplicação Web: FastAPI (Python 3.12)

**Escolhido porque:**
- Framework Python moderno e assíncrono
- Swagger UI automático (OpenAPI) — útil para demo de endpoints protegidos
- Suporte nativo a Jinja2 para web UI
- Integração direta com `authlib` para OIDC
- Tipagem forte com Pydantic (configuração validada no arranque)

**Alternativas descartadas:**
- Express (Node.js) — maior complexidade de setup para o mesmo resultado
- Spring Boot — overhead desnecessário para um projeto académico
- Flask — menos ergonómico para API REST + web UI em simultâneo

### Cliente OIDC: authlib

**Escolhido porque:**
- Implementação mais completa de OAuth2/OIDC para Python
- Integração nativa com Starlette (base do FastAPI)
- Suporta PKCE, discovery automático via `.well-known`, refresh token
- Mantido ativamente

### Scripts JML: python-keycloak

**Escolhido porque:**
- Wrapper de alto nível sobre a Keycloak Admin REST API
- Reduz boilerplate de autenticação e gestão de tokens de admin
- Suporta todas as operações necessárias: criar/atualizar/desativar utilizadores, roles, sessões
- CLI simples via `argparse`

**Alternativas:**
- Chamadas diretas HTTP com `httpx` — mais verboso, mais controlo; usado como fallback se necessário

---

## Consequências

- Stack totalmente em Python — coerência entre app e scripts JML
- Keycloak Admin Console disponível em `:8080` para debug e inspeção
- Sem app mobile no âmbito (mantém demo focada)
- Client secret do OIDC client está pré-configurado com valor fixo de desenvolvimento no `realm-export.json` e `.env.example` — `docker compose up` é totalmente reproduzível sem passos manuais
