#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""오클라호마 법전 (oscn.net OSCN) — ④HTML파서. 매트릭스 지정 대체 호스트로 전환 2026-06-13.
oklegislature.gov TitleIndex.aspx = SPA(__doPostBack)·netcap 0XHR(run 27444369856) → 수집 불가.
→ 매트릭스 지정 oscn.net(Oklahoma Statutes Citationized) 정적 .asp 트리 전환.
관찰[측정:WebSearch 2026-06-13] = index.asp?ftdb=STOKST&level=1(전 타이틀) →
  Index.asp?ftdb=STOKSTNN&level=1(타이틀별 섹션 목록) → DeliverDocument.asp?CiteID=NNN(본문).
  2단 트리 = chapter_re(타이틀 STOKSTNN) → link_re(DeliverDocument CiteID).
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제.
★ link_re/chapter_re 미기재 = GHA --diag href 실측 후 보정(추정 금지·계명1)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "ok",
    "base": "https://www.oscn.net",
    "index_url": "https://www.oscn.net/applications/oscn/index.asp?level=1&ftdb=STOKST",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
