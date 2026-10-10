"""GDELT 1.0 일별 사건 파일 → 북한(Actor1CountryCode=PRK) 일별 집계. 원본 저장 안 함(받아서 바로 거름). 직렬.
출력: nkdb/gdelt_daily.csv  date,total,r13_threat,r15_force,r17_coerce,r18_assault,r19_fight,r20_mass,threat_to_kor_usa_jpn,mentions,goldstein_sum
"""
import subprocess, csv, os, datetime as dt, io, zipfile, sys, time
OUT = "nkdb/gdelt_daily.csv"
done = set()
if os.path.exists(OUT):
    done = {r["date"] for r in csv.DictReader(open(OUT))}
f = open(OUT, "a", newline=""); w = csv.writer(f)
if not done: w.writerow(["date", "total", "r13_threat", "r15_force", "r17_coerce", "r18_assault", "r19_fight", "r20_mass", "threat_to_kor_usa_jpn", "mentions", "goldstein_sum"])
d = dt.date(2015, 10, 1); end = dt.date(2026, 10, 9)
while d <= end:
    k = d.strftime("%Y%m%d")
    if str(d) in done: d += dt.timedelta(1); continue
    raw = subprocess.run(["curl", "-s", "--max-time", "90", f"https://data.gdeltproject.org/events/{k}.export.CSV.zip"], capture_output=True).stdout
    try:
        z = zipfile.ZipFile(io.BytesIO(raw)); data = z.read(z.namelist()[0]).decode("utf-8", "ignore")
    except Exception:
        print("miss", d, len(raw), flush=True); d += dt.timedelta(1); time.sleep(1); continue
    c = dict(total=0, r13=0, r15=0, r17=0, r18=0, r19=0, r20=0, tgt=0, men=0, gold=0.0)
    for line in data.split("\n"):
        p = line.split("\t")
        if len(p) < 35 or p[7] != "PRK": continue
        c["total"] += 1; root = p[28]
        if root in ("13", "15", "17", "18", "19", "20"): c["r" + root] += 1
        if root == "13" and p[17] in ("KOR", "USA", "JPN"): c["tgt"] += 1
        try: c["men"] += int(p[31]); c["gold"] += float(p[30])
        except Exception: pass
    w.writerow([str(d), c["total"], c["r13"], c["r15"], c["r17"], c["r18"], c["r19"], c["r20"], c["tgt"], c["men"], round(c["gold"], 1)]); f.flush()
    if d.day == 1: print(d, c["total"], c["r13"], flush=True)
    d += dt.timedelta(1)
print("DONE", flush=True)
