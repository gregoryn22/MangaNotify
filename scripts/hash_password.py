#!/usr/bin/env python3
"""
Utility script to hash passwords for MangaNotify.

Usage:
    python scripts/hash_password.py "your-password-here"
    
This will output a bcrypt hash that you can use in your .env file:
    AUTH_PASSWORD=$2b$12$...
"""

import sys
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/hash_password.py \"your-password-here\"")
        sys.exit(1)
    
    password = sys.argv[1]
    hashed = hash_password(password)
    print(f"Hashed password: {hashed}")
    print("\nAdd this to your .env file:")
    print(f"AUTH_PASSWORD={hashed}")
