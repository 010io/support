#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

JAR_ID = "7Y88YyV1uA"
URL = f"https://send.monobank.ua/jar/{JAR_ID}"
DATA_PATH = Path("data/case31.json")


def parse_amount(raw: str) -> int:
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else 0


def scrape_jar() -> tuple[int, int, str]:
    resp = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (CASE-31-agent)"},
        timeout=20,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    text = soup.get_text(" ", strip=True).lower()

    m = re.search(
        r"зiбрано\s+([\d\s ]+)[^\d]+з\s+([\d\s ]+)",
        text,
    )
    if not m:
        raise RuntimeError("Could not find jar amounts in HTML")

    balance = parse_amount(m.group(1))
    goal = parse_amount(m.group(2))

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else f"CASE-31 ({JAR_ID})"

    return balance, goal, title


def load_existing() -> dict:
    if DATA_PATH.exists():
        with DATA_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "jar_id": JAR_ID,
        "title": "CASE-31",
        "balance": 0,
        "goal": 115000,
        "remaining": 115000,
        "progress_percent": 0.0,
        "currency": "UAH",
        "updated_at": None,
        "url": URL,
        "history": [],
        "metadata": {
            "case_id": "31",
            "brigade": "22_OMBr",
            "beneficiary": "@_s_o_v_e_n_k_o_",
            "author": "@010io",
        },
    }


def main() -> None:
    balance, goal, title = scrape_jar()

    now = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    data = load_existing()
    data["title"] = title or data.get("title") or "CASE-31"
    data["goal"] = goal or data.get("goal", 115000)
    data["balance"] = balance
    data["remaining"] = max(data["goal"] - balance, 0)
    data["progress_percent"] = (
        round(balance / data["goal"] * 100, 2) if data["goal"] else 0.0
    )
    data["updated_at"] = now

    history = data.get("history", [])
    if not history or history[-1]["balance"] != balance:
        history.append({"balance": balance, "timestamp": now})
    data["history"] = history

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(
        f"✅ Updated: {balance:,} / {data['goal']:,} UAH "
        f"({data['progress_percent']}%)"
    )
    print(f"📁 Saved to: {DATA_PATH}")


if __name__ == "__main__":
    main()
