import argparse
import sys
import logging
import json
from datetime import datetime
from keycloak import KeycloakError
from client import get_client

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - JML-LEAVER - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class LeaverError(Exception):
    """Exceção para erros no fluxo Leaver."""
    pass

def process_leaver(username, confirm=False, dry_run=False, client=None):
    """
    Processo de Offboarding com Auditoria e Dry-run.
    """
    if client is None:
        client = get_client()
    
    keycloak_admin = client.admin
    audit_trail = {
        "timestamp": datetime.now().isoformat(),
        "operator_action": "LEAVER_PROCESS",
        "target_user": username,
        "dry_run": dry_run,
        "steps": []
    }

    try:
        # 1. Obter utilizador e validar criticidade
        user_id = client.get_user_id(username)
        user_info = keycloak_admin.get_user(user_id)
        user_roles = [r['name'] for r in keycloak_admin.get_realm_roles_of_user(user_id)]

        if "admin" in user_roles and not dry_run:
            logger.warning(f"ALERTA: Tentativa de desativar conta de ADMINISTRADOR: {username}")
            # Aqui poderíamos exigir uma flag extra ou validação manual

        # 2. Desativação
        audit_trail["steps"].append({"action": "disable_account", "status": "pending"})
        if not dry_run:
            keycloak_admin.update_user(user_id, {"enabled": False})
            logger.info(f"Account disabled: {username}")
        audit_trail["steps"][-1]["status"] = "simulated" if dry_run else "success"

        # 3. Logout (Revogação de Sessões)
        audit_trail["steps"].append({"action": "revoke_sessions", "status": "pending"})
        if not dry_run:
            keycloak_admin.user_logout(user_id)
            logger.info(f"Sessions revoked: {username}")
        audit_trail["steps"][-1]["status"] = "simulated" if dry_run else "success"

        # 4. Remoção de Roles
        roles_to_remove = [r for r in keycloak_admin.get_realm_roles_of_user(user_id) 
                           if r['name'] not in ['offline_access', 'uma_authorization']]
        
        audit_trail["steps"].append({
            "action": "remove_roles", 
            "roles": [r['name'] for r in roles_to_remove],
            "status": "pending"
        })
        
        if roles_to_remove and not dry_run:
            keycloak_admin.delete_realm_roles_of_user(user_id, roles_to_remove)
            logger.info(f"Removed {len(roles_to_remove)} roles from {username}")
        audit_trail["steps"][-1]["status"] = "simulated" if dry_run else "success"

        # 5. Output da Auditoria
        if dry_run:
            logger.info("--- MODO DRY-RUN: Nenhuma alteração foi persistida no Keycloak ---")
        
        print("\n" + "="*60)
        print("RELATÓRIO DE AUDITORIA DE OFFBOARDING")
        print("="*60)
        print(json.dumps(audit_trail, indent=2))
        print("="*60)

        return True

    except KeycloakError as e:
        logger.error(f"Erro na API Keycloak: {e}")
        raise LeaverError(f"Falha técnica no offboarding: {e}")
    except Exception as e:
        logger.critical(f"Erro inesperado: {e}")
        raise LeaverError(f"Erro interno: {e}")

def main():
    parser = argparse.ArgumentParser(description="RetailCorp JML: Leaver - Offboarding Auditável")
    parser.add_argument("--username", required=True)
    parser.add_argument("--confirm", action="store_true", help="Confirmar execução real")
    parser.add_argument("--dry-run", action="store_true", help="Simular operação sem alterar dados")

    args = parser.parse_args()

    if not args.confirm and not args.dry_run:
        logger.error("Deve especificar --confirm para execução real ou --dry-run para simulação.")
        sys.exit(1)

    try:
        process_leaver(args.username, confirm=args.confirm, dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Falha: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
