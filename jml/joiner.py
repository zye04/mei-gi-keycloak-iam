import argparse
import sys
import logging
from keycloak import KeycloakPostError
from client import get_client, ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - JML-JOINER - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class JoinerError(Exception):
    pass


def process_joiner(username, email, first_name, last_name, role, client=None):
    """Lógica de negócio do Joiner — importável por endpoints FastAPI e testes."""
    if client is None:
        client = get_client()

    keycloak_admin = client.admin

    if not client.validate_email(email):
        raise JoinerError(f"Email inválido: '{email}'. Deve pertencer ao domínio {client.ALLOWED_EMAIL_DOMAIN}")

    logger.info(f"A iniciar processo Joiner para utilizador: {username}")

    try:
        user_id = keycloak_admin.create_user({
            "email": email,
            "username": username,
            "enabled": True,
            "firstName": first_name,
            "lastName": last_name,
            "emailVerified": True,
        }, exist_ok=False)

        logger.info(f"Utilizador '{username}' criado com sucesso (ID: {user_id})")

        temp_pass = client.generate_random_password()
        keycloak_admin.set_user_password(user_id, temp_pass, temporary=True)
        logger.info("Password temporária aleatória definida.")

        role_data = client.get_role(role)
        keycloak_admin.assign_realm_roles(user_id, [role_data])
        logger.info(f"Role '{role}' atribuído.")

        actions = ["UPDATE_PASSWORD"]
        if role in client.MFA_REQUIRED_ROLES:
            actions.append("CONFIGURE_TOTP")
            logger.info(f"Role sensível '{role}' detetado. MFA (TOTP) exigido.")

        keycloak_admin.update_user(user_id, {"requiredActions": actions})
        logger.info(f"Ações obrigatórias definidas: {actions}")

        return {
            "user_id": user_id,
            "username": username,
            "role": role,
            "temp_password": temp_pass,
            "required_actions": actions,
        }

    except KeycloakPostError as e:
        logger.error(f"Falha na API Keycloak ao criar utilizador: {e}")
        raise JoinerError(f"Falha na API Keycloak: {e}")
    except ClientError:
        raise
    except Exception as e:
        logger.critical(f"Erro inesperado no fluxo Joiner: {e}")
        raise JoinerError(f"Erro inesperado: {e}")


def main():
    parser = argparse.ArgumentParser(description="RetailCorp JML: Joiner - Criar novo utilizador")
    parser.add_argument("--username", required=True, help="Username do colaborador")
    parser.add_argument("--email", required=True, help="Email institucional (@retailcorp.local)")
    parser.add_argument("--first-name", required=True, help="Primeiro nome")
    parser.add_argument("--last-name", required=True, help="Apelido")
    parser.add_argument("--role", required=True,
                        choices=["admin", "hr", "store_manager", "cashier", "warehouse", "supplier"])
    parser.add_argument("--show-password", action="store_true",
                        help="Mostrar a password gerada no output (risco de segurança)")

    args = parser.parse_args()

    try:
        result = process_joiner(args.username, args.email, args.first_name, args.last_name, args.role)

        display_pass = result["temp_password"] if args.show_password else "******** (use --show-password para visualizar)"

        print("\n" + "=" * 50)
        print(f"SUCESSO: Colaborador '{args.username}' registado.")
        print(f"Username: {args.username}")
        print(f"Password Temporária: {display_pass}")
        print(f"Role: {args.role}")
        print("=" * 50)
        if not args.show_password:
            print("[INFO] Por segurança, a password está oculta. Use --show-password se necessário.")
        print("[AVISO] Partilhe a password de forma segura. O utilizador terá de a alterar no primeiro login.")

    except (JoinerError, ClientError) as e:
        logger.error(f"Falha na operação: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
