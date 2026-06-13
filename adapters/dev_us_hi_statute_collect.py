#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""하와이 법전 (www.capitol.hawaii.gov) — ④정적 PDF 디렉토리. 본문 PD.
근거 = 리서치 0614 4주 보고서 = /hrscurrent/ 정적 PDF 디렉토리(14볼륨·챕터별 PDF·2026-01-06 갱신).
  index = https://www.capitol.hawaii.gov/hrscurrent/  (IIS 디렉토리 리스팅 = Vol01~Vol14 폴더)
  Vol 폴더 → 챕터 PDF (2단). 동적 검색(search.capitol.hawaii.gov)은 403 = 사용 금지.
라이선스 = 퍼블릭도메인(HRS government edict). "unofficial compilation" 표기는 공식성 문제일 뿐.
지오블록 + 정적 403 위험 → GHA(미국 IP) diag 선행으로 200·href 실측 후 셀렉터 보정(추정 금지·계명1)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "hi",
    "base": "https://www.capitol.hawaii.gov",
    "index_url": "https://www.capitol.hawaii.gov/hrscurrent/",
    "ext": ".pdf",
}

if __name__ == "__main__":
    run(CONFIG)
