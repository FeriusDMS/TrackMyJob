"""
Run once locally to get your Gmail refresh token.
Requires: pip install google-auth-oauthlib
"""
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def main():
    print("TrackMyJob — Setup OAuth Gmail")
    print("=" * 40)
    print("Assure-toi d'avoir client_secrets.json dans ce dossier.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        "setup/client_secrets.json",
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0)

    with open("setup/client_secrets.json") as f:
        secrets = json.load(f)["installed"]

    print("\n✅ Authentification réussie !\n")
    print("Ajoute ces 4 secrets dans GitHub > Settings > Secrets > Actions :\n")
    print(f"  GMAIL_CLIENT_ID     = {secrets['client_id']}")
    print(f"  GMAIL_CLIENT_SECRET = {secrets['client_secret']}")
    print(f"  GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
    print(f"  DISCORD_WEBHOOK_URL = <ton webhook Discord>")
    print()


if __name__ == "__main__":
    main()
