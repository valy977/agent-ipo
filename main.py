import urllib.request
import xml.etree.ElementTree as ET

# 1. Top companii private globale cu potential urias de evaluare (Unicorni > $2Mld+)
MEGA_UNICORNS = [
    # Tech & AI
    "OPENAI", "ANTHROPIC", "DATABRICKS", "SCALE AI", "PERPLEXITY",
    # Aerospace & Defense
    "SPACEX", "ANDURIL",
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
TOP_UNDERWRITERS = [
    "GOLDMAN SACHS", 
    "MORGAN STANLEY", 
    "J.P. MORGAN", "JPMORGAN", 
    "CITIGROUP", 
    "BANK OF AMERICA", "BOFA"
]

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

def check_sec_s1_filings():
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1&output=atom"
    
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'VasileAgentIPO vasile@example.com'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        entries = root.findall('atom:entry', namespace)
        
        matches_found = 0
        
        for entry in entries:
            title = entry.find('atom:title', namespace).text.upper()
            summary = entry.find('atom:summary', namespace)
            summary_text = summary.text.upper() if summary is not None else ""
            link = entry.find('atom:link', namespace).attrib['href']
            
            is_unicorn = any(company in title for company in MEGA_UNICORNS)
            has_top_underwriter = any(bank in summary_text for bank in TOP_UNDERWRITERS)
            
            if is_unicorn or has_top_underwriter:
                matches_found += 1
                reason = "Unicorn Target" if is_unicorn else "Major Bank Underwritten IPO"
                msg = f"[{reason}] S-1 Detectat: {entry.find('atom:title', namespace).text}. Link: {link}"
                send_push_notification("ALERTA IPO POTENTIAL MARE", msg)
                print(f"Match gasit: {msg}")

        # Notificare de test / confirmare si status
        if matches_found == 0:
            send_push_notification(
                "STATUS AGENT IPO", 
                "Scanare SEC EDGAR finalizata cu succes. Niciun S-1 nou depus de unicorni."
            )

    except Exception as e:
        print(f"Eroare la procesarea SEC RSS: {e}")

if __name__ == "__main__":
    check_sec_s1_filings()
