import gzip
import gzip
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import requests

CHANNELS = {
    "SIDHARTH.GOLD.in": {
        "name": "SIDHARTH GOLD",
        "url": "https://www.epgschedule.com/channel/sidharth-gold/",
    },
    "SIDHARTH.UTSAV.in": {
        "name": "SIDHARTH UTSAV",
        "url": "https://www.epgschedule.com/channel/sidharth-utsav/",
    },
    "sony.max.1": {
        "name": "SONY MAX 1",
        "url": "https://www.epgschedule.com/channel/sony-max-1/",
    },
    "sony.max.2": {
        "name": "SONY MAX 2",
        "url": "https://www.epgschedule.com/channel/sony-max-2/",
    },
    "SONY.MAX.HD.in": {
        "name": "SONY MAX HD",
        "url": "https://www.epgschedule.com/channel/sony-max-hd/",
    },
    "sony.max": {
        "name": "SONY MAX",
        "url": "https://www.epgschedule.com/channel/sony-max/",
    },
    "SONY.PAL.in": {
        "name": "SONY PAL",
        "url": "https://www.epgschedule.com/channel/sony-pal/",
    },
    "SONY.PIX.HD": {
        "name": "SONY PIX HD",
        "url": "https://www.epgschedule.com/channel/sony-pix-hd/",
    },
    "SONY.PIX.in": {
        "name": "SONY PIX",
        "url": "https://www.epgschedule.com/channel/sony-pix/",
    },
    "SONY.VIZHA.HD.in": {
        "name": "SONY VIZHA HD",
        "url": "https://www.epgschedule.com/channel/sony-vizha-hd/",
    },
    "SONY.VIZHA.in": {
        "name": "SONY VIZHA",
        "url": "https://www.epgschedule.com/channel/sony-vizha/",
    },
    "SONY.WAH.in": {
        "name": "SONY WAH",
        "url": "https://www.epgschedule.com/channel/sony-wah/",
    },
    "STAR.GOLD.SELECT.in": {
        "name": "STAR GOLD SELECT",
        "url": "https://www.epgschedule.com/channel/star-gold-select/",
    },
    "STAR.PRAVAH.PICTURES.HD.in": {
        "name": "STAR PRAVAH PICTURES HD",
        "url": "https://www.epgschedule.com/channel/star-pravah-pictures-hd/",
    },
    "STAR.UTSAV.MOVIES.in": {
        "name": "STAR UTSAV MOVIES",
        "url": "https://www.epgschedule.com/channel/star-utsav-movies/",
    },
    "ZEE.KANNADA.NEWS.in": {
        "name": "ZEE KANNADA NEWS",
        "url": "https://www.epgschedule.com/channel/zee-kannada-news/",
    },
    "ZEE.ZEST.HD.in": {
        "name": "ZEE ZEST HD",
        "url": "https://www.epgschedule.com/channel/zee-zest-hd/",
    },
}

IST = timezone(timedelta(hours=5, minutes=30))
TIME_PATTERN = re.compile(r"^(\d{1,2}:\d{2}\s*[AP]M)\s*[–-]\s*(\d{1,2}:\d{2}\s*[AP]M)$", re.I)


def parse_schedule(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=25)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    lines = [line.strip() for line in soup.stripped_strings if line.strip()]

    # "Today's Schedule" ke baad se shuru karein
    start_idx = 0
    for i, line in enumerate(lines):
        if "Today's Schedule" in line:
            start_idx = i + 1
            break

    # "Add Channel to Favorites on Telegram" jaise buttons skip karein
    while start_idx < len(lines) and (
        "Share on WhatsApp" in lines[start_idx]
        or "Add Channel to Favorites" in lines[start_idx]
    ):
        start_idx += 1

    programs = []
    today_date = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    current_date = today_date
    last_start_minutes = -1
    block_start = start_idx

    for i in range(start_idx, len(lines)):
        if "Related Channels" in lines[i]:
            break

        match = TIME_PATTERN.match(lines[i])
        if match:
            chunk = lines[block_start:i]
            block_start = i + 1
            if not chunk:
                continue

            raw_title = chunk[0]
            # Agar "Started Yesterday" alag span/line mein ho toh merge karein
            if len(chunk) > 1 and chunk[1] == "Started Yesterday":
                raw_title = f"{raw_title} Started Yesterday"
                desc = " ".join(chunk[2:]) if len(chunk) > 2 else raw_title
            else:
                desc = " ".join(chunk[1:]) if len(chunk) > 1 else raw_title

            start_str, end_str = match.group(1), match.group(2)
            s_time = datetime.strptime(start_str.upper(), "%I:%M %p")
            e_time = datetime.strptime(end_str.upper(), "%I:%M %p")
            start_minutes = s_time.hour * 60 + s_time.minute

            if "Started Yesterday" in raw_title:
                title = raw_title.replace("Started Yesterday", "").strip()
                start_dt = (today_date - timedelta(days=1)).replace(
                    hour=s_time.hour, minute=s_time.minute
                )
                end_dt = today_date.replace(hour=e_time.hour, minute=e_time.minute)
                last_start_minutes = -1
            else:
                title = raw_title
                if last_start_minutes != -1 and start_minutes < last_start_minutes:
                    current_date += timedelta(days=1)
                last_start_minutes = start_minutes

                start_dt = current_date.replace(hour=s_time.hour, minute=s_time.minute)
                end_dt = current_date.replace(hour=e_time.hour, minute=e_time.minute)
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)

            programs.append({
                "title": title,
                "desc": desc,
                "start": start_dt.strftime("%Y%m%d%H%M%S +0530"),
                "stop": end_dt.strftime("%Y%m%d%H%M%S +0530"),
            })

    return programs


def build_epg():
    tv = ET.Element("tv", {"generator-info-name": "Custom-EPGSchedule-Scraper"})

    for ch_id, info in CHANNELS.items():
        ch_elem = ET.SubElement(tv, "channel", {"id": ch_id})
        disp = ET.SubElement(ch_elem, "display-name")
        disp.text = info["name"]

        try:
            progs = parse_schedule(info["url"])
            for p in progs:
                prog_elem = ET.SubElement(
                    tv,
                    "programme",
                    {"start": p["start"], "stop": p["stop"], "channel": ch_id},
                )
                t_elem = ET.SubElement(prog_elem, "title", {"lang": "en"})
                t_elem.text = p["title"]
                d_elem = ET.SubElement(prog_elem, "desc", {"lang": "en"})
                d_elem.text = p["desc"]
            print(f"Success: {info['name']} ({len(progs)} shows)")
        except Exception as e:
            print(f"Error scraping {info['name']}: {e}")

    xml_bytes = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(xml_bytes)


if __name__ == "__main__":
    build_epg()


