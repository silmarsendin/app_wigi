import bcrypt

password = "Teste123"

password_hash = bcrypt.hashpw(
    password.encode("utf-8"),
    bcrypt.gensalt()
)

print(password_hash.decode("utf-8"))