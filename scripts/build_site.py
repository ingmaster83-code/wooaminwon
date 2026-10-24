# -*- coding: utf-8 -*-
"""우아민원 정적 사이트 생성기 → _site/.  사용: python scripts/build_site.py"""
import sys, json, re, shutil, time, collections
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *

A = json.loads((ROOT / "data" / "agencies.json").read_text(encoding="utf-8"))
MASTER = json.loads((ROOT / "data" / "master_sg.json").read_text(encoding="utf-8"))
ASOF = "2026년"

def table(heads, rows, num=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)

def chips(items): return '<div class="chips">%s</div>' % "".join('<a class="chip" href="%s">%s</a>' % (u, esc(t)) for t, u in items)
def sl(s): return re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-") or "x"

KINDS = [
    ("세무서", "세무서", "국세청", "국세청 소속 세무서는 세금 신고·납부, 사업자등록, 세무 상담 등을 처리합니다. 국세 상담 전화는 126입니다."),
    ("건강보험", "건강보험공단 지사", "국민건강보험공단", "국민건강보험공단 지사는 건강보험 가입·자격, 보험료, 급여 문의를 처리합니다. 대표 전화는 1577-1000입니다."),
    ("국민연금", "국민연금공단 지사", "국민연금공단", "국민연금공단 지사는 국민연금 가입·납부·수령 상담을 처리합니다. 국민연금 상담 전화는 1355입니다."),
    ("고용센터", "고용복지플러스센터", "고용노동부", "고용복지플러스센터는 구직 상담, 실업급여, 직업훈련, 복지 연계 서비스를 한 곳에서 제공합니다. 고용노동부 상담 전화는 1350입니다."),
    ("근로복지공단", "근로복지공단 지사", "근로복지공단", "근로복지공단 지사는 산재보험 접수·상담과 퇴직연금, 근로자 복지 업무를 처리합니다."),
    ("노동청", "고용노동청·지청", "고용노동부", "지방고용노동청과 지청은 근로감독, 임금체불 진정 등 노동 관련 민원을 처리합니다. 고용노동부 상담 전화는 1350입니다."),
    ("병무청", "지방병무청 병역판정검사장", "병무청", "지방병무청은 병역판정검사(신체검사)와 병역 관련 민원을 처리합니다. 병역판정검사장은 거주지에 따라 정해집니다."),
    ("보훈", "보훈청·지청", "국가보훈부", "지방보훈청과 보훈지청은 국가유공자 등록·보훈 급여·보훈 서비스 상담을 처리합니다."),
    ("출입국", "출입국·외국인관서", "법무부", "출입국·외국인청(사무소·출장소)은 외국인의 체류·비자 민원을 처리합니다. 외국인종합안내센터 전화는 1345입니다."),
]
KD = {k: (lab, org, desc) for k, lab, org, desc in KINDS}
NOTE = "관공서 정보는 각 기관이 공공데이터포털에 공개한 자료(%s 기준)를 정리한 참고용입니다. 관할구역은 행정동 단위로 나뉘는 경우가 있고 기관 이전·개편으로 바뀔 수 있으니 방문 전 해당 기관에 확인하세요." % ASOF
SIDO_ORDER = ["서울특별시", "부산광역시", "대구광역시", "인천광역시", "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도", "충청북도", "충청남도", "전북특별자치도", "전남광주통합특별시", "경상북도", "경상남도", "제주특별자치도"]
MASTER_KEYS = {(m["sido"], m["sg"]) for m in MASTER}

for a in A:
    a["slug"] = sl(a["name"]); a["path"] = "/agency/%s/%s/" % (a["kind"], a["slug"])
    a["cov"] = [tuple(c) for c in a["cov"]]; a["loc"] = tuple(a["loc"]) if a["loc"] else None
used = set()
for a in A:
    s = a["slug"]; n = 2
    while (a["kind"], s) in used: s = "%s-%d" % (a["slug"], n); n += 1
    used.add((a["kind"], s)); a["slug"] = s; a["path"] = "/agency/%s/%s/" % (a["kind"], s)
COVER = collections.defaultdict(list); LOCATED = collections.defaultdict(list); BY_KIND = collections.defaultdict(list)
for a in A:
    BY_KIND[a["kind"]].append(a)
    for c in a["cov"]: COVER[c].append(a)
    if a["loc"]: LOCATED[a["loc"]].append(a)
# 지역 키: 마스터 + 커버 + 소재지
REGION_KEYS = sorted(set(MASTER_KEYS) | set(COVER) | set(LOCATED) | {(a["loc"][0], a["loc"][1]) for a in A if a["loc"]}, key=lambda k: (SIDO_ORDER.index(k[0]) if k[0] in SIDO_ORDER else 99, k[1]))
SIDOS = [s for s in SIDO_ORDER if any(k[0] == s for k in REGION_KEYS)]
REAL = [a for a in A if a["sub"] not in ("병원", "기타")]

def rp(k): return "/region/%s/%s/" % (k[0], k[1])
def alink(a): return '<a href="%s">%s</a>' % (a["path"], esc(a["name"]))
def short_j(a, n=60):
    j = re.sub(r"\s+", " ", a.get("juris", "") or "").strip()
    return esc(j if len(j) <= n else j[:n].rstrip() + "…")

# ───────────────────────── 기관 ─────────────────────────
def page_agency(a):
    lab, org, desc = KD[a["kind"]]
    peers = [x for x in (LOCATED.get(a["loc"], []) if a["loc"] else []) if x is not a and x["kind"] != a["kind"]][:8]
    same = [x for x in BY_KIND[a["kind"]] if x is not a and a["loc"] and x["loc"] and x["loc"][0] == a["loc"][0] and x["sub"] not in ("병원", "기타")][:8]
    covers = a["cov"]
    lead = (f"<p class=\"lead\"><b>{esc(a['name'])}</b>은(는) {org}의 {lab}{('(' + esc(a['sub']) + ')') if a['sub'] != lab and a['sub'] not in lab else ''}입니다. 주소는 {esc(a['addr']) or '정보 없음'}{(', 전화번호는 <b>' + esc(a['tel']) + '</b>') if a['tel'] else ''}입니다. "
            f"{('관할구역은 <b>' + short_j(a, 120) + '</b>입니다. ') if a.get('juris') else ''}{desc}</p>")
    rows = [["기관", esc(a["name"])], ["구분", lab if a["sub"] in lab or a["sub"] == lab else "%s · %s" % (lab, esc(a["sub"]))]]
    if a["addr"]: rows.append(["주소", esc(a["addr"])])
    if a.get("zip"): rows.append(["우편번호", esc(a["zip"])])
    if a["tel"]: rows.append(["전화", '<a href="tel:%s">%s</a>' % (re.sub(r"[^0-9]", "", a["tel"].split("~")[0].split("(")[0]), esc(a["tel"]))])
    if a.get("fax"): rows.append(["팩스", esc(a["fax"])])
    if a.get("hours"): rows.append(["이용시간", esc(a["hours"])])
    if a.get("juris"): rows.append(["관할구역", esc(re.sub(r"\s+", " ", a["juris"]))])
    if a.get("home"): rows.append(["홈페이지", '<a href="%s" rel="nofollow noopener" target="_blank">%s</a>' % (esc(a["home"]), esc(a["home"]))])
    t1 = table(["항목", "내용"], rows)
    cov = ""
    if covers:
        cov = '<h2 class="group-title">📍 관할 시군구</h2>' + chips([("%s %s" % (c[0].replace("특별자치도", "").replace("특별시", "").replace("광역시", "").replace("특별자치시", ""), c[1]), rp(c)) for c in covers[:60]]) + ('<p class="note">일부 지역(동·면 단위)만 관할하거나 제외되는 곳이 있습니다. 정확한 관할은 기관에 확인하세요.</p>' if a["partial"] else "") + (("<p class=\"lead\">외 %d곳</p>" % (len(covers) - 60)) if len(covers) > 60 else "")
    ps = ('<h2 class="group-title">🏛️ 같은 지역의 다른 관공서</h2>' + table(["기관", "구분", "전화"], [[alink(x), KD[x["kind"]][0], esc(x["tel"] or "-")] for x in peers])) if peers else ""
    sm = ('<h2 class="group-title">🔁 같은 종류의 인근 기관</h2>' + table(["기관", "소재지", "전화"], [[alink(x), esc(x["addr"][:30]), esc(x["tel"] or "-")] for x in same])) if same else ""
    body = f"""
<div class="page-head"><h1>{esc(a['name'])} — 전화번호·주소·관할구역</h1><p>{lab} · {org}</p></div>
{lead}
{ad()}
<h2 class="group-title">📋 기관 정보</h2>
{t1}
{cov}
{ps}
{sm}
<p class="note">{NOTE}</p>
{chips([(lab + " 전체", "/type/%s/" % a["kind"]), ("지역별 관공서", "/region/"), ("관할 관공서 찾는 법", "/guide/")] + ([(a["loc"][1] + " 관공서", rp(a["loc"]))] if a["loc"] else []))}
"""
    faq = [(f"{a['name']} 전화번호는?", a["tel"] or "공공데이터에 전화번호가 없습니다. 기관 대표번호를 확인하세요."), (f"{a['name']} 주소는?", a["addr"] or "정보가 없습니다."), (f"{a['name']} 관할은 어디까지인가요?", (re.sub(r"\s+", " ", a["juris"]) if a.get("juris") else "공공데이터에 관할구역 정보가 없습니다."))]
    write(a["path"], layout(a["path"], f"{a['name']} — 전화번호·주소·관할구역 ({lab})", f"{a['name']}({lab}) 전화 {a['tel'] or '-'}, 주소 {a['addr'] or '-'}. 관할구역과 인근 관공서 안내.", body, faq, [("홈", "/"), (lab, "/type/%s/" % a["kind"]), (a["name"], a["path"])]), "0.5")

# ───────────────────────── 지역 ─────────────────────────
def page_region(k):
    sido, sg = k
    cover = COVER.get(k, []); loc = LOCATED.get(k, [])
    rows = []; nk = 0
    for kind, lab, org, _ in KINDS:
        cs = [a for a in cover if a["kind"] == kind and a["sub"] != "지방국세청"]
        if kind == "국민연금":
            cs = [a for a in loc if a["kind"] == kind]
            note_loc = True
        for a in cs:
            rows.append([lab, alink(a), esc(a["tel"] or "-"), ("일부 지역" if a["partial"] and kind != "국민연금" else ("이 지역 소재" if kind == "국민연금" else "관할"))])
        if cs: nk += 1
        else:
            rows.append([lab, '<span style="color:#9CA3AF">이 지역 관할 정보 없음</span>', "-", "-"])
    # 소재하지만 관할이 아닌 기관(인근)
    extra = [a for a in loc if a["kind"] != "국민연금" and a not in cover]
    ex = ('<h2 class="group-title">📌 이 지역에 소재한 다른 기관</h2>' + table(["기관", "구분", "전화"], [[alink(a), KD[a["kind"]][0], esc(a["tel"] or "-")] for a in extra[:12]])) if extra else ""
    ext = []
    if k in MASTER_KEYS:
        ext = [("우체국", "https://wooapost.wooahouse.com/region/%s/%s/" % (sido, sg)), ("119안전센터·지구대", "https://wooasafe.wooahouse.com/region/%s/%s/" % (sido, sg))]
    sd = sido.replace("특별자치도", "").replace("특별시", "").replace("광역시", "").replace("특별자치시", "")
    path = rp(k)
    body = f"""
<div class="page-head"><h1>{esc(sido)} {esc(sg)} 관할 관공서 — 세무서·건강보험·국민연금·고용센터</h1><p>이 지역을 관할하는 {nk}종 기관</p></div>
<p class="lead"><b>{esc(sido)} {esc(sg)}</b>를 관할하는 세무서·건강보험공단·고용복지플러스센터·근로복지공단·지방병무청·보훈청 등을 한눈에 정리했습니다. 기관 이름을 누르면 주소·전화번호·관할구역을 볼 수 있습니다. 국민연금공단은 관할 정보가 없어 이 지역에 소재한 지사를 보여 드립니다.</p>
{ad()}
{table(['종류', '기관', '전화', '비고'], rows)}
{ex}
<p class="note">{NOTE}</p>
{chips([(sido, "/region/%s/" % sido), ("관할 관공서 찾는 법", "/guide/")] + ext)}
"""
    w = [a for a in cover if a["kind"] == "세무서" and a["sub"] != "지방국세청"]
    faq = [(f"{sg} 관할 세무서는 어디인가요?", (", ".join(a["name"] for a in w) + "입니다. 동에 따라 다른 세무서가 관할할 수 있으니 확인하세요.") if w else "공공데이터에서 확인되지 않았습니다."), (f"{sg} 건강보험공단 지사는?", (", ".join(a["name"] for a in cover if a["kind"] == "건강보험") or "공공데이터에서 확인되지 않았습니다.")), (f"{sg} 고용센터는?", (", ".join(a["name"] for a in cover if a["kind"] == "고용센터") or "공공데이터에서 확인되지 않았습니다."))]
    write(path, layout(path, f"{sido} {sg} 관할 세무서·건강보험·고용센터 — 우리 동네 관공서", f"{sido} {sg} 관할 세무서, 건강보험공단 지사, 고용복지플러스센터, 근로복지공단, 병무청, 보훈청. 전화번호와 관할구역.", body, faq, [("홈", "/"), ("지역별", "/region/"), (sido, "/region/%s/" % sido), (sg, path)]), "0.7")

def page_sido(sido):
    keys = [k for k in REGION_KEYS if k[0] == sido]; path = "/region/%s/" % sido
    rows = []
    for k in keys:
        cv = COVER.get(k, [])
        rows.append(['<a href="%s">%s</a>' % (rp(k), esc(k[1])), esc(", ".join(a["name"] for a in cv if a["kind"] == "세무서") or "-"), esc(", ".join(a["name"].replace("지사", "") for a in cv if a["kind"] == "건강보험") or "-")])
    body = f"""
<div class="page-head"><h1>{esc(sido)} 관할 관공서 — 시군구별 세무서·건강보험</h1><p>{len(keys)}개 시군구</p></div>
<p class="lead"><b>{esc(sido)}</b>의 시군구별 관할 세무서와 건강보험공단 지사입니다. 시군구를 누르면 고용센터·근로복지공단·병무청·보훈청까지 한 번에 볼 수 있습니다.</p>
{ad()}
{table(['시군구', '관할 세무서', '건강보험공단 지사'], rows)}
<p class="note">{NOTE}</p>
{chips([("지역별", "/region/"), ("관할 관공서 찾는 법", "/guide/")])}
"""
    faq = [(f"{sido} 관할 세무서는 어떻게 찾나요?", "시군구를 선택하면 관할 세무서가 표시됩니다. 일부 시군구는 동에 따라 관할 세무서가 나뉩니다.")]
    write(path, layout(path, f"{sido} 관할 세무서·건강보험공단 지사 — 시군구별 관공서", f"{sido} {len(keys)}개 시군구별 관할 세무서와 건강보험공단 지사 목록.", body, faq, [("홈", "/"), ("지역별", "/region/"), (sido, path)]), "0.8")

def hub_region():
    rows = [['<a href="/region/%s/">%s</a>' % (s, s), len([k for k in REGION_KEYS if k[0] == s])] for s in SIDOS]
    body = f"""
<div class="page-head"><h1>지역별 관할 관공서 — 우리 동네 세무서·건강보험·고용센터</h1><p>시도·시군구 {len(REGION_KEYS)}곳</p></div>
<p class="lead">시도와 시군구를 선택하면 해당 지역을 관할하는 <b>세무서, 건강보험공단 지사, 고용복지플러스센터, 근로복지공단, 지방병무청, 보훈청</b>을 한 번에 볼 수 있습니다. 관할 기관을 모를 때 가장 먼저 확인해 보세요.</p>
{ad()}
{table(['시도', '시군구 수'], rows, (1,))}
<p class="note">{NOTE}</p>
{chips([(KD[k][0], "/type/%s/" % k) for k, *_ in KINDS[:4]] + [("찾는 법", "/guide/")])}
"""
    faq = [("우리 동네 관할 세무서는 어떻게 찾나요?", "지역 목록에서 시도와 시군구를 선택하면 관할 세무서가 나옵니다."), ("관할 기관이 두 곳으로 나오면?", "동·면에 따라 관할이 나뉘는 경우입니다. 기관 페이지의 관할구역 문구를 확인하거나 전화로 문의하세요.")]
    write("/region/", layout("/region/", "지역별 관할 관공서 — 우리 동네 세무서·건강보험공단·고용센터", f"시도·시군구 {len(REGION_KEYS)}곳별 관할 세무서, 건강보험공단 지사, 고용복지플러스센터, 근로복지공단, 병무청, 보훈청.", body, faq, [("홈", "/"), ("지역별", "/region/")], coupang=True), "0.9")

# ───────────────────────── 종류 ─────────────────────────
def page_kind(kind):
    lab, org, desc = KD[kind]; lst = [a for a in BY_KIND[kind]]
    lst.sort(key=lambda a: (SIDO_ORDER.index(a["loc"][0]) if a["loc"] and a["loc"][0] in SIDO_ORDER else 99, a["name"]))
    rows = [[alink(a), esc(a["sub"]), esc(a["loc"][0] + " " + a["loc"][1]) if a["loc"] else "-", short_j(a, 50) or "-", esc(a["tel"] or "-")] for a in lst]
    path = "/type/%s/" % kind
    body = f"""
<div class="page-head"><h1>{lab} {len(lst)}곳 — 전국 전화번호·관할구역</h1><p>{org}</p></div>
<p class="lead">{desc} 전국 {lab} {len(lst)}곳의 전화번호와 관할구역을 정리했습니다. 이름을 누르면 주소와 관할 시군구를 볼 수 있습니다.</p>
{ad()}
{table(['기관', '구분', '소재지', '관할(요약)', '전화'], rows)}
<p class="note">{NOTE}</p>
{chips([("지역별 관공서", "/region/"), ("관할 관공서 찾는 법", "/guide/")] + [(KD[k][0], "/type/%s/" % k) for k, *_ in KINDS if k != kind][:5])}
"""
    faq = [(f"{lab}은(는) 어떤 일을 하나요?", desc), (f"전국에 {lab}은(는) 몇 곳인가요?", f"공공데이터 기준 {len(lst)}곳입니다.")]
    write(path, layout(path, f"{lab} {len(lst)}곳 — 전국 전화번호·관할구역 목록", f"전국 {lab} {len(lst)}곳의 전화번호·주소·관할구역. {desc[:60]}", body, faq, [("홈", "/"), (lab, path)]), "0.8")

# ───────────────────────── 안내 ─────────────────────────
GNOTE = "일반적인 안내이며 기관별 요구 서류와 절차는 다를 수 있으니 방문 전 확인하세요."
def guide(slug, title, h1, intro, steps, faq, desc):
    body = f"""
<div class="page-head"><h1>{h1}</h1><p>일반 안내</p></div>
<p class="lead">{intro}</p>
{ad()}
{''.join('<h2 class="group-title">%d. %s</h2><p class="lead">%s</p>' % (i + 1, t, d) for i, (t, d) in enumerate(steps))}
<p class="note">{GNOTE}</p>
{chips([("지역별 관공서", "/region/"), ("세무서", "/type/세무서/"), ("건강보험공단", "/type/건강보험/"), ("국민연금공단", "/type/국민연금/"), ("고용센터", "/type/고용센터/")])}
"""
    path = "/guide/%s/" % slug
    write(path, layout(path, title, desc, body, faq, [("홈", "/"), ("찾는 법", "/guide/"), (h1, path)]), "0.7")

def guides():
    guide("tax-office", "관할 세무서 찾는 법 — 주소로 확인하는 3가지 방법", "관할 세무서 찾는 법", "세금 신고나 사업자등록을 하려면 거주지·사업장 소재지의 관할 세무서를 알아야 합니다. 관할은 시군구와 동 단위로 정해집니다.",
          [("이 사이트에서 찾기", "지역별 목록에서 시도·시군구를 선택하면 관할 세무서가 표시됩니다. 동에 따라 관할이 나뉘는 곳은 기관 페이지의 관할구역 문구를 확인하세요."), ("국세청 홈택스에서 확인", "국세청 홈택스(hometax.go.kr)에서 관할 세무서를 조회할 수 있습니다."), ("전화로 확인", "국세 상담 전화 126으로 주소를 말씀드리면 관할 세무서를 안내받을 수 있습니다."), ("사업장과 거주지는 다를 수 있음", "사업자등록은 사업장 소재지 관할 세무서에서, 종합소득세 신고는 주소지 관할 세무서와 사업장 관할이 다를 수 있으니 안내를 확인하세요.")],
          [("관할 세무서는 어디서 정해지나요?", "납세지(주소지·사업장 소재지)에 따라 정해집니다."), ("세무서는 아무 곳이나 가도 되나요?", "신고·납부는 홈택스나 가까운 세무서의 민원실에서 가능한 경우가 많지만 사업자등록 등은 관할을 확인하세요.")], "관할 세무서를 이 사이트·홈택스·126 전화로 찾는 방법과 사업장·주소지 관할 차이를 정리했습니다.")
    guide("insurance", "건강보험·국민연금 지사 이용 안내 — 방문 전 확인할 것", "건강보험·국민연금 지사 이용 안내", "건강보험과 국민연금은 많은 업무를 전화·모바일·인터넷으로 처리할 수 있어 지사 방문 전 먼저 확인하면 시간을 줄일 수 있습니다.",
          [("업무 가능 여부 확인", "자격 확인, 보험료 조회, 증명서 발급 등은 온라인(홈페이지·앱)에서 가능한 경우가 많습니다."), ("대표 전화", "국민건강보험공단 대표 전화는 1577-1000, 국민연금 상담 전화는 1355입니다."), ("신분증 지참", "방문 시에는 신분증을 가져가고 대리 방문이면 위임장과 대리인 신분증이 필요합니다."), ("관할 지사 확인", "건강보험은 거주지 관할 지사가 정해져 있으며 이 사이트에서 시군구별로 확인할 수 있습니다.")],
          [("건강보험 지사는 아무 곳이나 가도 되나요?", "대부분의 민원은 가까운 지사에서도 처리되지만 일부 업무는 관할 지사에서만 가능할 수 있으니 확인하세요."), ("국민연금 지사의 관할은?", "공공데이터에 지사별 관할구역이 없어 이 사이트는 소재지 기준으로 안내합니다.")], "건강보험·국민연금 지사 방문 전 확인 사항과 대표 전화, 준비물을 정리한 안내.")
    guide("employment", "고용센터·근로복지공단 이용 안내 — 실업급여·산재 문의", "고용센터·근로복지공단 이용 안내", "실업급여, 구직 상담은 고용복지플러스센터에서, 산재보험 접수·상담은 근로복지공단 지사에서 처리하는 것이 일반적입니다.",
          [("실업급여", "실업급여(구직급여)는 거주지 관할 고용센터에서 수급자격 신청을 합니다. 고용노동부 상담 전화는 1350입니다."), ("산재보험", "산재 요양급여 신청과 상담은 근로복지공단 지사에서 접수합니다."), ("임금체불", "임금체불 진정은 관할 고용노동청·지청에 접수합니다."), ("관할 확인", "고용센터·근로복지공단·노동청의 관할은 이 사이트의 시군구별 목록에서 확인할 수 있습니다.")],
          [("실업급여는 어디에 신청하나요?", "거주지 관할 고용복지플러스센터에 신청합니다."), ("임금체불은 어디에 신고하나요?", "관할 지방고용노동청 또는 지청에 진정하거나 고용노동부 1350으로 상담합니다.")], "실업급여·산재·임금체불 문의 기관(고용센터·근로복지공단·노동청)과 관할 확인 방법.")
    body = f"""
<div class="page-head"><h1>관할 관공서 찾는 법 — 세무서·건강보험·고용센터 안내</h1><p>방문 전 확인 가이드</p></div>
<p class="lead">관공서는 주소에 따라 관할이 정해져 있습니다. 관할 기관을 찾는 방법과 방문 전 확인 사항을 정리했습니다.</p>
{ad()}
{chips([("관할 세무서 찾는 법", "/guide/tax-office/"), ("건강보험·국민연금 지사", "/guide/insurance/"), ("고용센터·근로복지공단", "/guide/employment/"), ("지역별 관공서", "/region/")])}
<p class="note">{GNOTE}</p>
"""
    write("/guide/", layout("/guide/", "관할 관공서 찾는 법 — 세무서·건강보험·고용센터 안내", "관할 세무서, 건강보험·국민연금 지사, 고용센터·근로복지공단 이용 방법을 정리한 안내.", body, None, [("홈", "/"), ("찾는 법", "/guide/")]), "0.7")

def page_home():
    body = f"""
<div class="hero"><h1>🏛️ 우리 동네 관할 관공서 — 세무서·건강보험·국민연금·고용센터</h1><p>시군구를 고르면 관할 기관과 전화번호가 한눈에 나옵니다.</p></div>
{ad()}
<div class="card-grid">
<a class="card" href="/region/"><b>📍 지역별</b><span>시군구 {len(REGION_KEYS)}곳 관할 관공서</span></a>
<a class="card" href="/type/세무서/"><b>🧾 세무서</b><span>{len(BY_KIND['세무서'])}곳 · 관할구역</span></a>
<a class="card" href="/type/건강보험/"><b>🏥 건강보험공단</b><span>{len(BY_KIND['건강보험'])}곳 지사</span></a>
<a class="card" href="/type/국민연금/"><b>👵 국민연금공단</b><span>{len(BY_KIND['국민연금'])}곳 지사·센터</span></a>
<a class="card" href="/type/고용센터/"><b>💼 고용복지플러스센터</b><span>{len(BY_KIND['고용센터'])}곳</span></a>
<a class="card" href="/type/근로복지공단/"><b>🦺 근로복지공단</b><span>산재·퇴직연금</span></a>
<a class="card" href="/type/노동청/"><b>⚖️ 고용노동청·지청</b><span>임금체불·근로감독</span></a>
<a class="card" href="/guide/"><b>📖 찾는 법</b><span>관할 확인 가이드</span></a>
</div>
<p class="lead">우아민원은 세무서(국세청), 건강보험공단, 국민연금공단, 고용복지플러스센터, 근로복지공단, 고용노동청, 병무청, 보훈청, 출입국관서의 공공데이터 {len(A)}건을 시군구별 관할로 묶어 보여 드립니다. 관할구역이 동 단위로 나뉘는 곳은 표시하며 방문 전 기관에 확인이 필요합니다. 자세한 기준은 <a href="/about/">데이터 설명</a>을 참고하세요.</p>
"""
    faq = [("관할 관공서는 어떻게 찾나요?", "지역별에서 시도·시군구를 선택하면 관할 세무서·건강보험공단 지사·고용센터 등이 표시됩니다."), ("정보는 어디서 가져오나요?", "국세청, 국민건강보험공단, 국민연금공단, 고용노동부, 근로복지공단, 병무청, 국가보훈부, 법무부가 공공데이터포털에 공개한 기관 현황을 사용합니다.")]
    write("/", layout("/", "우아민원 — 우리 동네 관할 세무서·건강보험공단·국민연금·고용센터 찾기", f"시군구별 관할 세무서, 건강보험공단·국민연금공단 지사, 고용복지플러스센터, 근로복지공단, 병무청, 보훈청의 전화번호와 관할구역 {len(A)}곳.", body, faq), "1.0")

def page_about():
    body = f"""
<div class="page-head"><h1>데이터 설명</h1><p>정보의 출처와 한계</p></div>
<h2 class="group-title">📚 출처(공공데이터포털)</h2><p class="lead">국세청 세무서별 관할구역(15099881), 국민연금공단 지사 및 상담센터 현황(15010814), 국민건강보험공단 본부 및 지사 현황(15142232), 고용노동부 고용복지플러스센터 현황(15066368), 법무부 출입국관리사무소 현황(15040715), 근로복지공단 본부 및 지사 현황(15049970), 병무청 지방병무청 병역판정검사장 위치 및 관할지역(15062525), 고용노동부 지방노동청(15029545), 국가보훈부 지방청과 지청 관할 지역 정보(15113992)를 사용했습니다. 총 {len(A)}건입니다.</p>
<h2 class="group-title">🧭 관할 해석 방법</h2><p class="lead">관할구역 문구에서 시군구 이름을 읽어 지역별 페이지에 연결했습니다. 문구에 동·읍·면 단위 제외나 일부 관할이 있는 경우 ‘일부 지역’으로 표시했습니다. 국민연금공단은 지사별 관할 정보가 없어 지사 소재지 기준으로만 연결했고 건강보험공단 일부 출장소는 이름에서 관할 시군을 추정했습니다. 2026년 행정구역 개편(광주·전남 통합, 인천 일부 구 개편 등)으로 데이터마다 구 이름이 다를 수 있습니다.</p>
<h2 class="group-title">⚠️ 한계</h2><p class="lead">{NOTE} 이 사이트는 민원 접수나 기관 연결을 대행하지 않습니다.</p>
<h2 class="group-title">📬 문의·정정</h2><p class="lead">오류 제보는 <a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a> 으로 보내 주세요.</p>
"""
    write("/about/", layout("/about/", "데이터 설명 — 출처와 관할 해석 방법", "우아민원 데이터 출처(국세청·건강보험·국민연금·고용노동부 등 공공데이터)와 관할구역 해석 방법, 한계.", body, None, [("홈", "/"), ("데이터 설명", "/about/")]), "0.5")

def page_privacy():
    body = """
<div class="page-head"><h1>개인정보처리방침</h1></div>
<p class="lead">우아민원(wooaminwon.wooahouse.com, 이하 “서비스”)은 회원가입·로그인을 요구하지 않으며 이용자의 개인정보를 직접 수집하지 않습니다.</p>
<h3>자동 수집 정보</h3><p class="lead">서비스 개선을 위해 Google Analytics로 방문자 수·페이지뷰 등 익명 통계를 수집하며, Google AdSense와 쿠팡 파트너스는 맞춤 광고를 위해 쿠키를 사용할 수 있습니다. 쿠키는 브라우저 설정에서 비활성화할 수 있습니다. (<a href="https://policies.google.com/privacy">Google 개인정보처리방침</a>, <a href="https://policies.google.com/technologies/ads">Google 광고 정책</a>)</p>
<h3>쿠팡 파트너스</h3><p class="lead">일부 페이지에는 쿠팡 파트너스 활동의 일환으로 광고가 포함되어 있으며 이에 따른 수수료를 제공받을 수 있습니다.</p>
<h3>문의</h3><p class="lead"><a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a></p>
<p class="note">최종 수정일: 2026년 10월 24일</p>
"""
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아민원 개인정보처리방침", body, None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)

def make_og():
    f = ROOT / "assets" / "og-image.png"
    if f.exists(): return
    try: from PIL import Image, ImageDraw, ImageFont
    except Exception: return
    im = Image.new("RGB", (1200, 630), (30, 64, 175)); dr = ImageDraw.Draw(im)
    def font(sz):
        for n in ("malgunbd.ttf", "malgun.ttf", "NanumGothicBold.ttf"):
            try: return ImageFont.truetype(n, sz)
            except Exception: pass
        return ImageFont.load_default()
    dr.rounded_rectangle((90, 90, 1110, 540), 40, fill=(255, 255, 255))
    dr.text((150, 150), "우아민원", font=font(110), fill=(30, 58, 138))
    dr.text((150, 300), "우리 동네 관할 관공서", font=font(54), fill=(31, 41, 55))
    dr.text((150, 380), "세무서 · 건강보험 · 국민연금 · 고용센터", font=font(46), fill=(31, 41, 55))
    dr.text((150, 470), "wooaminwon.wooahouse.com", font=font(34), fill=(107, 114, 128))
    im.save(f)

def main():
    t0 = time.time(); make_og()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    for nf in ROOT.glob("naver*.html"): shutil.copy(nf, OUT / nf.name)
    for a in A: page_agency(a)
    for k in REGION_KEYS: page_region(k)
    for s in SIDOS: page_sido(s)
    hub_region()
    for kind, *_ in KINDS: page_kind(kind)
    guides(); page_home(); page_about(); page_privacy()
    today = time.strftime("%Y-%m-%d")
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), today, pr) for p, pr in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooaminwon.wooahouse.com\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈</a><a class="chip" href="/region/">지역별 관공서</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("pages", len(WRITTEN), "elapsed", round(time.time() - t0), "s")

if __name__ == "__main__":
    main()
