import argparse
import sys
from client import get_client

def main():
    parser = argparse.ArgumentParser(description="RetailCorp JML: Mover - Alterar role e revogar sessões")
    parser.add_argument("--username", required=True, help="Username do colaborador")
    parser.add_argument("--from-role", required=True, help="Role antigo a remover")
    parser.add_argument("--to-role", required=True, 
                        choices=["admin", "hr", "store_manager", "cashier", "warehouse", "supplier"],
                        help="Novo role a atribuir")

    args = parser.parse_args()
    client = get_client()
    keycloak_admin = client.admin

    try:
        # 1. Obter ID do utilizador (centralizado no client)
        user_id = client.get_user_id(args.username)

        print(f"[*] A processar 'Mover' para '{args.username}'...")

        # 2. Remover Role antigo
        old_role_data = client.get_role(args.from_role, required=False)
        if old_role_data:
            try:
                keycloak_admin.delete_realm_roles_from_user(user_id, [old_role_data])
                print(f"[+] Role antigo '{args.from_role}' removido.")
            except Exception:
                print(f"[!] Aviso: Role '{args.from_role}' não estava atribuído.")
        else:
            print(f"[!] Aviso: Role antigo '{args.from_role}' não existe no Keycloak. A ignorar remoção.")

        # 3. Atribuir Novo Role
        new_role_data = client.get_role(args.to_role, required=True)
        keycloak_admin.assign_realm_roles(user_id, [new_role_data])
        print(f"[+] Novo role '{args.to_role}' atribuído.")

        # 4. Revogar sessões (Logout forçado)
        # Isto é CRÍTICO para que o novo role seja lido no próximo login
        keycloak_admin.logout_user(user_id)
        print("[+] Sessões ativas revogadas. O utilizador terá de fazer login novamente.")

        # 5. Se o novo role exigir MFA e o user não tiver, forçar configuração
        if args.to_role in client.MFA_REQUIRED_ROLES:
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
