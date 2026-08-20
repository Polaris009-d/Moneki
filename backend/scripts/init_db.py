"""数据清洗 + 建库脚本。

读取 data/*.csv → 清洗 → 写入 data/moneki.db，并生成 data/data_quality.json。

用法（在 backend/ 目录下执行）：
    python scripts/init_db.py

统一统计口径（详见 README）：
    - 营业额 = SUM(amount)，负数(退款)自然扣减，即净营业额
    - 订单数 = COUNT(DISTINCT order_id)
    - 客单价 = 净营业额 / 有效订单数（至少有一条有效 amount 的 order_id）
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

# 让脚本能 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine
from app.models import Base, Product, Sale, Store

DATA_DIR = settings.data_dir
QUALITY_PATH = DATA_DIR / "data_quality.json"

_RE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_SLASH = re.compile(r"^(\d{4})/(\d{2})/(\d{2})$")
_RE_DMY = re.compile(r"^(\d{2})-(\d{2})-(\d{4})$")


def parse_date(s: str) -> str | None:
    """统一三种日期格式为 YYYY-MM-DD。"""
    s = (s or "").strip()
    if _RE_ISO.match(s):
        return s
    m = _RE_SLASH.match(s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _RE_DMY.match(s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def parse_amount(s: str) -> float | None:
    """金额：剥离货币符号/千分位，空值返回 None，保留负号(退款)。"""
    s = (s or "").strip()
    if s == "":
        return None
    s = s.replace("¥", "").replace("￥", "").replace("元", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_qty(s: str) -> float | None:
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main() -> None:
    # 1. 读取维表
    stores = {}
    with open(DATA_DIR / "stores.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            stores[r["store_id"].strip()] = {k: v.strip() for k, v in r.items()}
    products = {}
    with open(DATA_DIR / "products.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            products[r["product_id"].strip()] = {k: v.strip() for k, v in r.items()}

    # 2. 读取销售流水（原始）
    raw_rows = []
    with open(DATA_DIR / "sales.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            raw_rows.append({k: (v or "").strip() for k, v in r.items()})

    report = {"raw_sales": len(raw_rows)}

    # 3. 完全重复行去重
    seen = set()
    deduped = []
    duplicates = 0
    for r in raw_rows:
        key = tuple(r[k] for k in ("order_id", "date", "store_id", "product_id", "qty", "amount", "payment"))
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
            deduped.append(r)
    report["duplicates_removed"] = duplicates

    # 4. 逐行清洗并统计
    cleaned = []
    date_fixed = 0
    amount_currency = 0
    amount_missing = 0
    invalid_amount = 0
    store_case_fixed = 0
    refund_amount_rows = 0
    refund_qty_rows = 0
    amount_mismatch = 0
    orphan_store = Counter()
    orphan_product = Counter()

    for r in deduped:
        d = parse_date(r["date"])
        if d is None:
            report.setdefault("invalid_date_dropped", 0)
            report["invalid_date_dropped"] += 1
            continue
        if d != r["date"]:
            date_fixed += 1

        amt_raw = r["amount"]
        if any(ch in amt_raw for ch in ("¥", "￥", "元")):
            amount_currency += 1
        amt = parse_amount(amt_raw)
        if amt_raw == "":
            amount_missing += 1
        elif amt is None:
            invalid_amount += 1
        if amt is not None and amt < 0:
            refund_amount_rows += 1

        qty = parse_qty(r["qty"])
        if qty is None:
            qty = 0.0
        if qty < 0:
            refund_qty_rows += 1

        sid = r["store_id"]
        if sid == "s01":
            sid = "S01"
            store_case_fixed += 1
        pid = r["product_id"]

        if sid not in stores:
            orphan_store[sid] += 1
        if pid not in products:
            orphan_product[pid] += 1

        # amount 与 单价×数量 一致性检查（仅对有效正数金额、有效商品、正数数量）
        if amt is not None and amt > 0 and qty > 0 and pid in products:
            expected = float(products[pid]["unit_price"]) * qty
            if abs(amt - expected) > 0.01:
                amount_mismatch += 1

        cleaned.append(
            {
                "order_id": r["order_id"],
                "date": d,
                "store_id": sid,
                "product_id": pid,
                "qty": qty,
                "amount": amt,
                "payment": r["payment"],
            }
        )

    report.update(
        {
            "date_format_normalized": date_fixed,
            "amount_currency_stripped": amount_currency,
            "amount_missing_set_null": amount_missing,
            "invalid_amount_set_null": invalid_amount,
            "store_id_case_normalized": store_case_fixed,
            "refund_rows_negative_amount": refund_amount_rows,
            "refund_rows_negative_qty": refund_qty_rows,
            "amount_mismatch_unit_price_qty": amount_mismatch,
            "orphan_store_ids": dict(orphan_store),
            "orphan_product_ids": dict(orphan_product),
            "final_records": len(cleaned),
        }
    )

    # 5. 建库写入
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Store(
                    store_id=k,
                    store_name=v["store_name"],
                    category=v["category"],
                    district=v["district"],
                )
                for k, v in stores.items()
            ]
        )
        session.add_all(
            [
                Product(
                    product_id=k,
                    product_name=v["product_name"],
                    product_category=v["product_category"],
                    unit_price=float(v["unit_price"]),
                )
                for k, v in products.items()
            ]
        )
        session.add_all([Sale(**row) for row in cleaned])
        session.commit()

    # 6. 输出质量报告
    QUALITY_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Data cleaning done. Quality report:")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
