#!/usr/bin/env python3
"""Regenerate the standalone engine output and simple presentation assets."""
from pathlib import Path
import json
from PIL import Image, ImageDraw

from pramaan_engine import run, ASSETS, OUT


def chart(report):
    image = Image.new("RGB", (1000, 500), "white"); draw = ImageDraw.Draw(image)
    draw.text((35, 25), "Synthetic EoA · Trust pillar score", fill="#102d45")
    colors = {"completeness":"#087f82", "authenticity":"#c94b4b", "consistency":"#e88b39", "external":"#5a78a8", "infrastructure":"#17835e"}
    for i, (key, value) in enumerate(report["pillars"].items()):
        y = 90 + i * 70; draw.text((35, y), key.title(), fill="#142638")
        draw.rectangle((210, y, 900, y+28), fill="#e8eef0"); draw.rectangle((210, y, 210 + value * 6.9, y+28), fill=colors[key])
        draw.text((920, y+5), str(value), fill="#142638")
    image.save(ASSETS / "trust_pillars.png")


if __name__ == "__main__":
    result = run(); chart(result); print("Assets written to", ASSETS)
