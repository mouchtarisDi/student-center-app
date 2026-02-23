# Αυτό είναι το “ασφαλές κομμάτι” για passwords και tokens. 
# Κανένα password δεν αποθηκεύεται ως απλό κείμενο, μόνο ως bcrypt hash. 
# Στο login γίνεται verify του password με το hash. Μετά δημιουργούμε JWT token με λήξη (exp), 
# μέσα στο οποίο βάζουμε το sub (username) και το role. Σε κάθε request, 
# θα κάνουμε decode και verify το token. Αυτό κρατάει το auth απλό, χωρίς sessions/cookies, 
# και είναι τέλειο για MVP/portfolio. Το SECRET_KEY πρέπει να είναι διαφορετικό/μυστικό 
# σε πραγματικό deployment (ιδανικά env var), αλλά για dev είναι εντάξει να το έχεις εδώ.

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
import jwt

# ΣΗΜΑΝΤΙΚΟ:
# - Σε production, το SECRET_KEY ΠΡΕΠΕΙ να έρχεται από env var (μην το κάνεις hardcode).
# - Αν αλλάξει το SECRET_KEY, τα παλιά tokens παύουν να είναι έγκυρα (λογικό/επιθυμητό).
SECRET_KEY = os.getenv("SECRET_KEY", "Dimouch.220133_2004.studentcenterapp!?")  # ΠΡΟΣΟΧΗ: Μην χρησιμοποιείς αυτό το default σε production!
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


def create_access_token(subject: str, role: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=expires_minutes)
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None