"""Rewrite the 「최신 영상」 block of README.md from the channel's public YouTube feed (no API key, no login).

Runs daily in GitHub Actions (.github/workflows/latest-videos.yml). Only public videos are in the feed,
so scheduled/private ones never show. Keeps videos whose title has 「AI 비공식 리마스터」 (어쩐지 저녁 영상).
usage: python update_videos.py [README.md]   -> exit 0, file changed only when the list changed
"""
import re, sys, urllib.request
from xml.etree import ElementTree as ET

CHANNEL = "UCsccQogob4VEzw6-lbLhcig"  # 유튜브 고전리마스터
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}"
KEEP = "AI 비공식 리마스터"
LONG_MAX, SHORT_MAX = 4, 3
START, END = "<!-- LATEST_VIDEOS_START -->", "<!-- LATEST_VIDEOS_END -->"
TOP_START, TOP_END = "<!-- TOP_VIDEO_START -->", "<!-- TOP_VIDEO_END -->"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def is_short(vid):
    """/shorts/<id> answers 200 for a Short and redirects (303) for a normal video."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        r = urllib.request.build_opener(NoRedirect).open(
            urllib.request.Request(f"https://www.youtube.com/shorts/{vid}", method="HEAD", headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
        return r.status == 200
    except Exception:
        return False


def main(path="README.md"):
    root = ET.fromstring(urllib.request.urlopen(FEED, timeout=30).read())
    longs, shorts = [], []
    for e in root.findall("a:entry", NS):
        title = e.find("a:title", NS).text or ""
        if KEEP not in title:
            continue
        vid = e.find("yt:videoId", NS).text
        day = e.find("a:published", NS).text[:10]
        (shorts if is_short(vid) else longs).append((day, vid, title))
    lines = [START, "", "### 최신 개발 영상 (매일 자동 갱신)", ""]
    lines += [f"- {d} [{t}](https://www.youtube.com/watch?v={v})" for d, v, t in longs[:LONG_MAX]]
    if shorts:
        lines += ["", "쇼츠: " + " · ".join(f"[{t.split(',')[0].split('(')[0].strip()}](https://www.youtube.com/shorts/{v})" for d, v, t in shorts[:SHORT_MAX])]
    lines += ["", "전체 영상: [유튜브 고전리마스터](https://www.youtube.com/channel/" + CHANNEL + ")", "", END]
    block = "\n".join(lines)
    text = open(path, encoding="utf-8").read()
    if START in text and END in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        new = text.rstrip() + "\n\n" + block + "\n"
    # top of README: the newest long video, big thumbnail (night 11-19)
    if longs and TOP_START in new and TOP_END in new:
        d, v, t = longs[0]
        top = "\n".join([TOP_START,
                         f"[![{t}](https://i.ytimg.com/vi/{v}/hqdefault.jpg)](https://www.youtube.com/watch?v={v})",
                         "",
                         f"▶ **최신 개발 영상 ({d})**: [{t}](https://www.youtube.com/watch?v={v})",
                         TOP_END])
        new = re.sub(re.escape(TOP_START) + r".*?" + re.escape(TOP_END), lambda _: top, new, flags=re.S)
    if new != text:
        open(path, "w", encoding="utf-8").write(new)
        print("README updated:", len(longs[:LONG_MAX]), "long,", len(shorts[:SHORT_MAX]), "shorts")
    else:
        print("no change")


if __name__ == "__main__":
    main(*sys.argv[1:])
