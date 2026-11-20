from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, password)

    except VerifyMismatchError:
        return False

    except VerificationError:
        return False


# print(hash_password("daston8747"))
# print(verify_password(password="daston8747",
#                       hashed_password="$argon2id$v=19$m=65536,t=3,p=4$90gOFyNywg+XLAlB5zCygg$tw35Xhuan1O0jWfe4m1C5aiLf4KKsTyoI+/OOnmA+zw"))
