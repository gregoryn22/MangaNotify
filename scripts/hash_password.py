#!/usr/bin/env python3
"""
Utility script to hash passwords for MangaNotify.

This script uses the same bcrypt hashing that MangaNotify uses internally.
It's safe to use - the source code is open and uses standard libraries.

Usage:
    python scripts/hash_password.py "your-password-here"
    
This will output a bcrypt hash that you can use in your .env file:
    AUTH_PASSWORD=$2b$12$...

SECURITY: This script only hashes passwords locally. Your password
never leaves your machine, is not logged, and is not transmitted anywhere.
You can inspect the source code to verify this.

Alternative: If you prefer, you can use any bcrypt tool:
    python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
"""

import sys
from passlib.context import CryptContext

# Use the same context as MangaNotify for consistency
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt with the same settings as MangaNotify."""
    return pwd_context.hash(password)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/hash_password.py \"your-password-here\"")
        print("\nThis script hashes passwords locally using bcrypt.")
        print("Your password never leaves your machine.")
        sys.exit(1)
    
    password = sys.argv[1]
    
    # Basic password strength check
    if len(password) < 8:
        print("Warning: Password is less than 8 characters. Consider using a stronger password.")
    
    hashed = hash_password(password)
    print(f"Hashed password: {hashed}")
    print("\nAdd this to your .env file:")
    print(f"AUTH_PASSWORD={hashed}")
    print("\nNote: This hash was generated locally and your password was not transmitted anywhere.")
