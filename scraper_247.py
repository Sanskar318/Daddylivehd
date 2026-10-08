# -*- coding: utf-8 -*-

import os
import re
import html
import cloudscraper
from urllib.parse import urljoin

SEED_BASEURL = 'https://dlive.sx/'

# USA Proxy configuration
PROXIES = {
    'http': 'http://158.101.8.92:1080',
    'https': 'http://158.101.8.92:1080'
}

def get_scraper():
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'android',
            'desktop': False
        }
    )

def resolve_active_baseurl(seed):
    scraper = get_scraper()
    try:
        resp = scraper.get(seed, proxies=PROXIES, timeout=15, allow_redirects=True)
        return resp.url if resp.url else seed
    except:
        return seed

def get_247_channels(base_url):
    scraper = get_scraper()
    url = urljoin(base_url, '24-7-channels.php')
    
    try:
        headers = {'Referer': base_url, 'User-Agent': 'Mozilla/5.0'}
        resp = scraper.post(url, headers=headers, proxies=PROXIES, timeout=15)
        html_text = resp.text

        card_rx = re.compile(
            r'<a\s+class="card"[^>]*?href="(?P<href>[^"]+)"[^>]*?data-title="(?P<data_title>[^"]*)"[^>]*>'
            r'.*?<div\s+class="card__title">\s*(?P<title>.*?)\s*</div>'
            r'.*?ID:\s*(?P<id>\d+)\s*</div>'
            r'.*?</a>',
            re.IGNORECASE | re.DOTALL
        )

        channels = []
        for m in card_rx.finditer(html_text):
            title_dom = html.unescape(m.group('title').strip())
            title_attr = html.unescape(m.group('data_title').strip())
            name = title_dom or title_attr
            cid = m.group('id').strip()

            if '18+' in name.lower():
                continue

            channels.append({'name': name, 'id': cid})

        return channels
    except Exception as e:
        print(f"Error fetching 24/7 channels: {e}")
        return []

def main():
    print("Resolving base URL using USA Proxy...")
    active_base = resolve_active_baseurl(SEED_BASEURL)
    print(f"Active Base: {active_base}")

    output_dir = 'daddy'
    os.makedirs(output_dir, exist_ok=True)

    print("Fetching 24/7 Channels...")
    channels = get_247_channels(active_base)

    m3u_lines = [
        '#EXTM3U url-tvg="https://raw.githubusercontent.com/mattiapergola/RobaFiga/raw/refs/heads/main/epg.xml"'
    ]

    for ch in channels:
        ch_name = ch['name']
        ch_id = ch['id']
        
        # Purana wala proxy URL format ya direct stream link jo aap use karna chahein
        proxy_url = f"https://proxyfacilissimo.dpdns.org/extractor/video.m3u8?host=dlstreams&url=https://dlive.sx/watch.php?id={ch_id}&redirect_stream=true&max_res=true&api_password=Milito22"
        
        inf_line = f'#EXTINF:-1 group-title="DLHD 24/7", {ch_name}'
        m3u_lines.append(inf_line)
        m3u_lines.append(proxy_url)
        m3u_lines.append("")

    file_path = os.path.join(output_dir, '247_channels.m3u')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(m3u_lines))
    
    print(f"Saved 24/7 M3U: {file_path} (Total channels: {len(channels)})")

if __name__ == '__main__':
    main()
    
