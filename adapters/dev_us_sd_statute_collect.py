#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사우스다코타 법전 (sdlegislature.gov) — ④HTML파서 스캐폴드. 본문 PD.
도메인=매트릭스 본표 [측정] / index·셀렉터=[추정] GHA probe 로그로 보정 전제.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "sd",
    "base": "https://sdlegislature.gov",
    "index_url": "https://sdlegislature.gov/Statutes",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
