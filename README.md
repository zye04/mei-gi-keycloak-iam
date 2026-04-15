# RetailCorp IAM — Keycloak Identity & Access Management

Trabalho Prático — UC Gestão de Identidade | MEI — ESTG-IPP | 2025/26

Solução IAM completa para um cenário de retalho fictício (**RetailCorp**), construída sobre **Keycloak** como Identity Provider central. Cobre autenticação OIDC, autorização baseada em roles, ciclo de vida de identidade (JML), MFA via TOTP e auditoria de eventos.

---

## Pré-requisitos

| Ferramenta | Versão mínima | Instalação |
|------------|---------------|------------|
| Docker Desktop | 4.x | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| Git | — | [git-scm.com](https://git-scm.com/) |

> Os scripts JML correm localmente em Python. A aplicação web e o Keycloak correm em Docker.

---

## Setup inicial

### 1. Clonar o repositório

```bash
git clone https://github.com/zye04/mei-gi-keycloak-iam.git
cd mei-gi-keycloak-iam
git checkout dev
```

### 2. Criar o ambiente virtual Python

```bash
python -m venv .venv

# Ativar (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Ativar (macOS / Linux / Git Bash)
source .venv/bin/activate
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Editar o `.env` e preencher os valores `CHANGE_ME`. Gerar passwords seguras com:

```bash
openssl rand -base64 32   # para passwords
openssl rand -hex 32      # para APP_SECRET_KEY
```

> `KEYCLOAK_CLIENT_SECRET` está pré-configurado com um valor fixo de desenvolvimento — não é necessário alterar.

### 4. Arrancar os serviços *(disponível a partir da Fase 2)*

```bash
docker compose up -d
```

O Keycloak importa automaticamente o realm `retailcorp` na primeira execução.
Os healthchecks garantem a ordem de arranque correcta (postgres → keycloak → app).

### 5. Verificar

- Portal: [http://localhost:8000](http://localhost:8000)
- Keycloak Admin Console: [http://localhost:8080/admin](http://localhost:8080/admin)

---

## Cenário

A **RetailCorp** é uma cadeia de retalho nacional com lojas físicas, armazém central e portal B2B para fornecedores externos. O sistema IAM gere o acesso de 6 perfis distintos de utilizadores com regras de autorização claras, fluxos de onboarding/offboarding automatizados e MFA obrigatório para roles sensíveis.

Ver [docs/use-case.md](docs/use-case.md) para o cenário detalhado, matriz de acesso e fluxos JML.

---

## Roles

| Role | Perfil |
|------|--------|
| `admin` | Administrador IT — acesso total |
| `hr` | Recursos Humanos — gestão JML |
| `store_manager` | Gerente de loja — relatórios, POS, inventário |
| `cashier` | Operador de caixa — POS |
| `warehouse` | Operador de armazém — inventário |
| `supplier` | Fornecedor externo — portal B2B |

---

## JML — Gestão de Ciclo de Vida *(disponível a partir da Fase 3)*

Os scripts correm localmente e ligam ao Keycloak em `localhost:8080`.

```bash
# Instalar dependências JML
cd jml && pip install -r requirements.txt

# Joiner — novo colaborador
python jml/joiner.py --username joao.silva --email joao.silva@retailcorp.local \
                     --first-name Joao --last-name Silva --role cashier

# Mover — promoção interna (revoga sessões + TOTP se necessário)
python jml/mover.py --username joao.silva --from-role cashier --to-role store_manager

# Leaver — saída de colaborador (desativa conta + revoga sessões)
python jml/leaver.py --username joao.silva --confirm
```

---

## Arquitetura

```
Browser ──── OIDC ────► RetailCorp Portal (FastAPI :8000)
                                │
                         Token validation
                                │
                                ▼
                        Keycloak 26 (:8080)  ◄── JML Scripts (CLI)
                                │
                          PostgreSQL 16
```

Ver [docs/architecture.md](docs/architecture.md) para diagramas detalhados de componentes, fluxos de autenticação, JML e estratégia de auditoria.

---

## Decisões Técnicas

| Componente | Escolha | Documento |
|------------|---------|-----------|
| Identity Provider | Keycloak 26 | [ADR-001](docs/decisions/ADR-001-tech-stack.md) |
| Base de dados | PostgreSQL 16 | [ADR-001](docs/decisions/ADR-001-tech-stack.md) |
| Aplicação web | FastAPI (Python 3.12) | [ADR-001](docs/decisions/ADR-001-tech-stack.md) |
| Cliente OIDC | authlib | [ADR-001](docs/decisions/ADR-001-tech-stack.md) |
| Scripts JML | python-keycloak | [ADR-001](docs/decisions/ADR-001-tech-stack.md) |

---

## Branches e Fluxo de Trabalho

| Branch | Propósito |
|--------|-----------|
| `main` | Código estável — merges via PR no final de cada fase |
| `dev` | Branch de desenvolvimento ativo |

```bash
# Trabalhar sempre a partir de dev
git checkout dev
git pull origin dev

# Criar branch para uma feature/issue
git checkout -b feat/oidc-login

# Após concluir, abrir PR para dev
```

---

## Planeamento

Backlog organizado em milestones e issues no [GitHub](https://github.com/zye04/mei-gi-keycloak-iam/issues).

| Fase | Conteúdo | Milestone |
|------|----------|-----------|
| 1 — Arranque e arquitetura | Use case, ADR, arquitetura | [Fase 1](https://github.com/zye04/mei-gi-keycloak-iam/milestone/1) |
| 2 — Implementação base | Keycloak realm, OIDC, login/dashboard | [Fase 2](https://github.com/zye04/mei-gi-keycloak-iam/milestone/2) |
| 3 — Autorização + JML | Rotas protegidas, scripts Joiner/Mover/Leaver | [Fase 3](https://github.com/zye04/mei-gi-keycloak-iam/milestone/3) |
| 4 — MFA + auditoria | TOTP, event logging, audit dashboard | [Fase 4](https://github.com/zye04/mei-gi-keycloak-iam/milestone/4) |
| 5 — Preparação da demo | Guião, checklist, relatório | [Fase 5](https://github.com/zye04/mei-gi-keycloak-iam/milestone/5) |

**Entrega:** 28 de maio de 2026

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [docs/use-case.md](docs/use-case.md) | Cenário RetailCorp, roles, matriz de acesso, fluxos JML |
| [docs/architecture.md](docs/architecture.md) | Componentes, fluxos OIDC, JML, auditoria |
| [docs/decisions/ADR-001-tech-stack.md](docs/decisions/ADR-001-tech-stack.md) | Decisões técnicas fundamentadas |
