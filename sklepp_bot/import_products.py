# -*- coding: utf-8 -*-
"""Import all missing products from sklepp.by to Supabase."""
import os
import re
import httpx
import uuid
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"
CATEGORY_ID = "5419e53d-fca9-49d8-b68b-05c78e5f6c62"  # Накладки из Фольги

HEADERS_DB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def parse_products_from_markdown(md_text):
    products = []
    # Find product blocks: image link followed by name link followed by price
    # Pattern: ![...](IMAGE_URL) ... [NAME](URL) ... PRICE руб.
    blocks = re.split(r'-\s+\[', md_text)
    for block in blocks:
        # Get image URL
        img_match = re.search(r'!\[.*?\]\((https://images\.deal\.by/[^)]+)\)', block)
        # Get product name
        name_match = re.search(r'\[([^\]]+)\]\(/p\d+', block)
        # Get price
        price_match = re.search(r'(\d+[,.]\d+)\s*руб\.', block)

        if img_match and name_match and price_match:
            name = name_match.group(1).strip()
            price = float(price_match.group(1).replace(',', '.'))
            img_url = img_match.group(1)
            products.append({
                "name": name,
                "price_byn": price,
                "price_rub": round(price * 2.8, 2),
                "image_url": img_url,
                "min_order": 10
            })
    return products

def get_existing_products():
    r = httpx.get(f"{BASE}/subcategories", headers=HEADERS_DB,
                  params={"select": "name", "global_category_id": f"eq.{CATEGORY_ID}"})
    return {p["name"] for p in r.json()}

def download_image(url):
    r = httpx.get(url, timeout=15, follow_redirects=True)
    if r.status_code == 200:
        return r.content
    return None

def upload_to_storage(file_bytes, file_name):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "image/jpeg",
    }
    r = httpx.post(
        f"{STORAGE_URL}/object/products/{file_name}",
        headers=headers,
        content=file_bytes,
        timeout=30
    )
    if r.status_code in (200, 201):
        return f"{STORAGE_URL}/object/public/products/{file_name}"
    return None

def add_product(name, price_byn, price_rub, image_url, min_order=10):
    data = {
        "name": name,
        "global_category_id": CATEGORY_ID,
        "price_byn": price_byn,
        "price_rub": price_rub,
        "image_url": image_url,
        "min_order": min_order
    }
    r = httpx.post(f"{BASE}/subcategories", headers=HEADERS_DB, json=data, timeout=10)
    return r.status_code in (200, 201)

def fetch_page(page_num):
    if page_num == 1:
        url = "https://sklepp.by/g9452912-nakladki-folgi?view_as=list"
    else:
        url = f"https://sklepp.by/g9452912-nakladki-folgi/page_{page_num}?view_as=list"
    r = httpx.get(url, timeout=15, follow_redirects=True)
    return r.text if r.status_code == 200 else None

def main():
    print("Loading existing products...")
    existing = get_existing_products()
    print(f"  Found {len(existing)} existing products")

    all_products = []

    for page in range(1, 15):
        print(f"\nScraping page {page}...")
        html = fetch_page(page)
        if not html:
            print(f"  Failed to fetch page {page}")
            break

        products = parse_products_from_markdown(html)
        if not products:
            # Try HTML parsing
            products = parse_products_from_html(html)

        if not products:
            print(f"  No products on page {page}, stopping")
            break

        all_products.extend(products)
        print(f"  Found {len(products)} products")

    print(f"\nTotal scraped: {len(all_products)}")

    new_products = [p for p in all_products if p["name"] not in existing]
    print(f"New to add: {len(new_products)}")

    added = 0
    errors = 0

    for i, p in enumerate(new_products):
        print(f"\n[{i+1}/{len(new_products)}] {p['name'][:60]}...")

        img_bytes = download_image(p["image_url"])
        if not img_bytes:
            print(f"  FAIL: download")
            errors += 1
            continue

        file_name = f"{uuid.uuid4().hex}.jpg"
        storage_url = upload_to_storage(img_bytes, file_name)
        if not storage_url:
            print(f"  FAIL: upload")
            errors += 1
            continue

        if add_product(p["name"], p["price_byn"], p["price_rub"], storage_url, p["min_order"]):
            added += 1
            print(f"  OK")
        else:
            errors += 1
            print(f"  FAIL: db")

    print(f"\n=== DONE: {added} added, {errors} errors ===")

def parse_products_from_html(html):
    """Parse from raw HTML."""
    products = []
    # Find product entries with image URLs and names
    pattern = r'<img[^>]+src="(https://images\.deal\.by/[^"]+)"[^>]*>.*?<a[^>]+href="(/p\d+[^"]*)"[^>]*>\s*([^<]+)\s*</a>.*?(\d+[,.]\d+)\s*руб\.'
    matches = re.findall(pattern, html, re.DOTALL)

    for img_url, _, name, price in matches:
        name = name.strip()
        price_val = float(price.replace(',', '.'))
        products.append({
            "name": name,
            "price_byn": price_val,
            "price_rub": round(price_val * 2.8, 2),
            "image_url": img_url,
            "min_order": 10
        })
    return products

if __name__ == "__main__":
    main()
