import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import os
import datetime

# ============================================================
# CONFIGURARE
# ============================================================

MEGA_UNICORNS = [
    "OPENAI", "ANTHROPIC", "DATABRICKS", "SCALE AI", "PERPLEXITY",
    "SPACE EXPLORATION TECHNOLOGIES", "SPACEX", "ANDURIL",
    "STRIPE", "REVOLUT", "KLARNA", "CHIME", "PLAID", "RIPPLE",
    "SHEIN", "TEMU", "FANATICS", "SKIMS",
    "EPIC GAMES", "BYTEDANCE", "DISCORD", "CANVA", "FIGMA",
    "DEVOTED HEALTH", "TEMPUS", "FLEXPORT"
]

TOP_UNDERWRITERS = [
    "GOLDMAN SACHS", "MORGAN STANLEY", "J.P. MORGAN",
    "CITIGROUP", "BANK OF AMERICA"
]

PRAG_BANCI = 2  # notificam doar daca cel putin atatea banci mari apar in acelasi S-1

STATE_FILE = "seen_filings.json"
USER_AGENT = "VasileAgentIPO vasile@example.com"


# ============================================================
# NOTIFICARI
# ============================================================

def send_push_notification(title, message):
    url = "https://ntfy.sh/bursa-ipo-notificari-vasile"
    req = urllib.request.Request(
        url,
        data=f"{title}: {message}".encode('utf-8'),
        headers={'Title': title, 'Priority': 'high'}
    )
    try:
        urllib.request.urlopen(req)
        print("Notificare trimisa cu succes!")
    except Exception as e:
        print(f"Eroare la trimiterea notificarii: {e}")


# ============================================================
# STARE (evita notificari duplicate intre rulari)
# ============================================================

def load_seen_filings():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Nu am putut citi fisierul de stare, pornesc de la zero: {e}")
    return set()


def save_seen_filings(seen_links):
    trimmed = list(seen_links)[-500:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f)


# ============================================================
# 1. VERIFICARE PE NUME DE COMPANIE (feed EDGAR simplu)
# ============================================================

def check_unicorn_filings(seen_filings, new_seen_filings):
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1&output=atom"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', namespace)

        for entry in entries:
            title_el = entry.find('atom:title', namespace)
            link_el = entry.find('atom:link', namespace)
            if title_el is None or link_el is None:
                continue

            title = title_el.text.upper()
            link = link_el.attrib['href']

            if link in seen_filings:
                continue

            if any(company in title for company in MEGA_UNICORNS):
                msg = f"[Unicorn Target] S-1 Detectat: {title_el.text}. Link: {link}"
                send_push_notification("ALERTA IPO POTENTIAL MARE", msg)
                print(f"Match gasit (unicorn): {msg}")

            new_seen_filings.add(link)

    except Exception as e:
        print(f"Eroare la verificarea feed-ului de unicorni: {e}")
        send_push_notification("EROARE AGENT IPO", f"Eroare feed unicorni: {e}")


# ============================================================
# 2. VERIFICARE PE BANCI UNDERWRITER (Full-Text Search EDGAR)
#    Notificam doar daca 2+ banci mari apar in ACELASI S-1
# ============================================================

def check_underwriter_filings(seen_filings, new_seen_filings):
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=3)  # fereastra de siguranta

    filing_bank_matches = {}  # adsh -> {"banks": set(), "company": str}

    for bank in TOP_UNDERWRITERS:
        params = urllib.parse.urlencode({
            "q": f'"{bank}"',
            "forms": "S-1",  # doar depuneri initiale, nu si S-1/A
            "startdt": start_date.isoformat(),
            "enddt": end_date.isoformat()
        })
        url = f"https://efts.sec.gov/LATEST/search-index?{params}"
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())

            hits = data.get("hits", {}).get("hits", [])

            for hit in hits:
                source = hit.get("_source", {})
                adsh = source.get("adsh") or hit.get("_id", "")
                company_names = source.get("display_names", [])
                company = ", ".join(company_names) if company_names else "Companie necunoscuta"

                if adsh not in filing_bank_matches:
                    filing_bank_matches[adsh] = {"banks": set(), "company": company}
                filing_bank_matches[adsh]["banks"].add(bank)

        except Exception as e:
            print(f"Eroare la interogarea full-text search pentru {bank}: {e}")

    for adsh, info in filing_bank_matches.items():
        key = f"fulltext:{adsh}"
        if key in seen_filings:
            continue

        if len(info["banks"]) >= PRAG_BANCI:
            banci_text = ", ".join(sorted(info["banks"]))
            msg = f"[Major Bank Syndicate] Banci: {banci_text}. Companie: {info['company']}. Accession: {adsh}"
            send_push_notification("ALERTA IPO POTENTIAL MARE", msg)
            print(f"Match gasit (underwriter syndicate): {msg}")

        new_seen_filings.add(key)


# ============================================================
# RULARE
# ============================================================

if __name__ == "__main__":
    seen = load_seen_filings()
    new_seen = set(seen)

    check_unicorn_filings(seen, new_seen)
    check_underwriter_filings(seen, new_seen)

    save_seen_filings(new_seen)
