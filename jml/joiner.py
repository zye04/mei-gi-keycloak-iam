import os
import argparse
import sys
from dotenv import load_dotenv
from keycloak import KeycloakAdmin, KeycloakPostError

# Carregar variáveis de ambiente da raiz do projeto
load_dotenv(dotenv_path="../.env")

def get_admin_client():
    """Configura a ligação à API Admin do Keycloak."""
    return KeycloakAdmin(
        server_url=os.getenv("KEYCLOAK_INTERNAL_URL"),
        username=os.getenv("KEYCLOAK_ADMIN_USER"),
        password=os.getenv("KEYCLOAK_ADMIN_PASSWORD"),
        realm_name=os.getenv("KEYCLOAK_REALM"),
        user_realm_name="master",  # Admin autentica no realm master
        verify=True
    )

def main():
    parser = argparse.ArgumentParser(description="RetailCorp JML: Joiner - Criar novo utilizador")
    parser.add_argument("--username", required=True, help="Username do colaborador")
    parser.add_argument("--email", required=True, help="Email institucional")
    parser.add_argument("--first-name", required=True, help="Primeiro nome")
    parser.add_argument("--last-name", required=True, help="Apelido")
    parser.add_argument("--role", required=True, 
                        choices=["admin", "hr", "store_manager", "cashier", "warehouse", "supplier"],
                        help="Role a atribuir")
    parser.add_argument("--temp-pass", default="RetailCorp2026!", help="Password temporária")

    args = parser.parse_args()

    keycloak_admin = get_admin_client()

    print(f"[*] A criar utilizador '{args.username}'...")

    try:
        # 1. Criar o utilizador
        new_user = keycloak_admin.create_user({
            "email": args.email,
            "username": args.username,
            "enabled": True,
            "firstName": args.first_name,
            "lastName": args.last_name,
            "emailVerified": True,
        }, exist_ok=False)

        user_id = new_user

        # 2. Definir password temporária
        keycloak_admin.set_user_password(user_id, args.temp_pass, temporary=True)
        print(f"[+] Password temporária definida: {args.temp_pass}")

        # 3. Atribuir Role
        role_data = keycloak_admin.get_realm_role(args.role)
        keycloak_admin.assign_realm_roles(user_id, [role_data])
        print(f"[+] Role '{args.role}' atribuído com sucesso.")

        # 4. Configurar MFA (TOTP) se o role for sensível
        sensitive_roles = ["admin", "hr", "store_manager"]
        if args.role in sensitive_roles:
            keycloak_admin.update_user(user_id, {
                "requiredActions": ["CONFIGURE_TOTP", "UPDATE_PASSWORD"]
            })
            print("[!] Role sensível detetado: MFA (TOTP) configurado como obrigatório.")
        else:
            keycloak_admin.update_user(user_id, {
                "requiredActions": ["UPDATE_PASSWORD"]
            })

        print(f"\n[SUCCESS] Utilizador '{args.username}' pronto para o primeiro login.")

    except KeycloakPostError as e:
        print(f"[ERROR] Falha ao criar utilizador: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
