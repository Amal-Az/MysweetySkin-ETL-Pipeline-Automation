"""
scraping-skin/main.py
Script Selenium pour extraire :
- collection (nom)
- product_name
- price_text (ex: "98.00 Dhs")
- price_value (float: 98.0)  # tentative d'extraction numérique
- availability ("Vente" / "Épuisé" / "Inconnu")
- link (url produit)

Résultat -> data/raw_products.csv
"""
import time
import re
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException,
    StaleElementReferenceException, ElementClickInterceptedException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Pour faciliter l'installation du driver pour un débutant :
from webdriver_manager.chrome import ChromeDriverManager

# === Config ===
COLLECTIONS = {
    "Huile Parfumée": "https://mysweetyskin.ma/collections/huile-parfumee",
    "Mikhmariyat":     "https://mysweetyskin.ma/collections/mikhmariyat",
    "Musc Tahara":     "https://mysweetyskin.ma/collections/musc-tahara",
}
OUTPUT_CSV = "data/raw_products.csv"
PAGE_LOAD_TIMEOUT = 15
IMPLICIT_WAIT = 5
MAX_PAGES_PER_COLLECTION = 200  # sécurité pour éviter boucle infinie
PAGINATION_SLEEP = 1.2  # délai entre pages (respect du site)


def init_driver(headless=False):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # active si tu veux sans UI
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Optionnel : user-agent si besoin
    # options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver


def parse_price(price_text):
    """ Extrait un float depuis '98.00 Dhs', '1,234.50 Dhs', etc. """
    if not price_text:
        return None
    # garder chiffres, point ou virgule
    cleaned = re.sub(r"[^\d,\.]", "", price_text).strip()
    if cleaned == "":
        return None
    # remplacer virgule décimale par point si besoin (ex: "1.234,50" ou "1,234.50")
    # heuristique simple : si both '.' and ',' present, assume '.' thousands and ',' decimals
    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_from_item(item):
    """Extrait nom, prix, disponibilité et lien depuis un élément produit (WebElement)."""
    data = {"title": None, "price_text": None, "price_value": None, "availability": "Inconnu", "link": None}
    try:
        title_el = item.find_element(By.CSS_SELECTOR, "h3.product-grid-item__title a")
        data["title"] = title_el.text.strip()
        data["link"] = title_el.get_attribute("href")
    except NoSuchElementException:
        # fallback: chercher tout <a> dans le bloc
        try:
            a = item.find_element(By.TAG_NAME, "a")
            data["link"] = a.get_attribute("href")
            data["title"] = a.text.strip()
        except Exception:
            pass

    # prix : d'abord prix soldé, sinon regular
    price_text = ""
    try:
        price_text = item.find_element(By.CSS_SELECTOR, "span.price-item.price-item--sale").text.strip()
    except NoSuchElementException:
        try:
            price_text = item.find_element(By.CSS_SELECTOR, "span.price-item.price-item--regular").text.strip()
        except NoSuchElementException:
            # parfois le prix est dans une autre span
            try:
                price_text = item.find_element(By.CSS_SELECTOR, "div.price span").text.strip()
            except Exception:
                price_text = ""
    data["price_text"] = price_text
    data["price_value"] = parse_price(price_text)

    # disponibilité : première priorité = badge (sale__text), sinon essayer JSON dans <variant-swatch-buttons>
    try:
        badge = item.find_element(By.CSS_SELECTOR, "span.sale__text")
        txt = badge.text.strip()
        if txt:
            data["availability"] = txt
    except NoSuchElementException:
        # essayer de lire script JSON (variant-swatch-buttons)
        try:
            script = item.find_element(By.CSS_SELECTOR, "variant-swatch-buttons script[type='application/json']").get_attribute("innerHTML")
            j = json.loads(script)
            if isinstance(j, list) and len(j) > 0 and isinstance(j[0], dict):
                available = j[0].get("available", None)
                if available is True:
                    data["availability"] = "Vente"
                elif available is False:
                    data["availability"] = "Épuisé"
        except Exception:
            # impossibilité de déterminer => laisser "Inconnu"
            pass

    return data


def find_next_and_click(driver):
    """
    Essaie plusieurs selecteurs pour trouver le bouton 'suivant' et clique.
    Retourne True si a cliqué (page suivante), False sinon.
    """
    possible_selectors = [
        "a[rel='next']",
        "a.next",
        "a.pagination__next",
        "button[aria-label='Next']",
        "a[aria-label='next']",
        "a[aria-label='Suivant']",
        # xpath fallback (texte)
        "//a[contains(normalize-space(.), 'Suivant') or contains(normalize-space(.), 'Next') or contains(., '›') or contains(., '»')]"
    ]
    for sel in possible_selectors:
        try:
            if sel.startswith("//"):
                el = driver.find_element(By.XPATH, sel)
            else:
                el = driver.find_element(By.CSS_SELECTOR, sel)
            # essayer de cliquer proprement
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, el.get_attribute("xpath"))) if False else lambda d: True)
            try:
                el.click()
            except ElementClickInterceptedException:
                # fallback JS click
                driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            continue
    return False


def scrape_collection(driver, collection_name, url):
    print(f"\n--- Scraping collection: {collection_name} -> {url}")
    driver.get(url)
    products = []
    pages = 0
    visited_urls = set()

    while pages < MAX_PAGES_PER_COLLECTION:
        pages += 1
        try:
            # attendre au moins la présence des blocs produits
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.product-grid-item"))
            )
        except TimeoutException:
            print("Timeout: blocs produit non trouvés, on quitte cette collection.")
            break

        time.sleep(0.5)  # petit délai pour sécurité (renders, lazy load)
        items = driver.find_elements(By.CSS_SELECTOR, "div.product-grid-item")
        print(f"Page {pages}: {len(items)} éléments trouvés")
        for it in items:
            try:
                row = extract_from_item(it)
                row["collection"] = collection_name
                products.append(row)
            except StaleElementReferenceException:
                # si element stale, ignorer
                continue

        # pagination : essayer de cliquer sur "Suivant"
        current_url = driver.current_url
        # stratégie multi-essais : on tente trouver & click; si impossible, on tente détecter liens page=n
        clicked = False
        try:
            clicked = find_next_and_click(driver)
        except Exception as e:
            print("Erreur en cliquant next:", e)
            clicked = False

        # si on n'a pas cliqué, chercher lien page param "page="
        if not clicked:
            try:
                # trouver un lien Pagination > a[href*='page=']
                page_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='page=']")
                next_found = False
                for a in page_links:
                    href = a.get_attribute("href")
                    if href and href not in visited_urls and href != current_url:
                        visited_urls.add(href)
                        driver.get(href)
                        next_found = True
                        break
                if next_found:
                    time.sleep(PAGINATION_SLEEP)
                    continue
            except Exception:
                pass

        # si on a cliqué, attendre que l'URL change ou que les produits se rechargent
        if clicked:
            # attendre changement d'URL ou nouveau contenu
            try:
                WebDriverWait(driver, 8).until(lambda d: d.current_url != current_url)
            except Exception:
                # si URL ne change pas, attendre présence d'éléments (essai)
                time.sleep(PAGINATION_SLEEP)
            time.sleep(PAGINATION_SLEEP)
            continue

        # si rien de tout ça -> on suppose fin de pagination
        print("Fin de la pagination pour cette collection.")
        break

    return products


def main():
    driver = init_driver(headless=False)  # pour debug headless=False ; mettre True en production
    all_products = []
    try:
        for coll_name, url in COLLECTIONS.items():
            products = scrape_collection(driver, coll_name, url)
            print(f"Collection '{coll_name}' -> {len(products)} produits extraits.")
            all_products.extend(products)
    finally:
        driver.quit()

    # sauvegarde
    if not all_products:
        print("Aucun produit extrait.")
        return
    df = pd.DataFrame(all_products)
    # créer dossier data/ si nécessaire
    import os
    os.makedirs("data", exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\nTerminé. Total produits: {len(df)}. Fichier -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()



