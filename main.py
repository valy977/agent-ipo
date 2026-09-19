import requests
import xml.etree.ElementTree as ET

# Lista de companii pe care le monitorizăm
WATCHLIST = ["OpenAI", "SpaceX", "Stripe", "Databricks"]

# Canalul tău secret pentru notificări gratuite pe telefon (prin aplicația ntfy)
NTFY_CHANNEL = "bursa-ipo-notificari-vasile" 

def check_sec_s1_filings():
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1&output=atom"
    # SEC cere un User-Agent identificabil
    headers = {'User-Agent': 'IPOBot/1.0 (contact@example.com)'}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Eroare SEC: Status {response.status_code}")
            return

        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        found = False
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text
            link = entry.find('atom:link', ns).attrib['href']
            
            for company in WATCHLIST:
                if company.lower() in title.lower():
                    found = True
                    msg = f"🚀 IPO Alert: {company} a depus S-1 la SEC!\n{link}"
                    send_push_notification(f"IPO Nou: {company}", msg)
                    
        if not found:
            print("Verificare finalizată: Nicio companie din listă nu a depus dosar recent.")
            
    except Exception as e:
        print(f"A apărut o eroare: {e}")

def send_push_notification(title, text):
    # Trimite notificare gratuită direct pe telefon prin ntfy.sh
    requests.post(
        f"https://ntfy.sh/{NTFY_CHANNEL}",
        data=text.encode('utf-8'),
        headers={"Title": title}
    )

if __name__ == "__main__":
    check_sec_s1_filings()
