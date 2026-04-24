import argparse
import sys
import logging
from keycloak import KeycloakError
from client import get_client

# Configuração de Logs Estruturados
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - JML-LEAVER - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class LeaverError(Exception):
    """Exceção customizada para o fluxo Leaver."""
    pass

def process_leaver(username, confirm=False, client=None):
    """Lógica principal do processo de saída (Offboarding)."""
    if not confirm:
        logger.warning(f"Tentativa de desativar '{username}' sem confirmação.")
        return False

    if client is None:
        client = get_client()
    
    keycloak_admin = client.admin

    try:
        # 1. Obter ID do utilizador
        user_id = client.get_user_id(username)
        logger.info(f"A iniciar processo Leaver para '{username}' (ID: {user_id}).")

        # 2. Desativar a conta (Passo Crítico)
        keycloak_admin.update_user(user_id, {"enabled": False})
        logger.info("Conta desativada (enabled: false).")

        # 3. Revogar todas as sessões ativas
        keycloak_admin.user_logout(user_id)
        logger.info("Todas as sessões ativas foram revogadas.")

        # 4. Limpeza de Privilégios (Remover todos os Roles)
        user_roles = keycloak_admin.get_realm_roles_of_user(user_id)
        # Filtrar roles que não podem/devem ser removidos (como os de sistema, se existirem)
        roles_to_remove = [r for r in user_roles if r['name'] not in ['offline_access', 'uma_authorization']]
        
        if roles_to_remove:
            keycloak_admin.delete_realm_roles_of_user(user_id, roles_to_remove)
            logger.info(f"Removidos {len(roles_to_remove)} roles de realm.")

        return True

    except KeycloakError as e:
        logger.error(f"Erro na API Keycloak durante o processo Leaver: {e}")
        raise LeaverError(f"Falha ao desativar utilizador no Keycloak: {e}")
    except Exception as e:
        logger.critical(f"Erro inesperado no processo Leaver: {e}")
        raise LeaverError(f"Erro interno: {e}")

def main():
    parser = argparse.ArgumentParser(description="RetailCorp JML: Leaver - Offboarding seguro")
    parser.add_argument("--username", required=True, help="Username do colaborador")
    parser.add_argument("--confirm", action="store_true", help="Confirmar desativação definitiva")

    args = parser.parse_args()

    if not args.confirm:
        print(f"\n[!] AVISO: A conta de '{args.username}' será desativada e todos os acessos revogados.")
        print("Use a flag --confirm para executar a operação.")
        sys.exit(0)

    try:
        if process_leaver(args.username, confirm=True):
            logger.info(f"SUCESSO: O colaborador '{args.username}' foi removido do sistema.")
    except LeaverError as e:
        logger.error(f"Operação abortada: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
