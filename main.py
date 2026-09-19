import urllib.request
import xml.etree.ElementTree as ET
import json
import os

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
    "GOLDMAN SACHS", "MORGAN STANLEY", "J.P. MORGAN", "JPMORGAN",
    "CITIGROUP", "BANK OF AMERICA", "BOFA"
]

STATE_FILE = "seen_filings.json"


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


def check_sec_s1_filings():
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1&output=atom"

    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'VasileAgentIPO vasile@example.com'}
    )

    seen_filings = load_seen_filings()
    new_seen_filings = set(seen_filings)

    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()

        # --- DEBUG: vedem exact ce a raspuns SEC ---
        print(f"DEBUG: lungime raspuns brut: {len(xml_data)} caractere")
        print(f"DEBUG: primele 500 caractere: {xml_data[:500]}")
        # --- SFARSIT DEBUG ---

        root = ET.fromstring(xml_data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}

        entries = root.findall('atom:entry', namespace)

        # --- DEBUG: cate intrari, si titlurile lor ---
        print(f"DEBUG: numar total de intrari in feed: {len(entries)}")
        for i, e in enumerate(entries[:10]):
            t = e.find('atom:title', namespace)
            print(f"DEBUG: intrare {i}: {t.text if t is not None else '(fara titlu)'}")
        # --- SFARSIT DEBUG ---

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

            if link in seen_filings:
                continue

            is_unicorn = any(company in title for company in MEGA_UNICORNS)
            has_top_underwriter = any(bank in summary_text for bank in TOP_UNDERWRITERS)

            if is_unicorn or has_top_underwriter:
                matches_found += 1
                reason = "Unicorn Target" if is_unicorn else "Major Bank Underwritten IPO"
                msg = f"[{reason}] S-1 Detectat: {title_el.text}. Link: {link}"
                send_push_notification("ALERTA IPO POTENTIAL MARE", msg)
                print(f"Match gasit: {msg}")

            new_seen_filings.add(link)

        if matches_found == 0:
            print("Scanare finalizata. Niciun S-1 nou relevant.")

        save_seen_filings(new_seen_filings)

    except Exception as e:
        print(f"Eroare la procesarea SEC RSS: {e}")
        send_push_notification("EROARE AGENT IPO", f"Scriptul a esuat: {e}")


if __name__ == "__main__":
    check_sec_s1_filings()
