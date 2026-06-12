#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""인디애나 법전 (iga.in.gov) — SPA(React CRA) → 공개 JSON API 직수집 2026-06-13.

전환 사유 = 정적 코어 0파싱 확정(인박스 04:30 diag = body691B React CRA·정적 href 빈약).
  → SPA 코어(_us_spa_statute_core) netcap(XHR/fetch 응답 URL 캡처)으로 statute API 발굴.
★ netcap 실측 = index 페이지 로드 시 `https://iga.in.gov/ic/2025/Title_N.json` 공개 REST
  (Title 1~36 + 7.1 ≈ 40타이틀) 응답 캡처(run27440911901). 추정 아님·관찰 정본.
  api_re = 관찰된 `/ic/<연도>/Title_<번호>.json` 패턴만 일반화(셀렉터 추정 금지·계명1).
  http_json=True = Playwright 렌더 불요·urllib 직접 GET(공개 JSON·로그인/CAPTCHA 우회 안 함).
실행 = GHA(미국 IP) 전용. netcap=chromium / collect=urllib. 로컬 Playwright 금지(OOM)."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "in",
    "base": "https://iga.in.gov",
    "index_url": "https://iga.in.gov/laws/current/ic",
    "ext": ".json",
    "http_json": True,
    # api_re = netcap 발굴 statute API URL 패턴(관찰 정본·추정 금지).
    "api_re": re.compile(r"/ic/\d+/Title_[0-9.]+\.json$"),
}

if __name__ == "__main__":
    run(CONFIG)
