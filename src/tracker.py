import os
import re
import base64
import requests
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CATEGORIES = {
    "rejection": {
        "fr": [
            "malheureusement", "sans suite", "ne correspond pas",
            "retenu d'autres candidats", "ne donnera pas suite",
            "n'a pas été retenue", "regret", "regrette",
            "ne retenir", "pas retenu", "candidature n'a pas",
        ],
        "en": [
            "unfortunately", "not selected", "not moving forward",
            "decided not to proceed", "won't be moving forward",
            "other candidates", "position has been filled",
            "regret to inform", "unable to move forward",
        ],
    },
    "interview": {
        "fr": [
            "entretien", "rencontre", "échanger avec vous",
            "disponibilité", "appel téléphonique", "visio",
            "teams", "zoom", "meet", "sélectionné",
        ],
        "en": [
            "interview", "meeting", "schedule a call", "available",
            "next steps", "would like to speak", "phone screen",
            "video call", "selected for",
        ],
    },
    "offer": {
        "fr": [
            "offre d'emploi", "proposition de poste",
            "nous souhaitons vous proposer", "félicitations",
            "heureux de vous informer", "nous avons le plaisir",
        ],
        "en": [
            "offer letter", "job offer", "we would like to offer",
            "congratulations", "pleased to inform", "pleased to offer",
        ],
    },
    "acknowledgment": {
        "fr": [
            "bien reçu", "accusé de réception", "prise en compte",
            "examinons", "reviendrons vers vous", "bonne réception",
        ],
        "en": [
            "received your application", "acknowledge", "reviewing",
            "will be in touch", "get back to you", "under review",
            "thank you for applying",
        ],
    },
}

JOB_KEYWORDS = [
    "candidature", "application", "recrutement", "recruitment",
    "poste", "position", "emploi", "job", "offre", "offer",
    "entretien", "interview", "rh ", " hr ", "drh",
    "talent acquisition", "recruiter", "recruteuse", "chargé de recrutement",
]

DISCORD_COLORS = {
    "rejection":     0xFF4444,
    "interview":     0x00CC44,
    "offer":         0xFFD700,
    "acknowledgment": 0x4488FF,
    "unknown":       0x888888,
}

DISCORD_EMOJIS = {
    "rejection":     "❌",
    "interview":     "📅",
    "offer":         "🎉",
    "acknowledgment": "📬",
    "unknown":       "❓",
}

CATEGORY_LABELS = {
    "rejection":     "Refus",
    "interview":     "Entretien",
    "offer":         "Offre",
    "acknowledgment": "Accusé de réception",
    "unknown":       "Non classifié",
}

PROCESSED_LABEL = "TrackMyJob/Processed"


def get_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def get_or_create_label(service):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == PROCESSED_LABEL:
            return label["id"]
    result = service.users().labels().create(
        userId="me", body={"name": PROCESSED_LABEL}
    ).execute()
    return result["id"]


def fetch_unprocessed(service):
    result = service.users().messages().list(
        userId="me",
        q=f"in:inbox -label:{PROCESSED_LABEL}",
        maxResults=25,
    ).execute()
    return result.get("messages", [])


def extract_body(payload):
    if "parts" in payload:
        text = ""
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    text += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            elif "parts" in part:
                text += extract_body(part)
        return text
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""


def get_email(service, msg_id):
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    return {
        "id": msg_id,
        "subject": headers.get("Subject", "(no subject)"),
        "sender":  headers.get("From", "unknown"),
        "date":    headers.get("Date", ""),
        "body":    extract_body(msg["payload"])[:3000],
    }


def is_job_related(email):
    text = (email["subject"] + " " + email["body"] + " " + email["sender"]).lower()
    return any(kw in text for kw in JOB_KEYWORDS)


def classify(email):
    text = (email["subject"] + " " + email["body"]).lower()
    scores = {cat: 0 for cat in CATEGORIES}
    for cat, langs in CATEGORIES.items():
        for words in langs.values():
            for word in words:
                if word in text:
                    scores[cat] += 1
    best_score = max(scores.values())
    if best_score == 0:
        return "unknown"
    return max(scores, key=scores.get)


def send_to_discord(category, email):
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    emoji = DISCORD_EMOJIS[category]
    label = CATEGORY_LABELS[category]
    sender = re.sub(r"<.*?>", "", email["sender"]).strip()

    embed = {
        "title": f"{emoji} {label}",
        "description": f"**{email['subject'][:200]}**",
        "color": DISCORD_COLORS[category],
        "fields": [
            {"name": "Expéditeur", "value": sender[:100],      "inline": True},
            {"name": "Date",       "value": email["date"][:50], "inline": True},
        ],
        "footer": {"text": "TrackMyJob • GitHub Actions"},
    }
    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    resp.raise_for_status()


def mark_processed(service, msg_id, label_id):
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"addLabelIds": [label_id]},
    ).execute()


def main():
    print(f"[TrackMyJob] {datetime.now(timezone.utc).isoformat()}")
    service = get_gmail_service()
    label_id = get_or_create_label(service)

    messages = fetch_unprocessed(service)
    print(f"  {len(messages)} email(s) non traité(s)")

    sent = 0
    for msg in messages:
        email = get_email(service, msg["id"])
        if not is_job_related(email):
            mark_processed(service, email["id"], label_id)
            continue

        category = classify(email)
        print(f"  [{category}] {email['subject'][:60]}")
        send_to_discord(category, email)
        mark_processed(service, email["id"], label_id)
        sent += 1

    print(f"  {sent} notification(s) envoyée(s)")


if __name__ == "__main__":
    main()
