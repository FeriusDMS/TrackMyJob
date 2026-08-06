import re
import json
import requests
from bs4 import BeautifulSoup

JOB_ALERT_SENDERS = {
    "hellowork.com": "HelloWork",
    "indeed.com": "Indeed",
}

JOB_LINK_PATTERNS = {
    "HelloWork": re.compile(r"hellowork\.com/[^\"'\s]*/emplois?/[^\"'\s]+", re.I),
    "Indeed": re.compile(r"indeed\.com/(?:rc/clk|voir-emploi|viewjob|pagead/clk)[^\"'\s]*", re.I),
}

DISCORD_JOB_COLOR = 0x9B59B6

SEEN_JOBS_PATH = "data/seen_jobs.json"
MAX_SEEN = 1000


def is_job_alert(sender):
    sender = sender.lower()
    return any(domain in sender for domain in JOB_ALERT_SENDERS)


def source_from_sender(sender):
    sender = sender.lower()
    for domain, name in JOB_ALERT_SENDERS.items():
        if domain in sender:
            return name
    return "unknown"


def extract_job_id(href, source):
    if source == "Indeed":
        match = re.search(r"jk=([a-f0-9]+)", href)
        if match:
            return f"indeed:{match.group(1)}"
    return href.split("?")[0]


def extract_listings(html_body, source):
    if not html_body or source not in JOB_LINK_PATTERNS:
        return []

    soup = BeautifulSoup(html_body, "html.parser")
    pattern = JOB_LINK_PATTERNS[source]
    listings = []
    seen_hrefs = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not pattern.search(href) or href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        title = a.get_text(strip=True)
        if not title:
            continue

        parent = a.find_parent(["td", "div", "li"])
        context = parent.get_text(" ", strip=True) if parent else ""

        listings.append({
            "id": extract_job_id(href, source),
            "title": title,
            "context": context[:200],
            "link": href,
            "source": source,
        })

    return listings


def load_seen(path=SEEN_JOBS_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen, path=SEEN_JOBS_PATH):
    trimmed = list(seen)[-MAX_SEEN:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False, indent=2)


def send_job_to_discord(job, webhook_url):
    embed = {
        "title": f"🆕 {job['title'][:200]}",
        "description": job["context"] or "Nouvelle offre correspondant à tes critères",
        "url": job["link"],
        "color": DISCORD_JOB_COLOR,
        "fields": [
            {"name": "Source", "value": job["source"], "inline": True},
        ],
        "footer": {"text": "TrackMyJob • Veille offres"},
    }
    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    resp.raise_for_status()
