#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""미시간 법전 MCL (legislature.mi.gov) — ④HTML파서 스캐폴드. 본문 PD·UELMA.
도메인·진입=매트릭스+WebSearch 측정 [측정] / 셀렉터=[추정] GHA --diag 로그 보정 전제.
관찰[측정:WebSearch 2026-06-13] = /Laws/ChapterIndex 가 챕터 인덱스 →
  /Laws/Index?ObjectName=mcl-chapNN(챕터별 섹션 목록) → /Laws/MCL?objectName=... 본문.
  깔끔한 서버 렌더 URL = 정적 파싱 후보. 2단 트리 가능성 → diag 로 챕터/섹션 구조 실측.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제.
★ link_re/chapter_re 미기재 = GHA --diag href 실측 후 보정(추정 금지·계명1)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "mi",
    "base": "https://www.legislature.mi.gov",
    "index_url": "https://www.legislature.mi.gov/Laws/ChapterIndex",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
