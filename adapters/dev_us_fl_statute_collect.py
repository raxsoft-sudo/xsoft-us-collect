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

# index = Title 49개(/Laws/Statutes/2025/Title{N}/). 3단 트리(Title→Chapter→Section).
# diag 드릴 = chapter_re(Title 링크)로 첫 Title 페이지를 받아 챕터·섹션 구조 관찰(추정금지).
CONFIG = {
    "state": "fl",
    "base": "https://www.flsenate.gov",
    "index_url": "https://www.flsenate.gov/Laws/Statutes/2025/",
    "chapter_re": re.compile(
        r'href=["\'](/Laws/Statutes/2025/Title\d+/?)(?:#[^"\']*)?["\']', re.IGNORECASE
    ),
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
