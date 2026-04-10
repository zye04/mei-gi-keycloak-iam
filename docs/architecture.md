# Architecture — RetailCorp IAM

## Visão Geral

Solução IAM baseada em **Keycloak** como Identity Provider (IdP) central, com OIDC para a aplicação web e Admin REST API para os fluxos JML. Toda a infraestrutura corre em Docker Compose.

---

## Diagrama de Componentes

```mermaid
graph TB
    subgraph Utilizadores
        U1["Colaborador interno\n(browser)"]
        U2["Fornecedor externo\n(browser)"]
        U3["Admin / HR\n(CLI + browser)"]
    end

    subgraph Docker Compose
        APP["RetailCorp Portal\nFastAPI :8000"]
        KC["Keycloak 26\nIdP / SSO :8080"]
        PG["PostgreSQL 16\n:5432"]
    end

    JML["JML Scripts\njml/joiner|mover|leaver.py\n(host ou CI)"]

    U1 -->|HTTPS| APP
    U2 -->|HTTPS| APP
    U3 -->|HTTPS| APP
    U3 -->|CLI| JML

    APP -->|OIDC Authorization Code| KC
    APP -->|Token Introspection / JWKS| KC

    JML -->|Admin REST API| KC

    KC --> PG
```

---

## Fluxo de Autenticação (OIDC Authorization Code + PKCE)

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as Portal (FastAPI)
    participant K as Keycloak

    B->>A: GET /login
    A->>B: Redirect → KC /auth?response_type=code&code_challenge=...
    B->>K: Credenciais (username + password)
    K-->>B: [se role exige TOTP] Prompt OTP
    B->>K: Código OTP
    K->>B: Redirect → /auth/callback?code=...
    B->>A: GET /auth/callback?code=...
    A->>K: POST /token {code, code_verifier, client_secret}
    K->>A: {access_token, id_token, refresh_token}
    A->>A: Valida JWT (JWKS), extrai realm_access.roles
    A->>B: Session cookie → Redirect /dashboard
```

---

## Fluxo de Autorização

Após autenticação, o access token JWT contém:

```json
{
  "sub": "uuid-do-utilizador",
  "preferred_username": "joao.silva",
  "email": "joao.silva@retailcorp.local",
  "realm_access": {
    "roles": ["cashier", "default-roles-retailcorp"]
  }
}
```

A aplicação valida a presença dos roles necessários antes de servir cada rota protegida.

---

## Fluxos JML

### Joiner

```mermaid
sequenceDiagram
    participant HR as HR / Admin
    participant S as jml/joiner.py
    participant K as Keycloak Admin API

    HR->>S: python joiner.py --username --email --role --dept
    S->>K: POST /admin/realms/retailcorp/users
    S->>K: PUT /users/{id}/reset-password (temporária)
    S->>K: POST /users/{id}/role-mappings/realm
    Note over S,K: Se role in [admin,hr,store_manager]
    S->>K: PUT /users/{id} requiredActions=[CONFIGURE_TOTP]
    K-->>S: 201 Created
    S-->>HR: ✓ Utilizador criado | username | temp-password
```

### Mover

```mermaid
sequenceDiagram
    participant HR as HR / Admin
    participant S as jml/mover.py
    participant K as Keycloak Admin API

    HR->>S: python mover.py --username --from-role --to-role
    S->>K: DELETE /users/{id}/role-mappings/realm [old]
    S->>K: POST /users/{id}/role-mappings/realm [new]
    S->>K: DELETE /users/{id}/sessions (revoga sessão ativa)
    Note over S,K: Se new_role exige TOTP
    S->>K: PUT /users/{id} requiredActions=[CONFIGURE_TOTP]
    K-->>S: 204 No Content
    S-->>HR: ✓ Role atualizado | sessões revogadas
```

### Leaver

```mermaid
sequenceDiagram
    participant HR as HR / Admin
    participant S as jml/leaver.py
    participant K as Keycloak Admin API

    HR->>S: python leaver.py --username
    S->>K: DELETE /users/{id}/sessions
    S->>K: DELETE /users/{id}/role-mappings/realm [all]
    S->>K: PUT /users/{id} {enabled: false}
    K-->>S: 204 No Content
    S-->>HR: ✓ Conta desativada | sessões revogadas
```

---

## Modelo de Dados — Keycloak Realm

```
Realm: retailcorp
│
├── Roles (realm)
│   ├── admin
│   ├── hr
│   ├── store_manager
│   ├── cashier
│   ├── warehouse
│   └── supplier
│
├── Groups
│   ├── /it
│   ├── /rh
│   ├── /lojas
│   ├── /armazem
│   └── /fornecedores
│
├── Clients
│   └── retailcorp-portal (confidential, OIDC)
│       ├── Standard Flow: enabled
│       ├── Redirect URIs: http://localhost:8000/*
│       └── Scopes: openid, profile, email, roles
│
└── Events
    ├── User Events: LOGIN, LOGIN_ERROR, LOGOUT, UPDATE_TOTP, ...
    └── Admin Events: CREATE, UPDATE, DELETE (users, roles, sessions)
```

---

## Estratégia de Auditoria

Dois níveis complementares:

| Nível | Origem | Conteúdo | Consulta |
|-------|--------|----------|---------|
| **Keycloak Events** | Keycloak (BD) | Login, logout, MFA, erros | Admin Console → Events |
| **App Audit Log** | FastAPI (ficheiro JSON) | Acessos a rotas protegidas, 403s | `/admin/audit` (role admin) |

### Eventos Keycloak configurados

- `LOGIN` / `LOGIN_ERROR`
- `LOGOUT`
- `UPDATE_TOTP` / `REMOVE_TOTP`
- `CODE_TO_TOKEN` / `REFRESH_TOKEN`
- Admin Events: `CREATE_USER`, `UPDATE_USER`, `DELETE_USER`, `UPDATE_ROLE_MAPPING`

---

## Infraestrutura

```mermaid
graph LR
    subgraph Host
        BR["Browser\n:8000 / :8080"]
        CLI["JML CLI\npython jml/*.py"]
    end

    subgraph Docker Compose Network
        APP["app\nFastAPI :8000"]
        KC["keycloak\n:8080"]
        PG["postgres\n:5432"]
    end

    BR --> APP
    BR --> KC
    CLI -->|localhost:8080| KC
    APP --> KC
    KC --> PG
```

### Reprodutibilidade

- `docker compose up` arranca todos os serviços
- Keycloak importa automaticamente `keycloak/realm-export.json` na primeira execução
- Variáveis sensíveis em `.env` (ver `.env.example`)

---

## Decisões Técnicas

Ver [docs/decisions/ADR-001-tech-stack.md](decisions/ADR-001-tech-stack.md)
