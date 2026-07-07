import httpx
from config import SUPABASE_URL, SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

BASE = f"{SUPABASE_URL}/rest/v1"

_client = httpx.AsyncClient(timeout=10)


async def _get(table: str, params: dict = None):
    r = await _client.get(f"{BASE}/{table}", headers=HEADERS, params=params or {})
    r.raise_for_status()
    return r.json()


async def _post(table: str, data: dict):
    r = await _client.post(f"{BASE}/{table}", headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()


async def _patch(table: str, data: dict, filters: dict):
    r = await _client.patch(f"{BASE}/{table}", headers=HEADERS, json=data, params=filters)
    r.raise_for_status()
    return r.json()


async def _delete(table: str, filters: dict):
    r = await _client.delete(f"{BASE}/{table}", headers=HEADERS, params=filters)
    r.raise_for_status()
    return r.json()


async def get_global_categories():
    return await _get("global_categories", {"select": "*", "order": "created_at"})


async def get_all_subcategories():
    return await _get("subcategories", {"select": "*", "order": "created_at"})


async def get_global_category(category_id: str):
    return await _get("global_categories", {"select": "*", "id": f"eq.{category_id}"})


async def create_global_category(name: str, image_url: str = None):
    data = {"name": name}
    if image_url:
        data["image_url"] = image_url
    return await _post("global_categories", data)


async def update_global_category(category_id: str, name: str = None, image_url: str = None):
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if image_url is not None:
        update_data["image_url"] = image_url
    return await _patch("global_categories", update_data, {"id": f"eq.{category_id}"})


async def delete_global_category(category_id: str):
    return await _delete("global_categories", {"id": f"eq.{category_id}"})


async def get_subcategories(global_category_id: str):
    return await _get("subcategories", {"select": "*", "global_category_id": f"eq.{global_category_id}", "order": "created_at"})


async def get_subcategory(subcategory_id: str):
    return await _get("subcategories", {"select": "*", "id": f"eq.{subcategory_id}"})


async def create_subcategory(global_category_id: str, name: str, image_url: str = None,
                       price_byn: float = 0, price_rub: float = 0, min_order: int = 1):
    data = {
        "global_category_id": global_category_id,
        "name": name,
        "image_url": image_url,
        "price_byn": price_byn,
        "price_rub": price_rub,
        "min_order": min_order
    }
    return await _post("subcategories", data)


async def update_subcategory(subcategory_id: str, name: str = None, image_url: str = None,
                       price_byn: float = None, price_rub: float = None, min_order: int = None):
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if image_url is not None:
        update_data["image_url"] = image_url
    if price_byn is not None:
        update_data["price_byn"] = price_byn
    if price_rub is not None:
        update_data["price_rub"] = price_rub
    if min_order is not None:
        update_data["min_order"] = min_order
    return await _patch("subcategories", update_data, {"id": f"eq.{subcategory_id}"})


async def delete_subcategory(subcategory_id: str):
    return await _delete("subcategories", {"id": f"eq.{subcategory_id}"})


async def create_order(customer_name: str, customer_phone: str, customer_address: str,
                 subcategory_id: str, quantity: int, total_price_byn: float,
                 total_price_rub: float, customer_email: str = None, notes: str = None):
    data = {
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_address": customer_address,
        "customer_email": customer_email,
        "subcategory_id": subcategory_id,
        "quantity": quantity,
        "total_price_byn": total_price_byn,
        "total_price_rub": total_price_rub,
        "notes": notes
    }
    return await _post("orders", data)


async def get_orders():
    return await _get("orders", {"select": "*, subcategories(name)", "order": "created_at.desc", "limit": "20"})


async def update_order_status(order_id: str, status: str):
    return await _patch("orders", {"status": status}, {"id": f"eq.{order_id}"})


STORAGE_URL = f"{SUPABASE_URL}/storage/v1"


async def upload_photo_to_storage(file_bytes: bytes, file_name: str) -> str | None:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "image/jpeg",
    }
    r = await _client.post(
        f"{STORAGE_URL}/object/products/{file_name}",
        headers=headers,
        content=file_bytes,
    )
    if r.status_code in (200, 201):
        return f"{STORAGE_URL}/object/public/products/{file_name}"
    return None
