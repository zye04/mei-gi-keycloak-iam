# Use Case — RetailCorp Portal

## Contexto

A **RetailCorp** é uma cadeia de retalho nacional fictícia com:
- Lojas físicas distribuídas pelo país
- Um armazém central de logística
- Um portal B2B para fornecedores externos
- Departamento de RH centralizado

Este cenário serve de base ao trabalho prático da UC de Gestão de Identidade (MEI — ESTG-IPP).

---

## Atores e Perfis

| Role (Keycloak) | Perfil | Localização típica |
|-----------------|--------|-------------------|
| `admin` | Administrador de IT | Back-office central |
| `hr` | Técnico de Recursos Humanos | Sede central |
| `store_manager` | Gerente de loja | Loja física |
| `cashier` | Operador de caixa | Loja física |
| `warehouse` | Operador de armazém | Armazém central |
| `supplier` | Representante de fornecedor | Externo (B2B portal) |

---

## Matriz de Acesso

| Recurso / Módulo | admin | hr | store_manager | cashier | warehouse | supplier |
|------------------|:-----:|:--:|:-------------:|:-------:|:---------:|:--------:|
| Página pública / homepage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Dashboard pessoal (claims) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ponto de venda (POS) | ✓ | — | ✓ | ✓ | — | — |
| Gestão de inventário | ✓ | — | ✓ | — | ✓ | — |
| Relatórios financeiros de loja | ✓ | — | ✓ | — | — | — |
| Portal de fornecedores (B2B) | ✓ | — | — | — | — | ✓ |
| Dados de colaboradores (RH) | ✓ | ✓ | — | — | — | — |
| Gestão de utilizadores (JML) | ✓ | ✓ | — | — | — | — |
| Painel de auditoria & logs | ✓ | — | — | — | — | — |

---

## Fluxos JML Representativos

### Joiner — Novo Colaborador

1. HR cria utilizador no Keycloak via `jml/joiner.py`
2. Atribui role inicial consoante o departamento (ex: `cashier` para nova contratação de loja)
3. Para roles sensíveis (`admin`, `hr`, `store_manager`), o TOTP é definido como Required Action
4. Utilizador recebe credenciais temporárias e é obrigado a alterar a password no primeiro login

### Mover — Promoção Interna

**Cenário concreto:** Cashier promovido a Store Manager

1. HR executa `jml/mover.py --username joao.silva --from cashier --to store_manager`
2. Script remove role `cashier`, atribui `store_manager`
3. Sessões ativas são revogadas imediatamente (o utilizador é forçado a re-autenticar)
4. No novo login, é exigida a configuração de TOTP (Required Action)
5. Novo acesso reflete imediatamente as novas permissões

### Leaver — Saída de Colaborador

**Cenário concreto:** Operador de armazém rescinde contrato

1. HR executa `jml/leaver.py --username maria.santos`
2. Script revoga todas as sessões ativas
3. Remove todas as roles do utilizador
4. Desativa a conta (enabled: false)
5. Acesso bloqueado imediatamente sem eliminar o histórico de auditoria

---

## Estratégia de MFA

| Role | Política TOTP |
|------|---------------|
| `admin` | Obrigatório — Required Action no onboarding |
| `hr` | Obrigatório — Required Action no onboarding |
| `store_manager` | Obrigatório — Required Action após promoção |
| `cashier` | Opcional — pode configurar voluntariamente |
| `warehouse` | Opcional — pode configurar voluntariamente |
| `supplier` | Opcional — pode configurar voluntariamente |

---

## Eventos de Auditoria Relevantes

| Evento | Origem | Importância |
|--------|--------|-------------|
| Login bem-sucedido | Keycloak | Rastreio de acesso |
| Login falhado (> 3x) | Keycloak | Alerta de segurança |
| Logout / expiração de sessão | Keycloak | Ciclo de sessão |
| Configuração de TOTP | Keycloak | Onboarding MFA |
| Alteração de role (admin event) | Keycloak | Mudança de privilégios |
| Criação / desativação de utilizador | Keycloak | Ciclo JML |
| Acesso negado (403) | App | Violação de autorização |
| Acesso a relatórios financeiros | App | Dado sensível |
