# -*- coding: utf-8 -*-
"""Generate descriptions for all products."""
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE = f"{SUPABASE_URL}/rest/v1"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def get_all_products():
    r = httpx.get(f"{BASE}/subcategories", headers=HEADERS,
                  params={"select": "id,name,description", "order": "name"})
    return r.json()

def generate_description(name):
    name_lower = name.lower()

    # Extract dimensions if present
    dims = ""
    import re
    dims_match = re.search(r'\((\d+[хx]\d+)мм\)', name)
    if dims_match:
        dims = dims_match.group(1)

    # Base descriptions by product type
    if "крест №" in name_lower or "крест " in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-крест из высококачественной фольги. Подходит для оформления гробов и венков.{size_info} Изготовлено из прочных материалов, гарантирующих долговечность и сохранение внешнего вида."

    if "распятие" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-распятие из фольги. Изображение распятия Иисуса Христа.{size_info} Качественное изготовление, подходит для оформления памятных мест."

    if "ангел" in name_lower and "крест" not in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-ангел из фольги. Символ защиты и духовного покоя.{size_info} Элегантный дизайн, подходит для оформления гробов и памятников."

    if "роза" in name_lower and "бант" not in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-роза из фольги. Классический символ памяти и любви.{size_info} Деликатное исполнение, подходит для различных ритуальных изделий."

    if "гвоздика" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-гвоздика из фольги. Традиционный символ памяти.{size_info} Изготовлена из качественной фольги, сохраняет форму."

    if "хризантема" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-хризантема из фольги. Символ скорби и памяти.{size_info} Подходит для оформления венков и гробов."

    if "букет" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-букет из фольги. Композиция из цветов для оформления памятных мест.{size_info} Красивое и долговечное изделие."

    if "бант" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-бант из фольги. Элемент декора для венков и гробов.{size_info} Аккуратное исполнение, различных размеров."

    if "венок" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-венок из фольги. Символ вечной памяти.{size_info} Различные варианты исполнения: ажурный, с бантом, с надписью."

    if "ваза" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-ваза из фольги. Декоративный элемент для оформления памятных мест.{size_info} Качественное изготовление."

    if "полоса" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная полоса из фольги для оформления гробов и венков.{size_info} Доступна в различных ширинах и цветовых решениях."

    if "лента" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная лента из фольги с надписью.{size_info} Подходит для оформления венков и гробов."

    if "угол" in name_lower or "угл" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-угол из фольги. Декоративный элемент для оформления углов гробов.{size_info} Различные варианты: с розой, бабочкой, листком."

    if "икона" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-икона из фольги. Изображение святых.{size_info} Подходит для оформления гробов и памятников."

    if "мадонна" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-Мадонна из фольги. Изображение Девы Марии.{size_info} Элегантное исполнение, символ надежды и утешения."

    if "молящ" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка с изображением молящейся фигуры из фольги.{size_info} Символ веры и духовной связи."

    if "церковь" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-церковь из фольги. Символ веры.{size_info} Подходит для оформления памятных мест."

    if "свеча" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-свеча из фольги. Символ памяти и молитвы.{size_info} Различные варианты: одинарная, двойная, тройная."

    if "голуб" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка с изображением голубей из фольги. Символ мира и любви.{size_info} Подходит для оформления памятных мест."

    if "коса" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-коса из фольги. Декоративный элемент для оформления гробов.{size_info} Доступна лавровая, дубовая варианты."

    if "ветка" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-ветка из фольги. Природный мотив для оформления памятных мест.{size_info} Various sizes available."

    if "лист" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-лист из фольги. Природный элемент декора.{size_info} Лавровый лист, папоротник."

    if "бутоньерк" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная бутоньерка из фольги. Элегантный элемент для оформления.{size_info} Доступна в различных размерах."

    if "накладка" in name_lower and "крест" not in name_lower and "роза" not in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка из фольги. Декоративный элемент для оформления гробов и венков.{size_info} Различные формы и размеры."

    if "печаль" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка «Печаль» из фольги. Символ скорби.{size_info} Подходит для оформления памятных мест."

    if "скорбящ" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка «Скорбящая» из фольги. Изображение скорбящей фигуры.{size_info} Эмоциональное исполнение."

    if "проповедник" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка «Проповедник» из фольги.{size_info} Подходит для оформления памятных мест."

    if "тайная вечеря" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка «Тайная вечеря» из фольги. Изображение знаменитой сцены.{size_info} Детализированное исполнение."

    if "джисус" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка с изображением Иисуса из фольги.{size_info} Подходит для оформления памятных мест."

    if "мусульм" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка с мусульманской символикой из фольги.{size_info} Подходит для оформления памятных мест."

    if "звезда" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная накладка-звезда из фольги. Символ света и надежды.{size_info} Декоративный элемент."

    if "фурнитура" in name_lower:
        size_info = f" Размер: {dims}мм." if dims else ""
        return f"Ритуальная фурнитура из фольги. Крест католический.{size_info} Изготовлено из качественных материалов."

    # Default description
    size_info = f" Размер: {dims}мм." if dims else ""
    return f"Ритуальная накладка из фольги.{size_info} Изготовлена из качественных материалов, гарантирующих долговечность. Подходит для оформления ритуальных изделий."

def main():
    print("Loading products...")
    products = get_all_products()
    print(f"Found {len(products)} products")

    updated = 0
    errors = 0
    for p in products:
        desc = generate_description(p["name"])
        try:
            r = httpx.patch(
                f"{BASE}/subcategories?id=eq.{p['id']}",
                headers={**HEADERS, "Prefer": "return=minimal"},
                json={"description": desc}
            )
            if r.status_code in (200, 204):
                updated += 1
            else:
                errors += 1
                if errors <= 3:
                    print(f"  Error for {p['name'][:40]}: {r.status_code}")
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  Exception: {e}")

        if updated % 50 == 0 and updated > 0:
            print(f"  Updated {updated}...")

    print(f"Done: {updated} updated, {errors} errors")

if __name__ == "__main__":
    main()
