#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""매사추세츠 법전 (malegislature.gov) — JS 렌더 트리 확정 2026-06-13.
헤더 보정(07a8725)으로 정적 200 도달(rediag run27438905611 link_re=11).
★ 다단 진입점 측정 = GeneralLaws 루트에 Part 진입점 5개(PartI~PartV) 실재(run27440421293
  깊이분포 3:5). 그러나 PartI 페이지(run27440508871 status200·body120KB) statute href=0
  = Title/Chapter/Section 트리가 전부 클라이언트 JS 렌더(정적 href 부재).
★ 결론 = 정적 코어로 루트 아래 진입 불가. statute 목록 API URL 미측정 → 추정 금지(계명1).
  선행과제 = Playwright network-capture 로 XHR/fetch statute API 엔드포인트 데이터 발굴.
chapter_re 는 정적 루트에 chapter 직링크가 없어 매칭 0(무해·보존). 실행 = GHA(미국 IP)."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "ma",
    "base": "https://malegislature.gov",
    "index_url": "https://malegislature.gov/Laws/GeneralLaws",
    "ext": ".html",
    # chapter 목록 링크(Section 없이 Chapter 로 끝) — 관찰 섹션 URL 파생·diag 검증 전제
    "chapter_re": re.compile(
        r'href=["\']([^"\']*/Laws/GeneralLaws/Part[A-Za-z]+/Title[A-Za-z]+/Chapter[0-9A-Za-z]+)["\']',
        re.IGNORECASE,
    ),
}

if __name__ == "__main__":
    run(CONFIG)
