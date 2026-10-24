# -*- coding: utf-8 -*-
"""공공기관 현황 CSV 9종 → data/agencies.json (관할 시군구 파싱 포함). 사용: python scripts/build_data.py <원본폴더> <master posts.json>
원본(공공데이터포털): taxoffice 15099881, nps 15010814, nhis 15142232, job 15066368, immi 15040715, comwel 15049970, mma 15062525, labor 15029545, bohun 15113992"""
import sys, csv, io, re, json, pathlib, collections
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1]); MASTER = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))

CANON = {"서울": "서울특별시", "서울시": "서울특별시", "서울특별시": "서울특별시", "부산": "부산광역시", "부산광역시": "부산광역시", "대구": "대구광역시", "대구광역시": "대구광역시", "인천": "인천광역시", "인천광역시": "인천광역시",
         "광주": "전남광주통합특별시", "광주광역시": "전남광주통합특별시", "전남": "전남광주통합특별시", "전라남도": "전남광주통합특별시", "전남광주통합특별시": "전남광주통합특별시", "전남광주특별시": "전남광주통합특별시",
         "대전": "대전광역시", "대전광역시": "대전광역시", "울산": "울산광역시", "울산광역시": "울산광역시", "세종": "세종특별자치시", "세종특별자치시": "세종특별자치시", "경기": "경기도", "경기도": "경기도",
         "강원": "강원특별자치도", "강원도": "강원특별자치도", "강원특별자치도": "강원특별자치도", "충북": "충청북도", "충청북도": "충청북도", "충남": "충청남도", "충청남도": "충청남도",
         "전북": "전북특별자치도", "전라북도": "전북특별자치도", "전북특별자치도": "전북특별자치도", "경북": "경상북도", "경상북도": "경상북도", "경남": "경상남도", "경상남도": "경상남도",
         "제주": "제주특별자치도", "제주도": "제주특별자치도", "제주특별자치도": "제주특별자치도"}
METRO = {"서울특별시", "부산광역시", "대구광역시", "인천광역시", "대전광역시", "울산광역시", "전남광주통합특별시", "세종특별자치시"}
SIDO_RE = "|".join(sorted(CANON, key=lambda x: -len(x)))
SIDO_TOK = "(?:%s)(?![가-힣])" % SIDO_RE
UNIV = collections.defaultdict(set)   # sido -> sg set
for m in MASTER: UNIV[CANON.get(m["sido"], m["sido"])].add(m["sg"])
UNIV["세종특별자치시"].add("세종시")
STEM = {s: {(sg[:-1] if sg[-1] in "시군구" and len(sg) > 2 else sg): sg for sg in sgs} for s, sgs in UNIV.items()}

LEGACY = set()
LEGACY_OK = {('인천광역시', '서구'), ('인천광역시', '동구')}

def read(fn):
    b = (SRC / (fn + ".bin")).read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try: t = b.decode(enc); break
        except Exception: pass
    return [{k.strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(t))]

SG2SIDO = collections.defaultdict(set)
for _s, _sgs in UNIV.items():
    for _g in _sgs: SG2SIDO[_g].add(_s)

def loc_key(addr):
    """주소에서 (sido, sg)"""
    a = re.sub(r"^(\([^)]*\)\s*)+", "", (addr or "").strip()); p = a.split()
    if not p: return None
    sido = CANON.get(p[0])
    if not sido:
        if re.search(r"[시군구]$", p[0]) and len(SG2SIDO.get(p[0], ())) == 1: return (next(iter(SG2SIDO[p[0]])), p[0])
        return None
    if sido == "세종특별자치시": return (sido, "세종시")
    if len(p) > 1 and re.search(r"[시군구]$", p[1]): return (sido, p[1])
    return None

def juris(text, default=None, stem_mode=False):
    """관할 문자열 → ([(sido, sg)], partial)"""
    t = (text or "").strip()
    if not t or t == "0": return [], False
    partial = bool(re.search(r"제외|일부|중 |[가-힣0-9]+동[ ,]|[가-힣]+(?:면|읍)", t))
    whole = bool(re.search(r"전체|전역", t)) and not re.search(r"[가-힣]+[시군구](?![가-힣])", re.sub(r"서울특별시|부산광역시|대구광역시|인천광역시|대전광역시|울산광역시|세종특별자치시|특별자치도|광역시|특별시", "", t))
    t2 = re.sub(r"\([^)]*\)", " ", t)
    if not re.search(r"[가-힣]+[시군구](?![가-힣])", re.sub(SIDO_TOK, "", t2)) and not re.fullmatch(r"\s*(?:%s)(?:\s*[,ㆍ]\s*(?:%s))*\s*" % (SIDO_TOK, SIDO_TOK), t2): t2 = re.sub(r"[()]", " ", t)
    if stem_mode: t2 = re.sub(r"[()/]", " ", t)
    # '<시도> 전지역/전체' 확장
    pre = []
    for m in re.finditer(r"(%s)\s*(?:전지역|전역|전체)" % SIDO_TOK, t2):
        sd = CANON[m.group(1)]; pre += [(sd, sg) for sg in sorted(UNIV[sd])]
    t2 = re.sub(r"(%s)\s*(?:전지역|전역|전체)" % SIDO_TOK, " ", t2)
    out, seen = list(dict.fromkeys(pre)), set(pre); cur = default; city = None
    if stem_mode: pat = r"(%s)|()([가-힣]{2,5})" % SIDO_TOK
    else: pat = r"(%s)|([가-힣0-9]+?(?:시|군|구))(?![가-힣])|()" % SIDO_TOK
    for sd, suf, bare in re.findall(pat, t2):
        if sd:
            cur = CANON[sd]; city = None
            if stem_mode and cur in METRO and not re.search(r"%s\s*\(" % re.escape(sd), t):
                for sg in sorted(UNIV[cur]):
                    if (cur, sg) not in seen: seen.add((cur, sg)); out.append((cur, sg))
            continue
        if not cur: continue
        if suf:
            if suf.endswith("구") and cur not in METRO:       # 도 아래 구는 상위 시에 포함
                continue
            if cur == "세종특별자치시": key = (cur, "세종시")
            elif suf in UNIV[cur]: key = (cur, suf)
            elif suf[:-1] in STEM.get(cur, {}): key = (cur, STEM[cur][suf[:-1]])
            elif (cur, suf) in LEGACY_OK:
                key = (cur, suf); LEGACY.add(key)       # 개편 전 행정구역명 등 마스터에 없는 이름
            else: continue
            if key not in seen: seen.add(key); out.append(key)
        elif bare:
            b2 = bare[:-1] if bare[-1] in "시군구" and len(bare) > 2 else bare
            sg = STEM.get(cur, {}).get(b2)
            k = (cur, sg) if sg else None
            if not k:
                cands = [(sd2, st[b2]) for sd2, st in STEM.items() if b2 in st]
                if len(cands) == 1: k = cands[0]
            if k and k not in seen: seen.add(k); out.append(k)
    if not out and default and re.fullmatch(r"\s*(?:%s)(?:\s*[,ㆍ]\s*(?:%s))*\s*" % (SIDO_RE, SIDO_RE), t2):
        whole = True
        out_s = [CANON[x] for x in re.findall(SIDO_RE, t2)]
        return [(sd, sg) for sd in dict.fromkeys(out_s) for sg in sorted(UNIV[sd])], partial
    if whole and default and not out:
        out = [(default, sg) for sg in sorted(UNIV[default])]
    return out, partial

def from_name(name, sido):
    """'달성고령지사(고령출장소)' 같은 이름에서 시군 이름을 분해(관할구역 데이터가 없는 건강보험 지사용)"""
    stem = re.sub(r"\(.*?\)|지사|출장소|지역본부", "", name)
    keys = STEM.get(sido, {}); out = []; i = 0
    while i < len(stem):
        for L in range(min(4, len(stem) - i), 1, -1):
            if stem[i:i + L] in keys: out.append((sido, keys[stem[i:i + L]])); i += L; break
        else: i += 1
    ext = re.findall(r"\(([가-힣]+)출장소\)", name)
    for e in ext:
        if e in keys and (sido, keys[e]) not in out: out.append((sido, keys[e]))
    return out

def mk(kind, name, **kw): return dict(kind=kind, name=name, **kw)

def main():
    A = []
    for r in read("taxoffice"):
        lk = loc_key(r["도로명 주소"]); cov, part = juris(r["관할구역"], lk[0] if lk else None)
        if "지방국세청" in r["세무서명"]:
            sidos = list(dict.fromkeys(CANON[m] for m in re.findall(SIDO_RE, r["관할구역"])))
            if not sidos and lk: sidos = [lk[0]]
            cov = [(s, sg) for s in sidos for sg in sorted(UNIV[s])]; part = False
        A.append(mk("세무서", r["세무서명"], addr=r["도로명 주소"], zip=r["우편번호"], tel=r["전화번호"], fax=r["팩스번호"], juris=r["관할구역"], cov=cov, partial=part, sub="지방국세청" if "지방국세청" in r["세무서명"] else "세무서", loc=lk))
    for r in read("nps"):
        A.append(mk("국민연금", r["지사(센터)명"], addr=r["주소"], zip=r["우편번호"].zfill(5), tel=r["전화번호"], fax=r["FAX"], juris="", cov=[], partial=False, sub="센터" if "센터" in r["지사(센터)명"] else "지사", loc=loc_key(r["주소"])))
    for r in read("nhis"):
        nm = r["기관명"].replace("국민건강보험공단 ", "")
        lk = loc_key(r["주소"]); cov, part = juris(r["지사 관할구역"], lk[0] if lk else None)
        if not cov and lk and "지역본부" not in nm and nm != "본부":
            cov = from_name(nm, lk[0]); part = True
        A.append(mk("건강보험", nm, addr=r["주소"], zip=r["우편번호"], tel=r["전화번호"], fax="", juris="" if r["지사 관할구역"] == "0" else re.sub(r"\s+", " ", r["지사 관할구역"]), cov=cov, partial=part, sub="출장소" if "출장소" in nm else ("본부" if "본부" in nm else "지사"), loc=lk))
    for r in read("job"):
        lk = loc_key(r["소재지"]); cov, part = juris(r["관할구역"], lk[0] if lk else None)
        A.append(mk("고용센터", r["센터명"], addr=r["소재지"], zip="", tel=r["대표전화"], fax="", juris=r["관할구역"], cov=cov, partial=part, sub=r["청(지청)"], loc=lk))
    for r in read("comwel"):
        if not r["주소"]: continue
        lk = loc_key(r["주소"]); cov, part = juris(r["관할구역"], lk[0] if lk else None)
        A.append(mk("근로복지공단", r["기관(지사)명"], addr=r["주소"], zip=r["우편번호"], tel=r["대표 전화번호"], fax=r["대표 전자팩스"], juris=r["관할구역"], cov=cov, partial=part, sub="병원" if "병원" in r["기관(지사)명"] else ("본부" if "본부" in r["기관(지사)명"] else "지사"), hours=r["이용시간"], loc=lk))
    for r in read("labor"):
        sd = CANON.get(r["위치"].split()[0]) if r["위치"] else None
        cov, part = juris(r["관할구역"], sd)
        A.append(mk("노동청", r["명칭"], addr=r["위치"], zip="", tel="", fax="", juris=r["관할구역"], cov=cov, partial=part, sub=r["명칭구분"], loc=None))
    for r in read("bohun"):
        sd = CANON.get(r["지역"]); cov, part = juris(r["관할지역"], sd, stem_mode=True)
        A.append(mk("보훈", r["기관명"], addr=r["주소"], zip="", tel=r["전화번호"], fax="", juris=r["관할지역"], cov=cov, partial=part, sub=r["기관형태"], home=r["홈페이지 주소"], loc=loc_key(r["주소"])))
    for r in read("mma"):
        lk = loc_key(r["병역판정검사장 위치"]); cov, part = juris(r["해당 시군구"], lk[0] if lk else None, stem_mode=True)
        A.append(mk("병무청", r["지방병무(지)청"], addr=r["병역판정검사장 위치"], zip="", tel="", fax="", juris=r["해당 시군구"].strip(), cov=cov, partial=part, sub="병역판정검사장", loc=lk))
    for r in read("immi"):
        lk = loc_key(r["주소"]); cov, part = juris(r["관할구역"], lk[0] if lk else None)
        A.append(mk("출입국", r["기관명"], addr=r["주소"], zip="", tel=r["전화"], fax="", juris=r["관할구역"], cov=cov, partial=part, sub=r["지역"], loc=lk))
    for a in A:
        a["cov"] = [list(c) for c in a["cov"]]; a["loc"] = list(a["loc"]) if a["loc"] else None
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "agencies.json").write_text(json.dumps(A, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("개편 전/마스터 외 지명", sorted(LEGACY))
    byk = collections.Counter(a["kind"] for a in A); nocov = [a for a in A if not a["cov"] and a["kind"] != "국민연금"]
    print(len(A), dict(byk), "관할 미해석", len(nocov))
    for a in nocov[:30]: print("  -", a["kind"], a["name"], "|", a["juris"][:70])
    sg_cov = collections.Counter(tuple(c) for a in A for c in a["cov"]); print("커버 시군구", len(sg_cov), "마스터", sum(len(v) for v in UNIV.values()))

if __name__ == "__main__":
    main()
