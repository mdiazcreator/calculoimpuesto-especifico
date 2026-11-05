#!/usr/bin/env python3
"""Actualiza UTM mensual y tasas semanales de diésel desde páginas oficiales del SII."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
    "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
BASE_URLS = {
    "utm": "https://www.sii.cl/valores_y_fechas/utm/utm{year}.htm",
    "mepco": "https://www.sii.cl/valores_y_fechas/mepco/mepco{year}.htm",
}
HEADERS = {"User-Agent": "CalculadoraImpuestoDiesel/1.0 (consulta de indicadores publicos)"}


def fetch(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def parse_chilean_number(value: str) -> float:
    cleaned = re.sub(r"[^0-9,.-]", "", value.strip())
    if not cleaned:
        raise ValueError(f"Número vacío: {value!r}")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(".", "")
    return float(cleaned)


def parse_utm(html: str, year: int) -> dict[str, int]:
    soup = BeautifulSoup(html, "html.parser")
    values: dict[str, int] = {}
    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        for index, cell in enumerate(cells[:-1]):
            month = MONTHS.get(cell.strip().lower())
            if month is None:
                continue
            candidate = cells[index + 1].strip()
            if not re.search(r"\d", candidate):
                continue
            try:
                amount = round(parse_chilean_number(candidate))
            except ValueError:
                continue
            if amount > 0:
                values[f"{year}-{month:02d}"] = amount
    if not values:
        raise ValueError(f"No pude leer valores UTM de {year} desde la página oficial.")
    return values


def parse_variable(html: str, year: int) -> list[dict[str, str | float]]:
    soup = BeautifulSoup(html, "html.parser")
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).replace("\xa0", " ")
    markers = list(re.finditer(r"Vigencia\s+desde\s*:", text, flags=re.IGNORECASE))
    rates: dict[str, float] = {}
    for position, marker in enumerate(markers):
        end = markers[position + 1].start() if position + 1 < len(markers) else len(text)
        section = text[marker.end():end]
        date_match = re.search(r"(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)?\s*(\d{1,2})[-/](\d{1,2})[-/](\d{4})", section, re.IGNORECASE)
        if not date_match or int(date_match.group(3)) != year:
            continue
        diesel = re.search(r"Petr[oó]leo\s+Di[eé]sel", section, re.IGNORECASE)
        if not diesel:
            continue
        diesel_section = section[diesel.end():]
        rate_match = re.search(r"Impuesto\s+1\s*,\s*50\s+(-?\d+\s*,\s*\d{4})", diesel_section, re.IGNORECASE)
        if not rate_match:
            # Tolerates SII formatting the base with a different number of decimals.
            rate_match = re.search(r"Impuesto\s+1\s*,\s*5(?:0+)?\s+(-?\d+\s*,\s*\d{4})", diesel_section, re.IGNORECASE)
        if not rate_match:
            continue
        day, month, parsed_year = map(int, date_match.groups())
        effective = date(parsed_year, month, day).isoformat()
        rates[effective] = parse_chilean_number(rate_match.group(1))
    if not rates:
        raise ValueError(f"No pude leer tasas variables del diésel de {year} desde la página oficial.")
    return [{"valid_from": effective, "rate": rate} for effective, rate in sorted(rates.items())]


def build_data(years: list[int]) -> dict:
    utm: dict[str, int] = {}
    variable: list[dict[str, str | float]] = []
    for year in years:
        utm_url = BASE_URLS["utm"].format(year=year)
        mepco_url = BASE_URLS["mepco"].format(year=year)
        utm.update(parse_utm(fetch(utm_url), year))
        variable.extend(parse_variable(fetch(mepco_url), year))
    variable.sort(key=lambda row: str(row["valid_from"]))
    return {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fixed_rate": 1.5,
        "utm_clp": utm,
        "diesel_variable_utm_m3": variable,
        "sources": [BASE_URLS["utm"].format(year="{year}"), BASE_URLS["mepco"].format(year="{year}")],
        "coverage_years": years,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="datos-sii.json", help="Archivo JSON de destino")
    parser.add_argument("--years", nargs="+", type=int, help="Años a descargar; por defecto año actual y anterior")
    args = parser.parse_args()
    current_year = datetime.now(timezone.utc).year
    years = sorted(set(args.years or [current_year - 1, current_year]))
    try:
        data = build_data(years)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Datos SII actualizados en {output} ({len(data['utm_clp'])} valores UTM, {len(data['diesel_variable_utm_m3'])} tasas variables).")
        return 0
    except Exception as exc:  # fail the scheduled run so the error is visible in GitHub Actions
        print(f"Error actualizando datos oficiales del SII: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
