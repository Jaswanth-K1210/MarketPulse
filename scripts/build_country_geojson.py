"""Vendor and enrich the world geojson.

The map previously fetched world.geojson from raw.githubusercontent.com at
runtime, and its features carried only {"name": ...}. That put a third-party
CDN in the data path and left no key to join a map click to signal_aggregator,
which is keyed by ISO-3166 alpha-2.

This downloads the file once, adds iso2/iso3 to every feature, and writes it
into frontend/public/ so the app loads it locally.

Run:  venv/bin/python scripts/build_country_geojson.py
"""
import json
import os
import urllib.request

import pycountry

SOURCE = ("https://raw.githubusercontent.com/holtzy/D3-graph-gallery/"
          "master/DATA/world.geojson")
OUT = os.path.join(os.path.dirname(__file__), "..", "frontend", "public",
                   "world-countries.geojson")

# pycountry resolves 160 of the 177 feature names. These are the rest.
# England is not a typo: the source file labels the United Kingdom "England",
# which is where ARM is domiciled.
ALIASES = {
    "England": "GB",
    "Russia": "RU",
    "Turkey": "TR",
    "Ivory Coast": "CI",
    "The Bahamas": "BS",
    "Brunei": "BN",
    "Democratic Republic of the Congo": "CD",
    "Guinea Bissau": "GW",
    "Macedonia": "MK",
    "Swaziland": "SZ",
    "East Timor": "TL",
    "Falkland Islands": "FK",
    "French Southern and Antarctic Lands": "TF",
    "West Bank": "PS",
}

# Disputed or unrecognised territories with no ISO assignment. Listed so their
# absence is a decision on record rather than an oversight; they stay clickable
# and simply return no data.
UNMAPPED = {"Northern Cyprus", "Somaliland", "Kosovo"}


def resolve(name: str) -> tuple[str | None, str | None]:
    """Return (alpha_2, alpha_3) for a feature name, or (None, None)."""
    if name in ALIASES:
        country = pycountry.countries.get(alpha_2=ALIASES[name])
        return (country.alpha_2, country.alpha_3) if country else (ALIASES[name], None)
    if name in UNMAPPED:
        return None, None
    try:
        c = pycountry.countries.lookup(name)
        return c.alpha_2, c.alpha_3
    except LookupError:
        return None, None


def main() -> None:
    data = json.loads(urllib.request.urlopen(SOURCE, timeout=60).read())

    resolved = unresolved = 0
    for feature in data["features"]:
        name = feature["properties"].get("name", "")
        iso2, iso3 = resolve(name)
        feature["properties"]["iso2"] = iso2
        feature["properties"]["iso3"] = iso3
        if iso2:
            resolved += 1
        else:
            unresolved += 1
            print(f"  no ISO code: {name}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    print(f"\n{resolved} features with ISO codes, {unresolved} without")
    print(f"wrote {os.path.normpath(OUT)} "
          f"({os.path.getsize(OUT) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
