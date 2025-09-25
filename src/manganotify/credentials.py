# pip install keyring
import os

import keyring

SERVICE = "mangabaka"
PU_USER = "pushover_user_key"
PU_TOKEN = "pushover_app_token"

def get_pushover_creds():
    user = keyring.get_password(SERVICE, PU_USER) or os.getenv("PUSHOVER_USER_KEY")
    token = keyring.get_password(SERVICE, PU_TOKEN) or os.getenv("PUSHOVER_APP_TOKEN")
    return user, token

def set_pushover_creds(user_key: str, app_token: str):
    keyring.set_password(SERVICE, PU_USER, user_key)
    keyring.set_password(SERVICE, PU_TOKEN, app_token)
