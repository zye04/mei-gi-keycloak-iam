import argparse
import sys
import logging
from keycloak import KeycloakGetError, KeycloakPostError, KeycloakError
from client import get_client

# Configuração de Logs Estruturados
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - JML-MOVER - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class MoverError(Exception):
    """Exceção customizada para erros de negócio no fluxo Mover."""
    pass

def process_mover(username, from_role_name, to_role_name, client=None):
    """Lógica principal isolada para facilitar testes unitários."""
    if client is None:
        client = get_client()
    
    keycloak_admin = client.admin

    # 1. Validação de Política de Transição
    allowed_targets = client.ROLE_TRANSITIONS.get(from_role_name, [])
    if to_role_name not in allowed_targets and from_role_name != to_role_name:
        raise MoverError(f"Transição proibida pela política: {from_role_name} -> {to_role_name}")

    try:
        # 2. Obter ID e estado do utilizador
        user_id = client.get_user_id(username)
        user_info = keycloak_admin.get_user(user_id)
        
        if not user_info.get("enabled"):
            raise MoverError(f"Utilizador '{username}' está desativado.")

        # 3. Validar existência dos Roles
        old_role = client.get_role(from_role_name, required=True)
        new_role = client.get_role(to_role_name, required=True)

        # 4. Verificar se possui o role antigo
        user_roles = keycloak_admin.get_realm_roles_of_user(user_id)
        user_role_names = [r['name'] for r in user_roles]
        
        if from_role_name not in user_role_names:
            logger.warning(f"Utilizador não possui o role '{from_role_name}'. Roles atuais: {user_role_names}")

        # --- EXECUÇÃO ---
        
        # 5. Atribuir Novo Role
        keycloak_admin.assign_realm_roles(user_id, [new_role])
        logger.info(f"Novo role '{to_role_name}' atribuído.")

        # 6. Remover Role Antigo com Rollback
        try:
            keycloak_admin.delete_realm_roles_of_user(user_id, [old_role])
            logger.info(f"Role antigo '{from_role_name}' removido.")
        except KeycloakError as e:
            logger.error(f"Falha ao remover role antigo. A tentar reverter (rollback)... Erro: {e}")
            try:
                keycloak_admin.delete_realm_roles_of_user(user_id, [new_role])
                logger.info("Rollback concluído: Novo role removido.")
            except Exception as rollback_err:
                logger.critical(f"ERRO CRÍTICO: Falha no rollback! Utilizador '{username}' pode ter múltiplos roles.")
                logger.critical("A aplicar política de emergência: DESATIVAR CONTA.")
                keycloak_admin.update_user(user_id, {"enabled": False})
                raise MoverError(f"Inconsistência grave. Conta desativada por segurança. Erro: {rollback_err}")
            
            raise MoverError(f"Transição falhou, mas o rollback foi efetuado: {e}")

        # 7. Validação Pós-Operação
        final_roles = keycloak_admin.get_realm_roles_of_user(user_id)
        final_role_names = [r['name'] for r in final_roles]
        if to_role_name not in final_role_names:
            raise MoverError("Falha na validação final: Novo role não encontrado no utilizador.")

        # 8. Required Actions
        current_actions = user_info.get("requiredActions", [])
        if to_role_name in client.MFA_REQUIRED_ROLES and "CONFIGURE_TOTP" not in current_actions:
            new_actions = list(current_actions) + ["CONFIGURE_TOTP"]
            keycloak_admin.update_user(user_id, {"requiredActions": new_actions})
            logger.info("MFA (TOTP) exigido para o novo role.")

        # 9. Logout
        keycloak_admin.user_logout(user_id)
        return True

    except (KeycloakGetError, KeycloakPostError) as e:
        logger.error(f"Erro na API Keycloak: {e}")
        raise MoverError(f"Erro de comunicação com Keycloak: {e}")

def main():
    parser = argparse.ArgumentParser(description="RetailCorp JML: Mover - Transição segura de roles")
    parser.add_argument("--username", required=True)
    parser.add_argument("--from-role", required=True)
    parser.add_argument("--to-role", required=True)

    args = parser.parse_args()

    try:
        process_mover(args.username, args.from_role, args.to_role)
        logger.info(f"SUCESSO: Utilizador '{args.username}' movido para '{args.to_role}'.")
    except MoverError as e:
        logger.error(f"Falha na operação: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
