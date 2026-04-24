import argparse
import sys
import logging
from keycloak import KeycloakPostError
from client import get_client

# Configuração de Logs Estruturados
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - JML-JOINER - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="RetailCorp JML: Joiner - Criar novo utilizador")
    parser.add_argument("--username", required=True, help="Username do colaborador")
    parser.add_argument("--email", required=True, help="Email institucional (@retailcorp.local)")
    parser.add_argument("--first-name", required=True, help="Primeiro nome")
    parser.add_argument("--last-name", required=True, help="Apelido")
    parser.add_argument("--role", required=True, 
                        choices=["admin", "hr", "store_manager", "cashier", "warehouse", "supplier"],
                        help="Role a atribuir")
    parser.add_argument("--show-password", action="store_true", help="Mostrar a password gerada no output (risco de segurança)")

    args = parser.parse_args()

    client = get_client()
    keycloak_admin = client.admin

    # 1. Validação Forte de Inputs
    if not client.validate_email(args.email):
        logger.error(f"Email inválido: '{args.email}'. Deve pertencer ao domínio {client.ALLOWED_EMAIL_DOMAIN}")
        sys.exit(1)

    logger.info(f"A iniciar processo Joiner para utilizador: {args.username}")

    try:
        # 2. Criar o utilizador
        new_user = keycloak_admin.create_user({
            "email": args.email,
            "username": args.username,
            "enabled": True,
            "firstName": args.first_name,
            "lastName": args.last_name,
            "emailVerified": True,
        }, exist_ok=False)

        user_id = new_user
        logger.info(f"Utilizador '{args.username}' criado com sucesso (ID: {user_id})")

        # 3. Gerar password temporária aleatória
        temp_pass = client.generate_random_password()
        keycloak_admin.set_user_password(user_id, temp_pass, temporary=True)
        # Nota: Password NUNCA é registada nos logs
        logger.info("Password temporária aleatória definida.")

        # 4. Atribuir Role
        role_data = client.get_role(args.role)
        keycloak_admin.assign_realm_roles(user_id, [role_data])
        logger.info(f"Role '{args.role}' atribuído.")

        # 5. Configurar Required Actions (MFA e Password Update)
        actions = ["UPDATE_PASSWORD"]
        if args.role in client.MFA_REQUIRED_ROLES:
            actions.append("CONFIGURE_TOTP")
            logger.info(f"Role sensível '{args.role}' detetado. MFA (TOTP) exigido.")
        
        keycloak_admin.update_user(user_id, {"requiredActions": actions})
        logger.info(f"Ações obrigatórias definidas: {actions}")

        # Output final para o operador (com a password controlada por flag)
        display_pass = temp_pass if args.show_password else "******** (use --show-password para visualizar)"
        
        print("\n" + "="*50)
        print(f"SUCESSO: Colaborador '{args.username}' registado.")
        print(f"Username: {args.username}")
        print(f"Password Temporária: {display_pass}")
        print(f"Role: {args.role}")
        print("="*50)
        if not args.show_password:
            print("[INFO] Por segurança, a password está oculta. Use --show-password se necessário.")
        print("[AVISO] Partilhe a password de forma segura. O utilizador terá de a alterar no primeiro login.")

    except KeycloakPostError as e:
        logger.error(f"Falha na API Keycloak ao criar utilizador: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Erro inesperado no fluxo Joiner: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
