# -*- coding: utf-8 -*-
"""Upload product images to Supabase Storage and update database URLs."""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def get_products():
    r = httpx.get(f"{BASE}/subcategories", headers={**HEADERS, "Prefer": "return=representation"}, params={"select": "id,image_url"})
    return r.json()

def upload_image(file_path, file_name):
    with open(file_path, "rb") as f:
        data = f.read()
    r = httpx.post(
        f"{STORAGE_URL}/object/products/{file_name}",
        headers={**HEADERS, "Content-Type": "image/jpeg"},
        content=data
    )
    if r.status_code in (200, 201):
        return f"{STORAGE_URL}/object/public/products/{file_name}"
    print(f"  Error uploading {file_name}: {r.status_code} {r.text[:200]}")
    return None

def update_product_image(product_id, new_url):
    r = httpx.patch(
        f"{BASE}/subcategories?id=eq.{product_id}",
        headers={**HEADERS, "Prefer": "return=representation", "Content-Type": "application/json"},
        json={"image_url": new_url}
    )
    return r.status_code == 200

def main():
    products = get_products()
    print(f"Found {len(products)} products")

    uploaded = 0
    skipped = 0
    errors = 0

    for p in products:
        pid = p["id"]
        url = p.get("image_url", "")

        if not url or url.startswith("http"):
            skipped += 1
            continue

        # Extract filename from path like /static/products/filename.jpg
        filename = url.split("/")[-1]
        local_path = os.path.join("static", "products", filename)

        if not os.path.exists(local_path):
            print(f"  File not found: {local_path}")
            errors += 1
            continue

        print(f"  Uploading {filename}...")
        new_url = upload_image(local_path, filename)
        if new_url:
            if update_product_image(pid, new_url):
                uploaded += 1
                print(f"    OK -> {new_url}")
            else:
                errors += 1
                print(f"    Failed to update database")
        else:
            errors += 1

    print(f"\nDone: {uploaded} uploaded, {skipped} skipped, {errors} errors")

if __name__ == "__main__":
    main()
