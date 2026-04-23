import os
import argparse
import sys
from dotenv import load_dotenv
from keycloak import KeycloakAdmin, KeycloakGetError

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
    parser = argparse.ArgumentParser(description="RetailCorp JML: Mover - Alterar role e revogar sessões")
    parser.add_argument("--username", required=True, help="Username do colaborador")
    parser.add_argument("--from-role", required=True, help="Role antigo a remover")
    parser.add_argument("--to-role", required=True, 
                        choices=["admin", "hr", "store_manager", "cashier", "warehouse", "supplier"],
                        help="Novo role a atribuir")

    args = parser.parse_args()
    keycloak_admin = get_admin_client()

    try:
        # 1. Obter ID do utilizador
        user_id = keycloak_admin.get_user_id(args.username)
        if not user_id:
            print(f"[ERROR] Utilizador '{args.username}' não encontrado.")
            sys.exit(1)

        print(f"[*] A processar 'Mover' para '{args.username}'...")

        # 2. Remover Role antigo
        try:
            old_role_data = keycloak_admin.get_realm_role(args.from_role)
            keycloak_admin.delete_realm_roles_from_user(user_id, [old_role_data])
            print(f"[+] Role antigo '{args.from_role}' removido.")
        except Exception:
            print(f"[!] Aviso: Role '{args.from_role}' não estava atribuído ou não existe.")

        # 3. Atribuir Novo Role
        new_role_data = keycloak_admin.get_realm_role(args.to_role)
        keycloak_admin.assign_realm_roles(user_id, [new_role_data])
        print(f"[+] Novo role '{args.to_role}' atribuído.")

        # 4. Revogar sessões (Logout forçado)
        # Isto é CRÍTICO para que o novo role seja lido no próximo login
        keycloak_admin.logout_user(user_id)
        print("[+] Sessões ativas revogadas. O utilizador terá de fazer login novamente.")

        # 5. Se o novo role exigir MFA e o user não tiver, forçar configuração
        sensitive_roles = ["admin", "hr", "store_manager"]
        if args.to_role in sensitive_roles:
            keycloak_admin.update_user(user_id, {
                "requiredActions": ["CONFIGURE_TOTP"]
            })
            print("[!] Novo role sensível: Configuração de MFA (TOTP) será exigida.")

        print(f"\n[SUCCESS] Utilizador '{args.username}' movido para '{args.to_role}' com sucesso.")

    except Exception as e:
        print(f"[ERROR] Falha na operação Mover: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
