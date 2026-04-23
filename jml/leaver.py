import os
import argparse
import sys
from dotenv import load_dotenv
from keycloak import KeycloakAdmin

# Carregar variáveis de ambiente
load_dotenv(dotenv_path="../.env")

def get_admin_client():
    return KeycloakAdmin(
        server_url=os.getenv("KEYCLOAK_INTERNAL_URL"),
        username=os.getenv("KEYCLOAK_ADMIN_USER"),
        password=os.getenv("KEYCLOAK_ADMIN_PASSWORD"),
        realm_name=os.getenv("KEYCLOAK_REALM"),
        user_realm_name="master",
        verify=True
    )

def main():
    parser = argparse.ArgumentParser(description="RetailCorp JML: Leaver - Desativar colaborador")
    parser.add_argument("--username", required=True, help="Username do colaborador")
    parser.add_argument("--confirm", action="store_true", help="Confirmar a desativação")

    args = parser.parse_args()

    if not args.confirm:
        print(f"[!] Aviso: Para desativar '{args.username}', use a flag --confirm.")
        sys.exit(0)

    keycloak_admin = get_admin_client()

    try:
        # 1. Obter ID do utilizador
        user_id = keycloak_admin.get_user_id(args.username)
        if not user_id:
            print(f"[ERROR] Utilizador '{args.username}' não encontrado.")
            sys.exit(1)

        print(f"[*] A processar 'Leaver' para '{args.username}'...")

        # 2. Desativar a conta
        keycloak_admin.update_user(user_id, {"enabled": False})
        print("[+] Conta desativada (enabled: false).")

        # 3. Revogar todas as sessões
        keycloak_admin.logout_user(user_id)
        print("[+] Todas as sessões ativas foram revogadas.")

        # 4. Remover todos os Roles de Realm (limpeza de privilégios)
        user_roles = keycloak_admin.get_realm_roles_of_user(user_id)
        if user_roles:
            keycloak_admin.delete_realm_roles_from_user(user_id, user_roles)
            print(f"[+] Removidos {len(user_roles)} roles do utilizador.")

        print(f"\n[SUCCESS] O colaborador '{args.username}' foi desativado com sucesso.")

    except Exception as e:
        print(f"[ERROR] Falha na operação Leaver: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
