#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""네브래스카 법전 (nebraskalegislature.gov) — ④HTML파서 스캐폴드. 본문 PD.
도메인=매트릭스 본표 [측정] / index·셀렉터=[추정] GHA probe 로그로 보정 전제.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "ne",
    "base": "https://nebraskalegislature.gov",
    "index_url": "https://nebraskalegislature.gov/laws/browse-statutes.php",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
