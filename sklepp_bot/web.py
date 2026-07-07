import os
import httpx
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

_photo_cache = {}


@app.context_processor
def inject_categories():
    try:
        categories = db_get("global_categories", {"select": "*", "order": "sort_order"})
    except Exception:
        categories = []
    return dict(categories=categories)


def get_photo_url(file_id):
    if not file_id:
        return None
    if file_id.startswith("http") or file_id.startswith("/static"):
        return file_id
    if file_id in _photo_cache:
        return _photo_cache[file_id]
    try:
        r = httpx.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=10)
        data = r.json()
        if data.get("ok"):
            file_path = data["result"]["file_path"]
            url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            _photo_cache[file_id] = url
            return url
    except Exception:
        pass
    return None


app.jinja_env.globals.update(get_photo_url=get_photo_url)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}
BASE = f"{SUPABASE_URL}/rest/v1"


def sort_by_number(products):
    import re
    def get_num(p):
        m = re.search(r'№(\d+)', p.get('name', ''))
        return int(m.group(1)) if m else 9999
    return sorted(products, key=get_num)


def db_get(table, params=None):
    r = httpx.get(f"{BASE}/{table}", headers=HEADERS, params=params or {}, timeout=10)
    r.raise_for_status()
    return r.json()


def db_post(table, data):
    r = httpx.post(f"{BASE}/{table}", headers=HEADERS, json=data, timeout=10)
    r.raise_for_status()
    return r.json()


@app.route("/")
def index():
    categories = db_get("global_categories", {"select": "*", "order": "sort_order"})
    cat_products = []
    for c in categories:
        subs = db_get("subcategories", {"select": "*", "global_category_id": f"eq.{c['id']}", "order": "created_at"})
        cat_products.append({"category": c, "products": sort_by_number(subs)})
    return render_template("index.html", cat_products=cat_products)


@app.route("/catalog")
def catalog():
    categories = db_get("global_categories", {"select": "*", "order": "sort_order"})
    cat_id = request.args.get("category")

    if not cat_id and categories:
        return redirect(url_for("catalog", category=categories[0]["id"]))

    selected_cat = None
    products = []
    if cat_id:
        subs = db_get("subcategories", {"select": "*", "global_category_id": f"eq.{cat_id}", "order": "created_at"})
        products = sort_by_number(subs)
        cats = db_get("global_categories", {"select": "*", "id": f"eq.{cat_id}"})
        selected_cat = cats[0] if cats else None

    return render_template("catalog.html", categories=categories, products=products, selected_cat=selected_cat)


@app.route("/product/<product_id>")
def product(product_id):
    try:
        subs = db_get("subcategories", {"select": "*", "id": f"eq.{product_id}"})
    except Exception:
        return redirect(url_for("index"))
    if not subs:
        return redirect(url_for("index"))
    sub = subs[0]
    cats = db_get("global_categories", {"select": "*", "id": f"eq.{sub['global_category_id']}"})
    category = cats[0] if cats else None
    return render_template("product.html", product=sub, category=category)


@app.route("/cart")
def cart():
    return render_template("cart.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/delivery")
def delivery():
    return render_template("delivery.html")


@app.route("/contacts")
def contacts():
    return render_template("contacts.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/offer")
def offer():
    return render_template("offer.html")


@app.route("/photo/<file_id>")
def photo_proxy(file_id):
    url = get_photo_url(file_id)
    if not url:
        return "", 404
    try:
        r = httpx.get(url, timeout=10)
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "image/jpeg")
            return Response(r.content, content_type=content_type, headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        pass
    return "", 502


@app.route("/order", methods=["POST"])
def order():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    items = data.get("items", [])
    if not items:
        required = ["name", "phone", "address", "product_id", "quantity"]
        for field in required:
            if not data.get(field):
                return jsonify({"error": f"Missing {field}"}), 400
        items = [{
            "product_id": data["product_id"],
            "name": "",
            "price_byn": 0,
            "price_rub": 0,
            "quantity": int(data.get("quantity", 1))
        }]

    for field in ["name", "phone", "address"]:
        if not data.get(field):
            return jsonify({"error": f"Missing {field}"}), 400

    region = data.get("region", "BY")
    is_ru = region == "RU"

    total_byn = 0
    total_rub = 0
    order_lines = []

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 1
        if quantity < 1:
            quantity = 1

        if not product_id:
            continue

        try:
            subs = db_get("subcategories", {"select": "*", "id": f"eq.{product_id}"})
        except Exception:
            continue

        if not subs:
            continue

        sub = subs[0]
        item_name = item.get("name") or sub.get("name", "?")
        price_byn = float(sub.get("price_byn", 0)) * quantity
        price_rub = float(sub.get("price_rub", 0)) * quantity

        total_byn += price_byn
        total_rub += price_rub

        if is_ru:
            order_lines.append(f"  • {item_name} × {quantity} = {price_rub:.2f} ₽")
        else:
            order_lines.append(f"  • {item_name} × {quantity} = {price_byn:.2f} Br")

        db_post("orders", {
            "customer_name": data["name"],
            "customer_phone": data["phone"],
            "customer_address": data["address"],
            "customer_email": data.get("email", ""),
            "subcategory_id": product_id,
            "quantity": quantity,
            "total_price_byn": price_byn,
            "total_price_rub": price_rub,
            "notes": data.get("comment", ""),
        })

    if not order_lines:
        return jsonify({"error": "No valid products found"}), 400

    region_name = "Россия" if is_ru else "Беларусь"

    msg = (
        f"📦 Новый заказ!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"📍 Адрес: {data['address']}\n"
        f"🌍 Регион: {region_name}\n"
    )
    if data.get("email"):
        msg += f"📧 Email: {data['email']}\n"
    msg += "\n" + "\n".join(order_lines) + "\n"
    if is_ru:
        msg += f"\n💰 Итого: {total_rub:.2f} ₽\n"
    else:
        msg += f"\n💰 Итого: {total_byn:.2f} Br\n"
    if data.get("comment"):
        msg += f"\n💬 Комментарий: {data['comment']}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━"

    try:
        httpx.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            params={"chat_id": ADMIN_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass

    return jsonify({"ok": True})


@app.route("/contact", methods=["POST"])
def contact():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()

    if not name or not phone or not message:
        return jsonify({"error": "Missing required fields"}), 400

    msg = (
        f"📩 Новое сообщение с сайта\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
    )
    if email:
        msg += f"Email: {email}\n"
    msg += f"\nСообщение:\n{message}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━"

    try:
        httpx.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            params={"chat_id": ADMIN_ID, "text": msg},
            timeout=10,
        )
    except Exception:
        pass

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
