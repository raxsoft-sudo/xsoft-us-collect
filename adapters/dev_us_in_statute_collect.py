#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""인디애나 법전 (iga.in.gov) — ④HTML파서 스캐폴드. 본문 PD.
도메인=매트릭스 본표 [측정] / index·셀렉터=[추정] GHA probe 로그로 보정 전제.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "in",
    "base": "https://iga.in.gov",
    "index_url": "https://iga.in.gov/laws/current/ic",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
