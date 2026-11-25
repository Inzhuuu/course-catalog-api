"""Passwords and tokens: no HTTP, only cryptography."""

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()  # Argon2id
# Hash of a “non-existent” password: verified when no user has this e-mail.
DUMMY_HASH = password_hash.hash("not-a-real-password")
