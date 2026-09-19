import urllib.request
import xml.etree.ElementTree as ET
import json
import os

# ============================================================
# CONFIGURARE
# ============================================================

# 1. Top companii private globale cu potential urias de evaluare (Unicorni > $2Mld+)
#    NOTA: SEC foloseste numele LEGAL al companiei, nu brandul. Ex: "SPACEX" apare
#    ca "SPACE EXPLORATION TECHNOLOGIES". Am completat cu variante legale unde le stiu;
#    verifica/ajusteaza daca vezi ca un match asteptat nu apare.
MEGA_UNICORNS = [
    # Tech & AI
    "OPENAI", "ANTHROPIC", "DATABRICKS", "SCALE AI", "PERPLEXITY",
    # Aerospace & Defense
    "SPACE EXPLORATION TECHNOLOGIES", "SPACEX", "ANDURIL",
    # Fintech & Payments
    "STRIPE", "REVOLUT", "KLARNA", "CHIME", "PLAID", "RIPPLE",
    # E-Commerce, Retail & Fashion
    "SHEIN", "TEMU", "FANATICS", "SKIMS",
    # Gaming, Social & Entertainment
    "EPIC GAMES", "BYTEDANCE", "DISCORD", "CANVA", "FIGMA",
    # Health, Automation & Logistics
    "DEVOTED HEALTH", "TEMPUS", "FLEXPORT"
]

# 2. Marile banci de investitii (Bulge Bracket Underwriters)
#    NOTA: feed-ul "getcurrent" NU contine de regula text despre underwriteri in summary,
#    deci acest filtru probabil nu va prinde nimic din acest endpoint. Il pastram
#    pentru cazul in care SEC schimba formatul, sau daca treci pe full-text search.
TOP_UNDERWRITERS = [
    "GOLDMAN SACHS",
    "MORGAN STANLEY",
    "J.P. MORGAN", "JPMORGAN",
    "CITIGROUP",
    "BANK OF AMERICA", "BOFA"
]

STATE_FILE = "seen_filings.json"


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
    # Pastram doar ultimele 500 de linkuri, ca fisierul sa nu creasca la infinit
    trimmed = list(seen_links)[-500:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f)


# ============================================================
# VERIFICARE SEC EDGAR
# ============================================================

def check_sec_s1_filings():
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1&output=atom"

    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'VasileAgentIPO vasile@example.com'}
    )

    seen_filings = load_seen_filings()
    new_seen_filings = set(seen_filings)  # copie de lucru, actualizata pe parcurs

    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}

        entries = root.findall('atom:entry', namespace)

        matches_found = 0

        for entry in entries:
            title_el = entry.find('atom:title', namespace)
            summary_el = entry.find('atom:summary', namespace)
            link_el = entry.find('atom:link', namespace)

            if title_el is None or link_el is None:
                continue

            title = title_el.text.upper()
            summary_text = summary_el.text.upper() if summary_el is not None and summary_el.text else ""
            link = link_el.attrib['href']

            # Cheia de deduplicare: link-ul filing-ului e unic per depunere
            if link in seen_filings:
                continue  # deja notificat la o rulare anterioara

            is_unicorn = any(company in title for company in MEGA_UNICORNS)
            has_top_underwriter = any(bank in summary_text for bank in TOP_UNDERWRITERS)

            if is_unicorn or has_top_underwriter:
                matches_found += 1
                reason = "Unicorn Target" if is_unicorn else "Major Bank Underwritten IPO"
                msg = f"[{reason}] S-1 Detectat: {title_el.text}. Link: {link}"
                send_push_notification("ALERTA IPO POTENTIAL MARE", msg)
                print(f"Match gasit: {msg}")

            # Marcam ca "vazut" indiferent daca a fost match sau nu,
            # ca sa nu re-procesam acelasi filing la infinit
            new_seen_filings.add(link)

        # Notificare de status doar daca nu s-a gasit nimic, ca sa nu primesti spam zilnic
        if matches_found == 0:
            print("Scanare finalizata. Niciun S-1 nou relevant.")

        save_seen_filings(new_seen_filings)

    except Exception as e:
        print(f"Eroare la procesarea SEC RSS: {e}")
        send_push_notification("EROARE AGENT IPO", f"Scriptul a esuat: {e}")


if __name__ == "__main__":
    check_sec_s1_filings()
