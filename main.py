import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import os
import re
import time
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

PRAG_BANCI = 3

CUVINTE_EXCLUSE = [
    "ACQUISITION CORP", "ACQUISITION CORP.", "ACQUISITION COMPANY",
    "SPAC", "BLANK CHECK"
]

ZILE_FEREASTRA_UNDERWRITER = 3
LISTING_FORMS = ["424B4", "424B1", "424B3", "8-A12B", "EFFECT"]

STATE_FILE = "seen_filings.json"
WATCHLIST_FILE = "watchlist.json"
USER_AGENT = "VasileAgentIPO vasile@example.com"


def este_exclusa(nume_companie):
    nume_upper = nume_companie.upper()
    return any(cuvant in nume_upper for cuvant in CUVINTE_EXCLUSE)


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
# STARE (filing-uri vazute)
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
# WATCHLIST AUTOMATA (companii de urmarit pentru listare)
# ============================================================

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)  # dict: cik -> nume companie
        except Exception as e:
            print(f"Nu am putut citi watchlist-ul, pornesc de la zero: {e}")
    return {}


def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f)


def adauga_in_watchlist(watchlist, cik, nume):
    if cik and cik not in watchlist:
        watchlist[cik] = nume
        print(f"Adaugat automat in watchlist: {nume} (CIK {cik})")


# ============================================================
# 1. VERIFICARE PE NUME DE COMPANIE (feed EDGAR simplu)
# ============================================================

def check_unicorn_filings(seen_filings, new_seen_filings, watchlist):
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

            title_original = title_el.text
            title = title_original.upper()
            link = link_el.attrib['href']

            if link in seen_filings:
                continue

            if any(company in title for company in MEGA_UNICORNS):
                msg = f"[Unicorn Target] S-1 Detectat: {title_original}. Link: {link}"
                send_push_notification("ALERTA IPO POTENTIAL MARE", msg)
                print(f"Match gasit (unicorn): {msg}")

                # Extragem CIK-ul din titlu, format tipic: "... (0001234567) ..."
                cik_match = re.search(r'\((\d{7,10})\)', title_original)
                if cik_match:
                    adauga_in_watchlist(watchlist, cik_match.group(1), title_original)

            new_seen_filings.add(link)

    except Exception as e:
        print(f"Eroare la verificarea feed-ului de unicorni: {e}")
        send_push_notification("EROARE AGENT IPO", f"Eroare feed unicorni: {e}")


# ============================================================
# 2. VERIFICARE PE BANCI UNDERWRITER (Full-Text Search EDGAR)
# ============================================================

def cauta_banca(bank, start_date, end_date, incercari=3):
    params = urllib.parse.urlencode({
        "q": f'"{bank}"',
        "forms": "S-1",
        "startdt": start_date.isoformat(),
        "enddt": end_date.isoformat()
    })
    url = f"https://efts.sec.gov/LATEST/search-index?{params}"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

    for incercare in range(incercari):
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())
            return data.get("hits", {}).get("hits", [])
        except Exception as e:
            print(f"Eroare la interogarea pentru {bank} (incercarea {incercare + 1}/{incercari}): {e}")
            if incercare < incercari - 1:
                time.sleep(3)

    return []


def check_underwriter_filings(seen_filings, new_seen_filings, watchlist):
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=ZILE_FEREASTRA_UNDERWRITER)

    filing_bank_matches = {}  # adsh -> {"banks": set(), "company": str, "cik": str}

    for bank in TOP_UNDERWRITERS:
        hits = cauta_banca(bank, start_date, end_date)

        for hit in hits:
            source = hit.get("_source", {})
            adsh = source.get("adsh") or hit.get("_id", "")
            company_names = source.get("display_names", [])
            company = ", ".join(company_names) if company_names else "Companie necunoscuta"

            if este_exclusa(company):
                continue

            # CIK-ul vine de regula in campul "ciks" (lista) sau derivat din display_names
            ciks = source.get("ciks", [])
            cik = ciks[0] if ciks else None

            if adsh not in filing_bank_matches:
                filing_bank_matches[adsh] = {"banks": set(), "company": company, "cik": cik}
            filing_bank_matches[adsh]["banks"].add(bank)

        time.sleep(1)

    for adsh, info in filing_bank_matches.items():
        key = f"fulltext:{adsh}"
        if key in seen_filings:
            continue

        if len(info["banks"]) >= PRAG_BANCI:
            banci_text = ", ".join(sorted(info["banks"]))
            msg = f"[Major Bank Syndicate] Banci: {banci_text}. Companie: {info['company']}. Accession: {adsh}"
            send_push_notification("ALERTA IPO POTENTIAL MARE", msg)
            print(f"Match gasit (underwriter syndicate): {msg}")

            if info["cik"]:
                adauga_in_watchlist(watchlist, info["cik"], info["company"])

        new_seen_filings.add(key)


# ============================================================
# 3. VERIFICARE LISTARE IMINENTA PENTRU WATCHLIST (automat)
# ============================================================

def check_watchlist_listing(seen_filings, new_seen_filings, watchlist):
    for cik, nume in list(watchlist.items()):
        cik_padded = cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])

            for form, date, accession in zip(forms, dates, accessions):
                if form in LISTING_FORMS:
                    key = f"listing:{accession}"
                    if key in seen_filings:
                        continue

                    msg = f"[Pregatire Listare] {nume}: depunere {form} din {date}. Posibil aproape de tranzactionare! Accession: {accession}"
                    send_push_notification("POSIBILA LISTARE IMINENTA", msg)
                    print(f"Match gasit (listare): {msg}")
                    new_seen_filings.add(key)

        except Exception as e:
            print(f"Eroare la verificarea watchlist pentru {nume} (CIK {cik}): {e}")

        time.sleep(1)


# ============================================================
# RULARE
# ============================================================

if __name__ == "__main__":
    seen = load_seen_filings()
    new_seen = set(seen)
    watchlist = load_watchlist()

    check_unicorn_filings(seen, new_seen, watchlist)
    check_underwriter_filings(seen, new_seen, watchlist)
    check_watchlist_listing(seen, new_seen, watchlist)

    save_seen_filings(new_seen)
    save_watchlist(watchlist)
