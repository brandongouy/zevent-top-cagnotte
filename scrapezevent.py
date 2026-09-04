from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def parse_amount(amount_str):
    """
    Transforme '1 250,50 €', '1 500 €' ou '500,7 €' en float (ex: 1250.5).
    """
    if not amount_str:
        return 0.0

    cleaned = amount_str.replace(",", ".")
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = re.sub(r"[^\d.]", "", cleaned)

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def scrape_zevent():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        print("Chargement de la page...")
        page.goto(
            "https://zevent.gdoc.fr/donation_goals/",
            wait_until="domcontentloaded",
        )

        print("Attente des streamers...")
        page.wait_for_selector("img[src*='jtvnw.net']", timeout=30000)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)

        html_content = page.content()
        browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    streamers = []

    imgs = soup.find_all("img", src=re.compile(r"jtvnw\.net"))

    for img in imgs:
        card = img.find_parent("div", class_=re.compile("border"))
        if not card:
            card = img.find_parent("div", class_="w-full")
        if not card:
            continue

        image_url = img.get("src", "")
        name = ""
        location = "À distance"

        header_text_div = card.find("div", class_=re.compile("text-sm|text-md"))
        if header_text_div:
            full_text = (
                header_text_div.get_text(" ", strip=True)
                .replace("Favoris", "")
                .strip()
            )

            if " - " in full_text:
                parts = full_text.split(" - ")
                name = parts[0].strip()
                location = parts[1].strip()
            else:
                name = full_text

        amount_p = card.find("p", class_=re.compile("text-primary"))
        amount_text = amount_p.get_text(strip=True) if amount_p else "0 €"
        numeric_amount = parse_amount(amount_text)

        if name and name not in [s["name"] for s in streamers]:
            streamers.append({
                "name": name,
                "image": image_url,
                "amount": amount_text,
                "raw_amount": numeric_amount,
                "location": location,
            })

    # Horodatage actuel (ex: 04/09/2026 à 18:15:00)
    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    output_data = {"last_updated": now_str, "streamers": streamers}

    with open("streamers.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    print(
        f"✅ {len(streamers)} streamers extraits dans streamers.json (Mis à"
        f" jour le {now_str}) !"
    )

if __name__ == "__main__":
    scrape_zevent()
