# -*- coding: utf-8 -*-
"""
전기세 얼마 — 가전제품별 전기요금 계산기 사이트를 통째로 만들어 내는 스크립트
실행: python3 build.py  →  dist/ 폴더에 사이트가 생깁니다. (추가 설치 없음)
- appliances.json : 가전 목록 (여기에 한 줄 추가하면 페이지가 하나 늘어납니다)
- links.json      : 가전별 제휴 링크 (넣으면 대가성 문구와 함께 표시)
- site.json       : 사이트 주소, 애드센스 ID 등
"""
import json, os, math, html, shutil, hashlib
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
SITE = json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))
APPS = json.load(open(os.path.join(ROOT, "appliances.json"), encoding="utf-8"))
LINKS = json.load(open(os.path.join(ROOT, "links.json"), encoding="utf-8"))
URL = (os.environ.get("SITE_URL") or SITE["url"]).rstrip("/")
BASE = "/" + "/".join(URL.split("/")[3:]) if len(URL.split("/")) > 3 else ""
BASE = BASE.rstrip("/")

# 주택용 전력(저압) 요금. 한전 요금표가 바뀌면 여기와 assets의 T 값을 같이 고칩니다.
TARIFF = {"base": [910, 1600, 7300], "rate": [120.0, 214.6, 307.3], "super": 736.2,
          "climate": 9.0, "fuel": 5.0, "vat": 0.10, "fund": 0.027}
DISC = {"coupang": "이 페이지는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.",
        "naver": "이 페이지는 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다."}


def limits(month):
    return [300, 450] if month in (7, 8) else [200, 400]


def bill(kwh, month):
    """월 사용량(kWh) → 청구 금액(원). 한전 계산 순서: 기본+전력량+기후환경+연료비 → 부가세(반올림) → 기금(10원 미만 버림)"""
    T, lim = TARIFF, limits(month)
    tier = 0 if kwh <= lim[0] else 1 if kwh <= lim[1] else 2
    e = min(kwh, lim[0]) * T["rate"][0] + max(0, min(kwh, lim[1]) - lim[0]) * T["rate"][1]
    if month in (7, 8, 12, 1, 2) and kwh > 1000:
        e += (1000 - lim[1]) * T["rate"][2] + (kwh - 1000) * T["super"]
    else:
        e += max(0, kwh - lim[1]) * T["rate"][2]
    sub = math.floor(T["base"][tier] + e + (T["climate"] + T["fuel"]) * kwh)
    vat = int(sub * T["vat"] + 0.5)
    fund = math.floor(sub * T["fund"] / 10) * 10
    return math.floor((sub + vat + fund) / 10) * 10


def added(base, add, month):
    return bill(base + add, month) - bill(base, month)


def won(n): return f"{int(n):,}"
def esc(s): return html.escape(str(s), quote=True)
def kwh_of(w, h, d): return round(w * h * d / 1000, 1)


def josa(word, a, b):
    """받침 있으면 a, 없으면 b (은/는, 을/를, 이/가)"""
    c = word.strip()[-1]
    if "가" <= c <= "힣": return a if (ord(c) - 0xAC00) % 28 else b
    return a if c.upper() in "LMNR136780" else b


def hours_txt(h):
    if h >= 1 and float(h).is_integer(): return f"{int(h)}시간"
    if h >= 1: return f"{int(h)}시간 {int(round((h - int(h)) * 60))}분"
    return f"{int(round(h * 60))}분"


def head(title, desc, path, extra=""):
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={esc(SITE["adsense_client"])}" crossorigin="anonymous"></script>'
           if SITE.get("adsense_client") else "")
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{URL}{path}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{URL}{path}">
<meta property="og:locale" content="ko_KR">
<link rel="icon" href="{BASE}/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{BASE}/s.css?v={VER}">
{ads}{extra}
<meta name="google-site-verification" content="E0MKLI_9g0wTNR9pjNKmxb_QGiA51AIK93dV9qBKumg"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8749404731911210" crossorigin="anonymous"></script><script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"전기세 얼마 계산기","url":"https://0520goeus.github.io/elec-calc/"}}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="logo" href="{BASE}/">{esc(SITE["name"])}</a>
  <nav><a href="{BASE}/#list">가전별 계산기</a><a href="{BASE}/about/">계산 기준</a><a href="{esc(SITE.get('price_note_url','https://0520goeus.github.io/price-note/'))}" rel="noopener">생필품 가격노트</a><a href="{esc(SITE.get('hub_url','https://0520goeus.github.io/life-money-lab/'))}" rel="noopener">생활비 연구소</a></nav>
</div></header>
<main class="wrap">
"""


def foot(script=True):
    return f"""<div style="margin:20px auto;max-width:960px;padding:16px 20px;border-radius:14px;background:linear-gradient(135deg,#0f172a,#0f766e);color:#fff;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;"><div><div style="font-weight:800;font-size:16px;">2026 직장인·1인셀러 무매크로 자동계산 엑셀 3종 올인원 번들</div><div style="font-size:13px;opacity:.9;margin-top:2px;">1인셀러 마진·ROAS + 내집마련 매물10개 비교 + 월급 가계부·순자산 대시보드 (즉시 다운로드)</div></div><a href="https://0520goeus.github.io/excel-store/" target="_blank" rel="noopener" style="background:#facc15;color:#0f172a;padding:10px 18px;border-radius:10px;font-weight:800;font-size:14px;text-decoration:none;white-space:nowrap;">3종 번들 즉시 다운로드 →</a></div>
</main>
<footer class="foot"><div class="wrap">
  <p>주택용 전력(저압) 요금표 기준, {esc(SITE["tariff_checked"])}에 확인했어요. 실제 청구 금액은 검침일, 할인, TV 수신료에 따라 달라져요.</p>
  <p><a href="{BASE}/about/">계산 기준과 한계</a> · <a href="{esc(SITE.get('price_note_url','https://0520goeus.github.io/price-note/'))}" rel="noopener">해뎐 가격노트</a> · <a href="{esc(SITE.get('hub_url','https://0520goeus.github.io/life-money-lab/'))}" rel="noopener">생활비 물가 연구소</a> · <a href="https://0520goeus.github.io/vs-pick/" rel="noopener">가성비 VS 비교 사전</a> · <a href="https://0520goeus.github.io/life-fee-calc/" rel="noopener">평수별 가전용량·직구관세</a> · <a href="https://0520goeus.github.io/money-calc-kr/" rel="noopener">연봉 실수령액</a> · <a href="https://0520goeus.github.io/benefit-calc-kr/" rel="noopener">지원금·실업급여 계산기</a> · <a href="https://0520goeus.github.io/seller-margin-calc/" rel="noopener">셀러 마진 계산기</a> · <a href="{esc(SITE["blog_url"])}" rel="noopener">생활해결 노트</a></p>
</div><div style="margin:14px auto 8px;max-width:960px;display:flex;flex-wrap:wrap;gap:6px;justify-content:center;font-size:12px;"><a href="https://0520goeus.github.io/house-calc-kr/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">부동산·대출·복비</a><a href="https://0520goeus.github.io/car-calc-kr/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">자동차세·유지비</a><a href="https://0520goeus.github.io/money-calc-kr/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">실수령액·금융</a><a href="https://0520goeus.github.io/benefit-calc-kr/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">2026 지원금</a><a href="https://0520goeus.github.io/life-fee-calc/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">평수가전·직구관세</a><a href="https://0520goeus.github.io/elec-calc/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">전기세 계산기</a><a href="https://0520goeus.github.io/vs-pick/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">가성비 VS 124종</a><a href="https://0520goeus.github.io/price-note/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">588 생필품 시세</a><a href="https://0520goeus.github.io/seller-margin-calc/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">셀러마진·엑셀</a><a href="https://0520goeus.github.io/kr-trend-brief/" style="padding:4px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:inherit;text-decoration:none;">실시간 트렌드</a></div>
</footer>
{f'<script src="{BASE}/c.js?v={VER}"></script>' if script else ''}
</body>
</html>
"""


def gauge():
    return """<div class="gauge" aria-hidden="true">
  <div class="g-bar"><i class="g-seg s1"></i><i class="g-seg s2"></i><i class="g-seg s3"></i><b class="g-pin before" id="pinA"><span>지금</span></b><b class="g-pin after" id="pinB"><span>더 쓰면</span></b></div>
  <div class="g-lab"><span>1구간</span><span>2구간</span><span>3구간</span></div>
</div>"""


def calc_box(a=None):
    d = SITE["default_base_kwh"]
    if a:
        chips = "".join(f'<button type="button" class="chip" data-w="{w}">{w:,}W</button>' for w in a["watts"])
        mid = a["watts"][1]
        top = f"""<div class="field"><label for="w">소비전력 <small>제품 라벨이나 상세페이지의 W 값</small></label>
      <div class="chips">{chips}</div>
      <div class="unit"><input id="w" type="number" inputmode="decimal" min="1" max="10000" value="{mid}"><span>W</span></div></div>
    <div class="two">
      <div class="field"><label for="h">하루 사용 시간</label><div class="unit"><input id="h" type="number" inputmode="decimal" min="0.1" max="24" step="0.1" value="{a['hours']}"><span>시간</span></div></div>
      <div class="field"><label for="d">한 달에 쓰는 날</label><div class="unit"><input id="d" type="number" inputmode="numeric" min="1" max="31" value="{a['days']}"><span>일</span></div></div>
    </div>"""
        res = """<div class="slip" aria-live="polite">
      <p class="slip-h">한 달에 늘어나는 요금</p>
      <p class="slip-big"><b id="rAdd">0</b>원</p>
      <dl>
        <div><dt>이 제품이 쓰는 전기</dt><dd><span id="rKwh">0</span> kWh</dd></div>
        <div><dt>지금 우리 집 요금</dt><dd><span id="rBefore">0</span>원</dd></div>
        <div><dt>이 제품을 쓴 뒤 요금</dt><dd><span id="rAfter">0</span>원</dd></div>
        <div><dt>누진 구간</dt><dd id="rTier">-</dd></div>
      </dl>
      <p class="slip-note" id="rNote"></p>
    </div>"""
    else:
        top = ""
        res = """<div class="slip" aria-live="polite">
      <p class="slip-h">이번 달 예상 전기요금</p>
      <p class="slip-big"><b id="rTotal">0</b>원</p>
      <dl>
        <div><dt>기본요금</dt><dd><span id="rBase">0</span>원</dd></div>
        <div><dt>전력량요금</dt><dd><span id="rEnergy">0</span>원</dd></div>
        <div><dt>기후환경·연료비조정</dt><dd><span id="rEtc">0</span>원</dd></div>
        <div><dt>부가세·전력기금</dt><dd><span id="rTax">0</span>원</dd></div>
        <div><dt>누진 구간</dt><dd id="rTier">-</dd></div>
      </dl>
      <p class="slip-note" id="rNote"></p>
    </div>"""
    months = "".join(f'<option value="{m}"{" selected" if m == NOW.month else ""}>{m}월</option>' for m in range(1, 13))
    return f"""<section class="calc" id="calc" data-mode="{'add' if a else 'bill'}">
  <form class="inputs" onsubmit="return false">
    {top}
    <div class="two">
      <div class="field"><label for="b">{'우리 집 평소 한 달 사용량' if a else '한 달 사용량'} <small>고지서의 사용량(kWh)</small></label><div class="unit"><input id="b" type="number" inputmode="numeric" min="0" max="3000" value="{d}"><span>kWh</span></div></div>
      <div class="field"><label for="m">계산할 달 <small>7~8월은 구간이 넓어져요</small></label><select id="m">{months}</select></div>
    </div>
  </form>
  <div class="result">{res}{gauge()}</div>
</section>"""


def ad_slot():
    if not SITE.get("adsense_client"): return ""
    return (f'<div class="ad"><ins class="adsbygoogle" style="display:block" data-ad-client="{esc(SITE["adsense_client"])}" '
            'data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></div>')


def coupang_banner():
    w = SITE.get("coupang_widget_html", "")
    if not w: return ""
    return f'<section class="shop"><p class="disc">{esc(DISC["coupang"])}</p><h2>절전·생활 가전 인기 상품</h2>{w}</section>'


def link_box(slug):
    items = [x for x in LINKS.get(slug, []) if isinstance(x, dict) and str(x.get("url", "")).startswith("http")]
    if not items: return coupang_banner()
    kinds = {("coupang" if "coupang" in x["url"] or "coupa.ng" in x["url"] else "naver") for x in items}
    disc = " ".join(DISC[k] for k in sorted(kinds))
    lis = "".join(f'<li><a href="{esc(x["url"])}" rel="sponsored nofollow noopener" target="_blank">{esc(x.get("label") or "상품 보기")}</a></li>' for x in items)
    return f'<section class="shop"><p class="disc">{esc(disc)}</p><h2>살펴볼 상품</h2><ul>{lis}</ul></section>' + coupang_banner()


def appliance_page(a):
    n, m = a["name"], NOW.month
    mid = a["watts"][1]
    k_mid = kwh_of(mid, a["hours"], a["days"])
    x250 = added(250, k_mid, m)
    x150, x350 = added(150, k_mid, m), added(350, k_mid, m)
    rows = ""
    for w in a["watts"]:
        k = kwh_of(w, a["hours"], a["days"])
        rows += (f"<tr><th scope='row'>{w:,}W</th><td>{k:g} kWh</td>"
                 + "".join(f"<td>{won(added(b, k, m))}원</td>" for b in (150, 250, 350)) + "</tr>")
    ht = hours_txt(a["hours"])
    faq = [
        (f"{n} 하루 {ht} 쓰면 한 달 전기요금은 얼마나 나오나요?",
         f"{mid:,}W 제품을 하루 {ht}, 한 달에 {a['days']}일 쓰면 약 {k_mid:g}kWh를 써요. 평소 250kWh를 쓰는 집이라면 {m}월 요금이 약 {won(x250)}원 늘어요. 주택용 전력(저압) 요금표로 계산한 값이에요."),
        (f"같은 {n}인데 왜 집마다 늘어나는 요금이 다른가요?",
         f"주택용 전기요금은 많이 쓸수록 단가가 올라가는 누진제예요. 같은 {k_mid:g}kWh를 더 써도 평소 150kWh를 쓰는 집은 약 {won(x150)}원, 350kWh를 쓰는 집은 약 {won(x350)}원이 늘어요."),
        (f"{n} 소비전력은 어디서 확인하나요?",
         "제품 뒷면이나 바닥의 정격 라벨, 사용설명서, 판매 페이지의 상세 사양에 '정격 소비전력'이 W 단위로 적혀 있어요. 에너지소비효율 등급 라벨이 붙은 제품은 월간 또는 연간 소비전력량(kWh)도 같이 나와요."),
    ]
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": t}} for q, t in faq]}
    same = [x for x in APPS if x["cat"] == a["cat"] and x["slug"] != a["slug"]][:6]
    others = [x for x in APPS if x["cat"] != a["cat"]][:4]
    title = f"{n} 전기세 계산기 | 하루 {ht} 쓰면 한 달 얼마 ({NOW.year}년 {m}월)"
    desc = f"{n}({a['aka']}) 소비전력과 사용 시간을 넣으면 누진제까지 반영해 한 달 전기요금이 얼마나 늘어나는지 계산해요. {mid:,}W를 하루 {ht} 쓰면 약 {won(x250)}원."
    path = f"/a/{a['slug']}/"
    body = head(title, desc, path, f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')
    body += f"""<p class="crumb"><a href="{BASE}/">전기요금 계산기</a> / {esc(a['cat'])} 가전</p>
<h1>{esc(n)} 전기세 계산기</h1>
<p class="lede">{esc(n)}{josa(n, '을', '를')} 쓰면 이번 달 전기요금이 얼마나 늘어나는지, 우리 집 누진 구간까지 넣어서 계산해요.</p>
{calc_box(a)}
{ad_slot()}
<section>
  <h2>소비전력별 한 달 요금</h2>
  <p>하루 {ht}, 한 달 {a['days']}일 쓰는 경우예요. 평소 사용량이 많은 집일수록 같은 제품을 써도 더 많이 늘어나요. {m}월 요금표 기준이에요.</p>
  <div class="scroll"><table>
    <thead><tr><th scope="col">소비전력</th><th scope="col">한 달 사용량</th><th scope="col">평소 150kWh 집</th><th scope="col">평소 250kWh 집</th><th scope="col">평소 350kWh 집</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  <p class="note">{esc(a['tip'])}{' 표의 값은 최대 소비전력으로 계속 켜 둔 경우라 실제보다 크게 나올 수 있어요.' if a['cycle'] else ''}</p>
</section>
{link_box(a['slug'])}
<section>
  <h2>자주 묻는 질문</h2>
  {''.join(f'<details><summary>{esc(q)}</summary><p>{esc(t)}</p></details>' for q, t in faq)}
</section>
<section>
  <h2>다른 가전도 계산해 보기</h2>
  <ul class="more">{''.join(f'<li><a href="{BASE}/a/{x["slug"]}/">{esc(x["name"])} 전기세</a></li>' for x in same + others)}</ul>
</section>
"""
    return path, body + foot()


def home_page():
    m = NOW.month
    lim = limits(m)
    cats = []
    for a in APPS:
        if a["cat"] not in cats: cats.append(a["cat"])
    groups = ""
    for c in cats:
        items = ""
        for a in [x for x in APPS if x["cat"] == c]:
            k = kwh_of(a["watts"][1], a["hours"], a["days"])
            items += (f'<li><a href="{BASE}/a/{a["slug"]}/"><b>{esc(a["name"])}</b>'
                      f'<span>{a["watts"][1]:,}W, 하루 {hours_txt(a["hours"])}</span><em>+{won(added(250, k, m))}원</em></a></li>')
        groups += f'<h3>{esc(c)}</h3><ul class="grid">{items}</ul>'
    T = TARIFF
    title = f"전기요금 계산기 | 가전제품별 한 달 전기세 ({NOW.year}년 {m}월 요금표)"
    desc = "한 달 사용량을 넣으면 누진제, 부가세, 전력기금까지 넣어 전기요금을 계산해요. 전기요, 에어컨, 제습기 같은 가전 하나가 요금을 얼마나 올리는지도 볼 수 있어요."
    body = head(title, desc, "/")
    body += f"""<h1>이번 달 전기요금, 얼마 나올까요</h1>
<p class="lede">고지서에 찍힌 사용량을 넣으면 누진제와 세금까지 계산해요. 가전 하나를 더 쓸 때 늘어나는 요금은 아래 가전별 계산기에서 볼 수 있어요.</p>
{calc_box()}
{ad_slot()}
{coupang_banner()}
<section id="list">
  <h2>가전 하나가 올리는 한 달 요금</h2>
  <p>평소 250kWh를 쓰는 집에서 {m}월에 쓰는 경우예요. 눌러서 우리 집 조건으로 다시 계산해 보세요.</p>
  {groups}
</section>
<section>
  <h2>{m}월 주택용 전력(저압) 요금표</h2>
  <div class="scroll"><table>
    <thead><tr><th scope="col">구간</th><th scope="col">사용량</th><th scope="col">기본요금</th><th scope="col">전력량요금</th></tr></thead>
    <tbody>
      <tr><th scope="row">1구간</th><td>{lim[0]}kWh 이하</td><td>{won(T['base'][0])}원</td><td>{T['rate'][0]}원/kWh</td></tr>
      <tr><th scope="row">2구간</th><td>{lim[0] + 1}~{lim[1]}kWh</td><td>{won(T['base'][1])}원</td><td>{T['rate'][1]}원/kWh</td></tr>
      <tr><th scope="row">3구간</th><td>{lim[1]}kWh 초과</td><td>{won(T['base'][2])}원</td><td>{T['rate'][2]}원/kWh</td></tr>
    </tbody>
  </table></div>
  <p class="note">여기에 기후환경요금 {T['climate']:g}원/kWh, 연료비조정요금 {T['fuel']:g}원/kWh, 부가가치세 10%, 전력산업기반기금 {T['fund'] * 100:g}%가 더해져요. 7~8월에는 구간 경계가 300kWh, 450kWh로 넓어져요.</p>
</section>
"""
    return "/", body + foot()


def about_page():
    T = TARIFF
    body = head(f"계산 기준과 한계 | {SITE['name']}", "이 사이트가 전기요금을 계산하는 방법과 실제 고지서와 달라질 수 있는 이유를 적었어요.", "/about/")
    body += f"""<h1>계산 기준과 한계</h1>
<section>
  <h2>어떻게 계산하나요</h2>
  <p>한국전력의 주택용 전력(저압) 요금표를 씁니다. 기본요금과 전력량요금을 누진 구간에 따라 구하고, 기후환경요금({T['climate']:g}원/kWh)과 연료비조정요금({T['fuel']:g}원/kWh)을 더한 뒤 부가가치세 10%(원 미만 반올림)와 전력산업기반기금 {T['fund'] * 100:g}%(10원 미만 버림)를 붙입니다. 요금표는 {esc(SITE['tariff_checked'])}에 확인했어요.</p>
  <p>가전제품이 올리는 요금은 "평소 사용량 + 그 제품의 사용량"으로 계산한 요금에서 "평소 사용량"만으로 계산한 요금을 뺀 값이에요. 그래서 누진 구간이 바뀌는 집에서는 같은 제품도 더 비싸게 계산돼요.</p>
</section>
<section>
  <h2>실제 고지서와 다를 수 있는 이유</h2>
  <ul class="plain">
    <li>가전제품은 라벨의 소비전력으로 계속 돌지 않아요. 온도나 습도가 맞으면 쉬는 제품은 실제 사용량이 더 적어요.</li>
    <li>아파트 고압 요금, 복지 할인, 대가족 할인, 자동이체 할인, TV 수신료는 넣지 않았어요.</li>
    <li>검침일에 따라 한 달의 기준이 달라져요. 7~8월 구간이 며칠씩 섞여 적용되기도 해요.</li>
    <li>연료비조정단가는 분기마다 바뀔 수 있어요. 정확한 금액은 한전ON에서 확인하세요.</li>
  </ul>
</section>
<section>
  <h2>운영</h2>
  <p>개인이 운영하는 사이트예요. 상품 링크가 있는 페이지에는 링크 바로 위에 수수료를 받는다는 문구를 적어요. 숫자가 틀린 곳을 발견하면 <a href="{esc(SITE['blog_url'])}" rel="noopener">운영자 블로그</a>에 알려 주세요.</p>
</section>
"""
    return "/about/", body + foot(script=False)


CSS = r""":root{--bg:#EEF1F4;--sheet:#fff;--ink:#15202B;--sub:#5B6875;--line:#D5DBE2;--accent:#0B5FFF;--accent-ink:#fff;
--t1:#3DAE7C;--t2:#F2B63D;--t3:#E2573C;--slip:#FFFDF5;--slip-line:#E6DFC6;
--font:"Pretendard Variable",Pretendard,-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#0F151B;--sheet:#17202A;--ink:#E7ECF1;--sub:#9AA7B4;--line:#2A3541;--accent:#6EA2FF;--accent-ink:#0B1220;--slip:#1D2630;--slip-line:#33404D;color-scheme:dark}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 var(--font);word-break:keep-all;overflow-wrap:anywhere}
a{color:var(--accent)}
.wrap{max-width:860px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left));padding-right:max(16px,env(safe-area-inset-right))}
.top{background:var(--sheet);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding-block:12px}
.logo{font-weight:800;font-size:18px;color:var(--ink);text-decoration:none;letter-spacing:-.02em}
.top nav{display:flex;gap:16px;font-size:14px}.top nav a{color:var(--sub);text-decoration:none}.top nav a:hover{color:var(--ink)}
main{padding-block:28px 56px;display:grid;gap:28px}
main>*{min-width:0}
.crumb{margin:0;font-size:13px;color:var(--sub)}.crumb a{color:var(--sub)}
h1{font-size:clamp(26px,5vw,36px);line-height:1.25;letter-spacing:-.03em;margin:0;text-wrap:balance}
h2{font-size:21px;letter-spacing:-.02em;margin:0 0 10px}
h3{font-size:14px;color:var(--sub);font-weight:600;margin:20px 0 8px}
p{margin:0 0 10px}
.lede{color:var(--sub);font-size:17px;max-width:38em;margin:-16px 0 0}
.note{color:var(--sub);font-size:14px;margin-top:10px}
section{display:block}
.calc{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;background:var(--sheet);border:1px solid var(--line);border-radius:14px;padding:22px}
@media (max-width:720px){.calc{grid-template-columns:minmax(0,1fr);padding:16px}}
.inputs{display:grid;gap:16px;align-content:start}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.field{display:grid;gap:6px;min-width:0}
label{font-size:14px;font-weight:600}label small{display:block;font-weight:400;color:var(--sub);font-size:12.5px}
input,select{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:10px 12px;width:100%;min-width:0;font-variant-numeric:tabular-nums}
input:focus-visible,select:focus-visible,.chip:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.unit{position:relative}.unit span{position:absolute;right:12px;top:50%;transform:translateY(-50%);color:var(--sub);font-size:14px;pointer-events:none}.unit input{padding-right:52px}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{font:inherit;font-size:13.5px;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:999px;padding:5px 12px;cursor:pointer;font-variant-numeric:tabular-nums}
.chip.on{background:var(--ink);color:var(--sheet);border-color:var(--ink)}
.result{display:grid;gap:16px;align-content:start;min-width:0}
/* 고지서 조각: 결과는 영수증처럼 항목과 금액을 점선으로 잇는다 */
.slip{background:var(--slip);border:1px solid var(--slip-line);border-radius:4px;padding:18px 18px 14px;position:relative}
.slip::before,.slip::after{content:"";position:absolute;left:0;right:0;height:6px;background:radial-gradient(circle at 6px -1px,var(--sheet) 5px,transparent 5.5px) 0 0/12px 6px repeat-x}
.slip::before{top:-1px}.slip::after{bottom:-1px;transform:scaleY(-1)}
.slip-h{margin:0;font-size:13.5px;color:var(--sub)}
.slip-big{margin:2px 0 12px;font-size:20px;font-weight:600}
.slip-big b{font-size:clamp(34px,8vw,46px);letter-spacing:-.03em;font-variant-numeric:tabular-nums;font-weight:800}
.slip dl{margin:0;display:grid;gap:6px;font-size:14.5px}
.slip dl div{display:flex;align-items:baseline;gap:8px}
.slip dt{color:var(--sub);flex:none}
.slip dd{margin:0;flex:1;text-align:right;font-variant-numeric:tabular-nums;display:flex;gap:8px;align-items:baseline;justify-content:flex-end}
.slip dd::before{content:"";flex:1;border-bottom:1px dotted var(--sub);opacity:.5;transform:translateY(-4px)}
.slip-note{margin:12px 0 0;font-size:13.5px;color:var(--t3);font-weight:600}
.slip-note:empty{display:none}
.gauge{display:grid;gap:6px;padding-top:22px}
.g-bar{position:relative;display:flex;height:12px;border-radius:6px;overflow:visible}
.g-seg{flex:1;display:block}.s1{background:var(--t1);border-radius:6px 0 0 6px}.s2{background:var(--t2)}.s3{background:var(--t3);border-radius:0 6px 6px 0}
.g-pin{position:absolute;top:-5px;width:3px;height:22px;background:var(--ink);border-radius:2px;transition:left .35s ease;left:0}
.g-pin span{position:absolute;bottom:26px;left:50%;transform:translateX(-50%);font-size:11.5px;font-weight:600;white-space:nowrap;background:var(--ink);color:var(--sheet);padding:1px 6px;border-radius:4px}
.g-pin.before{opacity:.45}.g-pin.before span{bottom:auto;top:26px}
.g-lab{display:flex;font-size:12px;color:var(--sub);margin-top:18px}.g-lab span{flex:1;text-align:center}
@media (prefers-reduced-motion:reduce){.g-pin{transition:none}}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--sheet)}
table{border-collapse:collapse;width:100%;font-size:14.5px;font-variant-numeric:tabular-nums}
th,td{padding:10px 12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
thead th{font-size:13px;color:var(--sub);font-weight:600;background:var(--bg)}
tbody tr:last-child>*{border-bottom:0}
.grid{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}
.grid a{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:12px 14px;background:var(--sheet);border:1px solid var(--line);border-radius:10px;text-decoration:none;color:var(--ink)}
.grid a:hover{border-color:var(--ink)}
.grid b{font-weight:700}.grid span{grid-column:1;font-size:12.5px;color:var(--sub)}
.grid em{grid-column:2;grid-row:1/3;align-self:center;font-style:normal;font-weight:700;font-variant-numeric:tabular-nums;font-size:14.5px}
details{background:var(--sheet);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:8px}
summary{cursor:pointer;font-weight:600}details p{margin:8px 0 0;color:var(--sub)}
.more{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.more a{display:block;padding:7px 12px;border:1px solid var(--line);border-radius:999px;background:var(--sheet);text-decoration:none;color:var(--ink);font-size:14px}
.plain{margin:0;padding-left:20px;display:grid;gap:6px}
.shop{background:var(--sheet);border:1px solid var(--line);border-radius:12px;padding:16px}
.shop .disc{font-size:13px;color:var(--sub);margin-bottom:10px}
.shop ul{margin:0;padding-left:20px;display:grid;gap:4px}
.ad{min-height:100px}
.foot{border-top:1px solid var(--line);padding-block:20px 36px;color:var(--sub);font-size:13px}
.foot a{color:var(--sub)}
"""

JS = r"""(function(){
var T=__TARIFF__;
function lim(m){return (m==7||m==8)?[300,450]:[200,400];}
function parts(k,m){var l=lim(m),t=k<=l[0]?0:k<=l[1]?1:2;
  var e=Math.min(k,l[0])*T.rate[0]+Math.max(0,Math.min(k,l[1])-l[0])*T.rate[1];
  if((m==7||m==8||m==12||m<=2)&&k>1000) e+=(1000-l[1])*T.rate[2]+(k-1000)*T["super"]; else e+=Math.max(0,k-l[1])*T.rate[2];
  var etc=(T.climate+T.fuel)*k, sub=Math.floor(T.base[t]+e+etc), vat=Math.round(sub*T.vat), fund=Math.floor(sub*T.fund/10)*10;
  return {tier:t,base:T.base[t],energy:Math.floor(e),etc:Math.floor(etc),tax:vat+fund,total:Math.floor((sub+vat+fund)/10)*10};}
function $(i){return document.getElementById(i);}
function num(i,d){var el=$(i); if(!el) return d; var v=parseFloat(el.value); return isFinite(v)&&v>=0?v:d;}
function won(n){return Math.round(n).toLocaleString('ko-KR');}
function pos(k,m){var l=lim(m),max=l[1]*1.5; if(k<=l[0]) return k/l[0]/3*100; if(k<=l[1]) return (1+(k-l[0])/(l[1]-l[0]))/3*100; return Math.min(100,(2+(k-l[1])/(max-l[1]))/3*100);}
function set(i,v){var el=$(i); if(el) el.textContent=v;}
var box=$('calc'); if(!box) return;
var mode=box.getAttribute('data-mode');
function run(){
  var m=parseInt($('m').value,10), b=num('b',0), names=['1구간','2구간','3구간'];
  if(mode==='add'){
    var add=num('w',0)*num('h',0)*num('d',0)/1000, A=parts(b,m), B=parts(b+add,m);
    set('rKwh',(Math.round(add*10)/10).toLocaleString('ko-KR')); set('rAdd',won(B.total-A.total)); set('rBefore',won(A.total)); set('rAfter',won(B.total));
    set('rTier',A.tier===B.tier?names[A.tier]+' 그대로':names[A.tier]+'에서 '+names[B.tier]+'으로');
    set('rNote',B.tier>A.tier?'누진 구간이 올라가서 단가가 비싸져요. 사용 시간을 줄이면 구간을 지킬 수 있는지 숫자를 바꿔 보세요.':'');
    $('pinA').style.left=pos(b,m)+'%'; $('pinB').style.left=pos(b+add,m)+'%';
    var w=num('w',0); [].forEach.call(document.querySelectorAll('.chip'),function(c){c.classList.toggle('on',parseFloat(c.getAttribute('data-w'))===w);});
  } else {
    var P=parts(b,m); set('rTotal',won(P.total)); set('rBase',won(P.base)); set('rEnergy',won(P.energy)); set('rEtc',won(P.etc)); set('rTax',won(P.tax));
    var l=lim(m), left=P.tier<2?(l[P.tier]-b):0;
    set('rTier',names[P.tier]); set('rNote',P.tier<2&&left<=30?'다음 구간까지 '+Math.max(0,Math.round(left))+'kWh 남았어요. 넘으면 단가가 올라가요.':'');
    $('pinB').style.left=pos(b,m)+'%'; $('pinA').style.display='none'; $('pinB').firstChild.textContent='우리 집';
  }
}
[].forEach.call(box.querySelectorAll('input,select'),function(el){el.addEventListener('input',run);});
[].forEach.call(document.querySelectorAll('.chip'),function(c){c.addEventListener('click',function(){$('w').value=c.getAttribute('data-w');run();});});
run();
})();"""

FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#15202B"/>'
           '<path d="M18 4 8 18h7l-2 10 11-15h-7z" fill="#F2B63D"/></svg>')

VER = hashlib.md5((CSS + JS + json.dumps(TARIFF)).encode()).hexdigest()[:8]


def write(path, text):
    full = os.path.join(DIST, path.strip("/"), "index.html") if path.endswith("/") or path == "/" else os.path.join(DIST, path.strip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(text)


def main():
    if os.path.isdir(DIST): shutil.rmtree(DIST)
    os.makedirs(DIST)
    pages = [home_page(), about_page()] + [appliance_page(a) for a in APPS]
    for path, text in pages: write(path, text)
    write("s.css", CSS)
    write("c.js", JS.replace("__TARIFF__", json.dumps(TARIFF)))
    write("favicon.svg", FAVICON)
    write("404.html", head(f"페이지를 찾지 못했어요 | {SITE['name']}", "주소가 바뀌었거나 없는 페이지예요.", "/404.html")
          + f'<h1>페이지를 찾지 못했어요</h1><p class="lede">주소가 바뀌었거나 없는 페이지예요. <a href="{BASE}/">계산기 첫 화면</a>에서 다시 찾아보세요.</p>' + foot(script=False))
    today = NOW.strftime("%Y-%m-01")
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"<url><loc>{URL}{p}</loc><lastmod>{today}</lastmod></url>\n" for p, _ in pages) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n")
    write("urls.txt", "\n".join(URL + p for p, _ in pages) + "\n")
    if SITE.get("adsense_client"):
        write("ads.txt", f"google.com, {SITE['adsense_client'].replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n")
    if SITE.get("indexnow_key"):
        write(SITE["indexnow_key"] + ".txt", SITE["indexnow_key"])
    if SITE.get("naver_verification"):
        write(SITE["naver_verification"], f"naver-site-verification: {SITE['naver_verification']}")
    if SITE.get("google_file"):
        write(SITE["google_file"], f"google-site-verification: {SITE['google_file']}")
    write(".nojekyll", "")
    print(f"{len(pages)}쪽을 만들었어요 → dist/  ({NOW:%Y-%m-%d %H:%M} 기준, {NOW.month}월 요금표)")


if __name__ == "__main__":
    main()
