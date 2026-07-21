#!/usr/bin/env python3
"""Stream the two public food XLSX files into a compact SQLite database."""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from xml.etree.ElementTree import iterparse
from zipfile import ZipFile

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
WANTED = {
    "식품코드": "food_code",
    "식품명": "name",
    "데이터구분명": "data_type",
    "식품대분류명": "category_large",
    "대표식품명": "representative_name",
    "식품중분류명": "category_medium",
    "식품소분류명": "category_small",
    "영양성분함량기준량": "basis",
    "에너지(kcal)": "calories",
    "단백질(g)": "protein",
    "당류(g)": "sugar",
    "제조사명": "manufacturer",
    "업체명": "manufacturer",
}


def clean(value: str | None) -> str:
    return unicodedata.normalize("NFC", (value or "").replace("\ufeff", "").strip())


def column_number(reference: str) -> int:
    number = 0
    for char in re.match(r"[A-Z]+", reference).group(0):
        number = number * 26 + ord(char) - 64
    return number


def load_shared_strings(book: ZipFile) -> list[str]:
    values: list[str] = []
    with book.open("xl/sharedStrings.xml") as stream:
        for _, element in iterparse(stream, events=("end",)):
            if element.tag == NS + "si":
                values.append(clean("".join(node.text or "" for node in element.iter(NS + "t"))))
                element.clear()
    return values


def cell_value(cell, shared: list[str]) -> str:
    value = cell.find(NS + "v")
    if value is None:
        inline = cell.find(NS + "is")
        return clean("".join(node.text or "" for node in inline.iter(NS + "t"))) if inline is not None else ""
    return shared[int(value.text)] if cell.attrib.get("t") == "s" else clean(value.text)


def number(value: str) -> float | None:
    try:
        parsed = float(value.replace(",", ""))
        return parsed if parsed >= 0 else None
    except (TypeError, ValueError):
        return None


def normalization_factor(basis: str) -> float | None:
    """Return a factor that converts a gram-based nutrient basis to 100 g."""
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*g\s*", basis, re.IGNORECASE)
    if not match:
        return None
    grams = float(match.group(1))
    return 100.0 / grams if grams > 0 else None


def rows_from_xlsx(path: Path):
    with ZipFile(path) as book:
        shared = load_shared_strings(book)
        header_map: dict[int, str] = {}
        with book.open("xl/worksheets/sheet1.xml") as stream:
            for _, row in iterparse(stream, events=("end",)):
                if row.tag != NS + "row":
                    continue
                row_number = int(row.attrib.get("r", "0"))
                if row_number == 1:
                    for cell in row.findall(NS + "c"):
                        header = cell_value(cell, shared)
                        if header in WANTED:
                            header_map[column_number(cell.attrib["r"])] = WANTED[header]
                    missing = {"food_code", "name", "data_type", "basis", "calories", "protein", "sugar"} - set(header_map.values())
                    if missing:
                        raise ValueError(f"{path.name}: 필수 컬럼 없음: {sorted(missing)}")
                else:
                    item: dict[str, str] = {}
                    for cell in row.findall(NS + "c"):
                        key = header_map.get(column_number(cell.attrib["r"]))
                        if key:
                            item[key] = cell_value(cell, shared)
                    if item.get("food_code") and item.get("name"):
                        yield item
                row.clear()


def create_database(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    connection.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE foods (
            id INTEGER PRIMARY KEY,
            food_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            category_large TEXT,
            representative_name TEXT,
            category_medium TEXT,
            category_small TEXT,
            manufacturer TEXT,
            original_basis TEXT,
            calories REAL,
            protein REAL,
            sugar REAL,
            normalized INTEGER NOT NULL DEFAULT 0
        );
    """)
    return connection


def import_file(connection: sqlite3.Connection, path: Path) -> int:
    sql = """INSERT OR REPLACE INTO foods
        (food_code,name,data_type,category_large,representative_name,category_medium,
         category_small,manufacturer,original_basis,calories,protein,sugar,normalized)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    batch = []
    count = 0
    for item in rows_from_xlsx(path):
        basis = item.get("basis", "")
        factor = normalization_factor(basis)
        nutrients = [number(item.get(key, "")) for key in ("calories", "protein", "sugar")]
        if factor is not None:
            nutrients = [round(value * factor, 4) if value is not None else None for value in nutrients]
        batch.append((
            item.get("food_code"), item.get("name"), item.get("data_type"),
            item.get("category_large", ""), item.get("representative_name", ""),
            item.get("category_medium", ""), item.get("category_small", ""),
            item.get("manufacturer", ""), basis, *nutrients, int(factor is not None),
        ))
        if len(batch) >= 2000:
            connection.executemany(sql, batch)
            connection.commit()
            count += len(batch)
            batch.clear()
            print(f"  {path.name}: {count:,}건", end="\r", flush=True)
    if batch:
        connection.executemany(sql, batch)
        connection.commit()
        count += len(batch)
    print(f"  {path.name}: {count:,}건 완료")
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--db", type=Path, default=Path(__file__).parents[1] / "data" / "foods.db")
    args = parser.parse_args()
    for path in args.files:
        if not path.exists():
            parser.error(f"파일을 찾을 수 없습니다: {path}")

    connection = create_database(args.db)
    try:
        total = sum(import_file(connection, path) for path in args.files)
        print("검색 인덱스를 생성합니다…")
        connection.executescript("""
            CREATE INDEX idx_foods_type ON foods(data_type);
            CREATE INDEX idx_foods_category ON foods(data_type, category_large, category_medium);
            CREATE INDEX idx_foods_calories ON foods(data_type, normalized, calories);
            CREATE INDEX idx_foods_protein ON foods(data_type, normalized, protein DESC);
            CREATE INDEX idx_foods_sugar ON foods(data_type, normalized, sugar);
            CREATE INDEX idx_foods_name ON foods(name);
            ANALYZE;
        """)
        connection.commit()
        print(f"완료: {args.db} ({total:,}건)")
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\n중단되었습니다.")
