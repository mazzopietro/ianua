from ianua.core.security import (
    hash_password,
    verify_password,
    generate_refresh_token,
    hash_refresh_token,
)

def test_password_hash_is_not_plaintext():
    password = "Password123!"

    hashed = hash_password(password)

    assert hashed != password

def test_password_hashes_are_different_for_same_password():
    password = "Password123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash

def test_verify_password():
    password = "Password123!"
    
    hashed = hash_password(password)

    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword!", hashed)

def test_refresh_tokens_are_random():
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second

def test_refresh_token_hash_is_deterministic():
    token = generate_refresh_token()

    first_hash = hash_refresh_token(token)
    second_hash = hash_refresh_token(token)

    assert first_hash == second_hash

def test_refresh_token_hash_is_not_plaintext():
    token = generate_refresh_token()

    hashed = hash_refresh_token(token)

    assert hashed != token