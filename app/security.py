# Αυτό είναι το “ασφαλές κομμάτι” για passwords και tokens. 
# Κανένα password δεν αποθηκεύεται ως απλό κείμενο, μόνο ως bcrypt hash. 
# Στο login γίνεται verify του password με το hash. Μετά δημιουργούμε JWT token με λήξη (exp), 
# μέσα στο οποίο βάζουμε το sub (username) και το role. Σε κάθε request, 
# θα κάνουμε decode και verify το token. Αυτό κρατάει το auth απλό, χωρίς sessions/cookies, 
# και είναι τέλειο για MVP/portfolio. Το SECRET_KEY πρέπει να είναι διαφορετικό/μυστικό 
# σε πραγματικό deployment (ιδανικά env var), αλλά για dev είναι εντάξει να το έχεις εδώ.

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
import jwt

SECRET_KEY = "Dimouch.220133_2004!?"  # για production: env var
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
