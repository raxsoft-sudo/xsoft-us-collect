#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사우스다코타 법전 (sdlegislature.gov) — SPA 코어 전환(2026-06-14 standing 8주).
도메인=매트릭스 본표 [측정] / index·셀렉터=미측정 → netcap(XHR/fetch·POST바디 관찰)으로 발굴.
정적 코어 미구현 모드: --netcap → SPA 코어 전환. link_re/api_re는 netcap 관찰 결과로만 보정(추정 금지·계명1).
지오블록으로 WSL(한국 IP) 불가 → GHA(미국 IP) 실행 전제. 라이선스 = 퍼블릭도메인."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "sd",
    "base": "https://sdlegislature.gov",
    "index_url": "https://sdlegislature.gov/Statutes",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
