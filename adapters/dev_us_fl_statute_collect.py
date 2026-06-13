#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""플로리다 법전 (www.flsenate.gov) — ④HTML파서 스캐폴드. 본문 PD.
근거 = 리서치 0614 4주 보고서 = flsenate.gov Title→Chapter→Section HTML(2025년판).
  index = https://www.flsenate.gov/Laws/Statutes/2025/  (Title 목록)
  Title → Chapter → Section (3단). Folio NXT zip(FLLawDL2025.zip)은 추출 불가 = 사용 금지.
라이선스 = 퍼블릭도메인(government edicts doctrine + Microdecisions v. Skinner). annotations 없음.
지오블록으로 WSL(한국 IP) probe 위험 → GHA(미국 IP) diag 선행 전제.
★ link_re/chapter_re 미기재 = GHA --diag href 실측 후 보정(추정 금지·계명1)."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

# 구조 [측정:GHA run 27480063309] = index→Title 49개(/Laws/Statutes/2025/Title{N}/)
#   → 각 Title 페이지에 Chapter 링크(/Laws/Statutes/2025/Chapter{N}). 챕터 페이지 = 본문 단위.
# 기존 2단 코어 매핑 = chapter_re(외부 루프=Title) → link_re(본문=Chapter). 추가 드릴 불요.
CONFIG = {
    "state": "fl",
    "base": "https://www.flsenate.gov",
    "index_url": "https://www.flsenate.gov/Laws/Statutes/2025/",
    "chapter_re": re.compile(
        r'href=["\'](/Laws/Statutes/2025/Title\d+/?)(?:#[^"\']*)?["\']', re.IGNORECASE
    ),
    "link_re": re.compile(
        r'href=["\'](/Laws/Statutes/2025/Chapter\d+)["\']', re.IGNORECASE
    ),
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
