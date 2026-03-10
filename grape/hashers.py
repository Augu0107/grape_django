"""
Custom password hasher for Grape.
Handles PHP bcrypt hashes ($2y$...) by treating them as $2b$ (identical algorithm).
New passwords are stored as $2y$ for cross-compatibility.
"""
import bcrypt
from django.contrib.auth.hashers import BasePasswordHasher
from django.utils.crypto import constant_time_compare


class GrapeBcryptHasher(BasePasswordHasher):
    """
    Handles PHP password_hash($pass, PASSWORD_BCRYPT) output ($2y$10$...).
    Also handles $2b$ hashes.
    Stores new hashes as $2y$ to match PHP output.
    """
    algorithm = 'grape_bcrypt'

    def salt(self):
        return ''  # bcrypt generates its own salt

    def encode(self, password, salt):
        # Generate a new bcrypt hash, store as $2y$ like PHP
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=10))
        # Replace $2b$ with $2y$ for PHP compatibility
        hashed_str = hashed.decode('utf-8').replace('$2b$', '$2y$')
        return hashed_str

    def verify(self, password, encoded):
        """
        encoded is the raw hash from the DB (e.g. $2y$10$... or $2b$10$...)
        """
        # Normalize: treat $2y$ same as $2b$ for bcrypt
        check_hash = encoded.replace('$2y$', '$2b$')
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                check_hash.encode('utf-8')
            )
        except Exception:
            return False

    def safe_summary(self, encoded):
        return {'algorithm': 'bcrypt (grape)', 'hash': encoded[:20] + '...'}

    def must_update(self, encoded):
        return False

    def harden_runtime(self, password, encoded):
        pass


def make_grape_password(raw_password):
    """Create a new bcrypt hash compatible with PHP password_hash."""
    hashed = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt(rounds=10))
    return hashed.decode('utf-8').replace('$2b$', '$2y$')


def check_grape_password(raw_password, hashed):
    """
    Check a password against a stored hash.
    Handles both $2y$ (PHP) and $2b$ (Python bcrypt) and Django PBKDF2.
    """
    if not hashed:
        return False

    # PHP bcrypt or Python bcrypt
    if hashed.startswith('$2y$') or hashed.startswith('$2b$'):
        check_hash = hashed.replace('$2y$', '$2b$')
        try:
            return bcrypt.checkpw(raw_password.encode('utf-8'), check_hash.encode('utf-8'))
        except Exception:
            return False

    # Old crypt-style SHA-256 ($5$...) used by older grape versions
    if hashed.startswith('$5$'):
        import crypt
        parts = hashed.split('$')
        try:
            return crypt.crypt(raw_password, f'${parts[1]}${parts[2]}${parts[3]}$') == hashed
        except Exception:
            return False

    # Django PBKDF2 fallback
    from django.contrib.auth.hashers import check_password
    return check_password(raw_password, hashed)
