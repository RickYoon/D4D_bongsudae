"""Google 뉴스 RSS 일별 기사 수 수집 (직렬, 2초 간격).
사용: python3 collect.py <시작 YYYY-MM-DD> <끝> <출력.csv> 키워드...
주의: RSS는 한 요청당 최대 약 100건만 돌려준다 → 100에 닿은 날은 '하한값'으로 표시.
"""
import csv, datetime as dt, subprocess, sys, time, re, os

def fetch(q):
    out = subprocess.run(["curl", "-s", "--max-time", "25", "-A", "Mozilla/5.0", "-G",
        "https://news.google.com/rss/search", "--data-urlencode", f"q={q}",
        "--data-urlencode", "hl=ko", "--data-urlencode", "gl=KR", "--data-urlencode", "ceid=KR:ko"],
        capture_output=True, text=True).stdout
    if "<rss" not in out:
        return None, []
    titles = re.findall(r"<item><title>(.*?)</title>.*?<pubDate>(.*?)</pubDate>", out, re.S)
    return len(titles), titles

start, end, outp, kws = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
done = set()
if os.path.exists(outp):
    done = {(r["date"], r["kw"]) for r in csv.DictReader(open(outp))}
f = open(outp, "a", newline="")
w = csv.writer(f)
if not done:
    w.writerow(["date", "kw", "n", "capped", "sample_titles"])
d = d0
while d <= d1:
    for k in kws:
        if (d.isoformat(), k) in done:
            continue
        n, t = fetch(f'"{k}" after:{d} before:{d + dt.timedelta(days=1)}')
        if n is None:
            print("FAIL", d, k, file=sys.stderr); time.sleep(10); continue
        w.writerow([d.isoformat(), k, n, int(n >= 95), " || ".join(x[0] for x in t)])
        f.flush()
        time.sleep(2)
    d += dt.timedelta(days=1)
