"""월별 기사 수 (직렬, 2초). 100건 상한에 닿은 달은 주 단위로 다시 나눠 센다.
사용: python3 collect_month.py <YYYY-MM 시작> <YYYY-MM 끝> <out.csv> 키워드...
"""
import csv, datetime as dt, subprocess, re, sys, time

def n(q):
    o = subprocess.run(["curl", "-s", "--max-time", "25", "-A", "Mozilla/5.0", "-G", "https://news.google.com/rss/search",
        "--data-urlencode", f"q={q}", "--data-urlencode", "hl=ko", "--data-urlencode", "gl=KR", "--data-urlencode", "ceid=KR:ko"],
        capture_output=True, text=True).stdout
    time.sleep(2)
    return len(re.findall(r"<item>", o)) if "<rss" in o else None

def count(k, a, b):
    c = n(f'"{k}" after:{a} before:{b}')
    if c is None or c < 95 or (b - a).days <= 7:
        return c, int(c is not None and c >= 95)
    tot, cap, d = 0, 0, a
    while d < b:
        e = min(d + dt.timedelta(days=7), b)
        x, y = count(k, d, e); tot += x or 0; cap |= y; d = e
    return tot, cap

y0, m0 = map(int, sys.argv[1].split("-")); y1, m1 = map(int, sys.argv[2].split("-"))
w = csv.writer(open(sys.argv[3], "w", newline="")); w.writerow(["month", "kw", "n", "capped"])
y, m = y0, m0
while (y, m) <= (y1, m1):
    a = dt.date(y, m, 1); b = dt.date(y + (m == 12), m % 12 + 1, 1)
    for k in sys.argv[4:]:
        c, cap = count(k, a, b); w.writerow([f"{y}-{m:02d}", k, c, cap]); print(y, m, k, c, cap, flush=True)
    y, m = y + (m == 12), m % 12 + 1
