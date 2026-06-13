#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""하와이 법전 (HRS) — data.capitol.hawaii.gov 2017 챕터 PDF 아카이브. 본문 PD.
근거 = 리서치 0614 보고서 소스2 = data.capitol.hawaii.gov/sessions/session2017/HRS-Chapter-PDF's/
  HRS_NNNN.pdf (챕터별 PDF·2017 구버전). 디렉토리 리스팅에서 PDF href 열거.
사유 = www.capitol.hawaii.gov/hrscurrent/ 정적 PDF는 GHA 미국 IP에서도 403(WAF) 확인
  (run 27479839243). data.capitol.hawaii.gov 서브도메인은 별개 = diag로 200·href 실측.
라이선스 = 퍼블릭도메인(HRS government edict). 2017판 = 현행화 델타는 별도 트랙.
★ link_re = HRS_NNNN.pdf 디렉토리 href 실측 후 보정(추정 금지·계명1)."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "hi",
    "base": "https://data.capitol.hawaii.gov",
    "index_url": "https://data.capitol.hawaii.gov/sessions/session2017/HRS-Chapter-PDF's/",
    # 디렉토리 경로에 아포스트로피(HRS-Chapter-PDF's) 포함 → 큰따옴표 전용 캡처(작은따옴표 허용).
    "link_re": re.compile(r'href="([^"]*HRS_\d+[^"]*\.pdf)"', re.IGNORECASE),
    "ext": ".pdf",
}

if __name__ == "__main__":
    run(CONFIG)
