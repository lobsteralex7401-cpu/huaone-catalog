"""華One 素食產業組產品目錄：從產業組網站（huaone-veg.web.app）的公開資料抓一份快照。

產出兩個檔，都放在本檔同一個資料夾：
  data.json     目錄頁的備援資料（線上讀不到時用這份）
  價格表.csv     給大家填美金價格的表（匯入 Google 試算表用；已有的價格不會被這支覆蓋）

用法：python snapshot.py
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://firestore.googleapis.com/v1/projects/derlife-kuan/databases/(default)/documents/"
HERE = Path(__file__).parent


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.load(r)


def val(v):
    """Firestore REST 的值轉成一般 Python 值。"""
    if v is None:
        return None
    if "stringValue" in v:
        return v["stringValue"]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "doubleValue" in v:
        return v["doubleValue"]
    if "booleanValue" in v:
        return v["booleanValue"]
    if "arrayValue" in v:
        return [val(x) for x in v["arrayValue"].get("values", [])]
    if "mapValue" in v:
        return {k: val(x) for k, x in v["mapValue"].get("fields", {}).items()}
    return None


def main():
    index = val(get("bni-veg-index/main")["fields"]["p"])
    partners = []
    for slug in index:
        f = {k: val(v) for k, v in get("bni-veg-partners/" + slug)["fields"].items()}
        partners.append({
            "slug": slug,
            "order": f.get("order") or 999,
            "category": f.get("category", ""),
            "brand": f.get("brand", ""),
            "brandEn": f.get("brandEn", ""),
            "tagline": f.get("tagline", ""),
            "taglineEn": f.get("taglineEn", ""),
            "logo": f.get("logo", ""),
            "products": [
                {k: (p.get(k) or "") for k in ("name", "nameEn", "desc", "descEn", "img")}
                for p in (f.get("products") or [])
            ],
        })
    partners.sort(key=lambda p: p["order"])
    (HERE / "data.json").write_text(json.dumps(partners, ensure_ascii=False, indent=1), encoding="utf-8")

    # 價格表：保留舊檔已填的價格，只補新商品
    csv_path = HERE / "價格表.csv"
    old = {}
    if csv_path.exists():
        with csv_path.open(encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                old[(row["代號"], row["商品"])] = row.get("美金價格", "")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["品牌", "商品", "美金價格", "代號"])
        for p in partners:
            for x in p["products"]:
                w.writerow([p["brand"], x["name"], old.get((p["slug"], x["name"]), ""), p["slug"]])

    n = sum(len(p["products"]) for p in partners)
    img = sum(1 for p in partners for x in p["products"] if x["img"])
    print(f"{len(partners)} 個品牌、{n} 項商品（{img} 項有照片）→ data.json、價格表.csv")


if __name__ == "__main__":
    main()
