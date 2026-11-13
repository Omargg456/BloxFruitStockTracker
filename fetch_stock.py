"""يجلب مخزون Blox Fruits من الويكي ويحفظه في stock_data.json (يعمل محليًا أو عبر GitHub Actions)."""
import json, os, re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

API = "https://blox-fruits.fandom.com/api.php"
PAGE = 'Blox Fruits "Stock"'
OUT = "stock_data.json"
HISTORY_LIMIT = 20
TYPES = {"N": "Natural", "E": "Elemental", "B": "Beast"}
RARITY = {"C": "Common", "U": "Uncommon", "R": "Rare", "L": "Legendary", "M": "Mythical"}

# الاسم | النوع | سعر Beli | سعر Robux | الندرة
RAW = """Rocket|N|5000|50|C;Spin|N|7500|75|C;Blade|N|30000|100|C;Spring|N|60000|180|C;Bomb|N|80000|220|C;
Smoke|E|100000|250|C;Spike|N|180000|380|C;Flame|E|250000|550|U;Ice|E|350000|750|U;Sand|E|420000|850|U;
Dark|E|500000|950|U;Eagle|B|550000|975|U;Diamond|N|600000|1000|U;Light|E|650000|1100|R;Rubber|N|750000|1200|R;
Ghost|N|940000|1275|R;Magma|E|960000|1300|R;Quake|N|1000000|1500|L;Buddha|B|1200000|1650|L;Love|N|1300000|1700|L;
Creation|N|1400000|1750|L;Spider|N|1500000|1800|L;Sound|N|1700000|1900|L;Phoenix|B|1800000|2000|L;
Portal|N|1900000|2000|L;Rumble|E|2100000|2100|L;Pain|N|2300000|2200|L;Blizzard|E|2400000|2250|L;
Gravity|N|2500000|2300|M;Mammoth|B|2700000|2350|M;T-Rex|B|2700000|2350|M;Dough|N|2800000|2400|M;
Shadow|E|2900000|2425|M;Venom|E|3000000|2450|M;Control|N|3200000|2500|M;Gas|E|3200000|2500|M;
Spirit|N|3400000|2550|M;Leopard|B|5000000|3000|M;Yeti|B|5000000|3000|M;Kitsune|B|8000000|4000|M;Dragon|B|15000000|5000|M"""

FRUITS = {}
for row in RAW.replace("\n", "").split(";"):
    n, t, beli, robux, r = row.split("|")
    FRUITS[n.lower()] = {"name": n, "type": TYPES[t], "price": f"{int(beli):,}",
                         "robux": f"{int(robux):,}", "rarity": RARITY[r]}


def fetch_html():
    r = requests.get(API, timeout=30, headers={"User-Agent": "bf-stock-tracker/1.0 (GitHub Pages project)"},
                     params={"action": "parse", "page": PAGE, "prop": "text",
                             "format": "json", "formatversion": 2, "redirects": 1})
    r.raise_for_status()
    return BeautifulSoup(r.json()["parse"]["text"], "html.parser")


def section_fruits(soup, pattern, limit):
    """يرجع أسماء الفواكه المعروفة الموجودة تحت أول عنوان يطابق pattern."""
    for h in soup.find_all(re.compile(r"^h[2-3]$")):
        if not re.search(pattern, h.get_text(), re.I):
            continue
        found = []
        for el in h.find_all_next():
            if el is not h and el.name in ("h2", "h3"):
                break
            if el.name == "a":
                key = re.sub(r"\s*fruit$", "", (el.get("title") or el.get_text()).strip(), flags=re.I).lower()
                if key in FRUITS and key not in found:
                    found.append(key)
        if found:
            return [FRUITS[k] for k in found[:limit]]
    return []


def main():
    data = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "normal_stock": [], "mirage_stock": [], "history": [], "note": ""}
    try:
        soup = fetch_html()
        data["normal_stock"] = section_fruits(soup, r"current|normal", 8)
        data["mirage_stock"] = section_fruits(soup, r"mirage|advanced", 10)
        if not data["normal_stock"]:
            data["note"] = "لم يعثر السكريبت على المخزون الحالي في الويكي (قد يكون المصدر توقف عن نشره)."
    except Exception as e:
        data["note"] = f"تعذّر الاتصال بالمصدر: {e}"
        print("خطأ:", e)

    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            pass
    history = old.get("history", [])
    names = lambda s: [x["name"] for x in s]
    # نضيف المخزون السابق للسجل فقط إذا تغيّر فعلًا
    if old.get("normal_stock") and names(old["normal_stock"]) != names(data["normal_stock"]) and data["normal_stock"]:
        history.insert(0, {"date": old.get("updated_at", "")[:16].replace("T", " ") + " UTC",
                           "stock": old["normal_stock"]})
    data["history"] = history[:HISTORY_LIMIT]
    if not data["normal_stock"] and old.get("normal_stock") and not data["note"]:
        data["normal_stock"] = old["normal_stock"]

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("تم الحفظ:", len(data["normal_stock"]), "عادي /", len(data["mirage_stock"]), "سراب")


if __name__ == "__main__":
    main()
