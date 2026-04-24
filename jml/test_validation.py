from client import get_client
import re

def test_logic():
    client = get_client()
    
    print("[*] Testando Geração de Password...")
    pw = client.generate_random_password()
    print(f"    Password gerada: {pw} (Tamanho: {len(pw)})")
    assert len(pw) == 16
    assert any(c.islower() for c in pw)
    assert any(c.isupper() for c in pw)
    assert any(c.isdigit() for c in pw)
    
    print("[*] Testando Validação de Email...")
    valid_email = "teste.user@retailcorp.local"
    invalid_email1 = "teste.user@gmail.com"
    invalid_email2 = "teste.user@retailcorp.com"
    
    print(f"    Validando {valid_email}: {client.validate_email(valid_email)}")
    assert client.validate_email(valid_email) is True
    
    print(f"    Validando {invalid_email1}: {client.validate_email(invalid_email1)}")
    assert client.validate_email(invalid_email1) is False
    
    print(f"    Validando {invalid_email2}: {client.validate_email(invalid_email2)}")
    assert client.validate_email(invalid_email2) is False

    print("\n[SUCCESS] Lógica de validação e segurança verificada com sucesso.")

if __name__ == "__main__":
    test_logic()
