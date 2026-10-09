# -*- coding: utf-8 -*-

import os
import re
import html
import math
import base64
import json
import cloudscraper
from urllib.parse import urljoin

SEED_BASEURL = 'https://dlive.sx/'

def get_scraper():
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'android',
            'desktop': False
        }
    )

def decode_econfig(raw):
    """
    Exact port of DaddyLive / DLHD obfuscated _econfig decoder:
      1. base64 decode raw string
      2. split into 4 equal segments
      3. drop the decoy canary char at index 3 of each segment
      4. base64 decode segments, reorder [2, 0, 3, 1]
      5. join + base64 decode -> JSON stream config
    """
    if not raw:
        return None
    try:
        order = [2, 0, 3, 1]
        decoded_b64 = base64.b64decode(raw).decode('utf-8')
        length = len(decoded_b64)
        if length < 4:
            return None
        
        part_len = math.ceil(length / 4)
        parts = []
        offset = 0
        for _ in range(4):
            parts.append(decoded_b64[offset:offset + part_len])
            offset += part_len
        
        ordered = [''] * 4
        for i, dest_idx in enumerate(order):
            if i < len(parts):
                c = parts[i]
                c = c[:3] + c[4:]  # drop decoy character
                ordered[dest_idx] = base64.b64decode(c).decode('utf-8')
        
        combined = "".join(ordered)
        final_json = base64.b64decode(combined).decode('utf-8')
        return json.loads(final_json)
    except Exception:
        return None

def resolve_channel_stream(channel_id):
    scraper = get_scraper()
    target_url = f"https://dlive.sx/cast/stream-{channel_id}.php"
    try:
        resp = scraper.get(target_url, headers={'Referer': 'https://dlive.sx/', 'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if not resp.ok:
            return None
        
        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', resp.text)
        if not iframe_match:
            return None
        
        source_url = iframe_match.group(1)
        if source_url.startswith('//'):
            source_url = 'https:' + source_url
        
        source_resp = scraper.get(source_url, headers={'Referer': 'https://dlive.sx/', 'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if not source_resp.ok:
            return None
        
        # Look for _econfig variable
        econfig_match = re.search(r'window\._econfig\s*=\s*[\'"]([^\'"]+)[\'"]', source_resp.text)
        if not econfig_match:
            econfig_match = re.search(r'_econfig\s*=\s*[\'"]([^\'"]+)[\'"]', source_resp.text)
        
        if econfig_match:
            config = decode_econfig(econfig_match.group(1))
            if config:
                stream_url = config.get('stream_url_nop2p') or config.get('stream_url')
                if stream_url:
                    return stream_url
        
        # Direct .m3u8 regex fallback
        m3u8_match = re.search(r'(https?://[^\s<>"\']+\.m3u8[^\s<>"\']*)', source_resp.text)
        if m3u8_match:
            return m3u8_match.group(1)
            
    except Exception as e:
        print(f"Error resolving channel {channel_id}: {e}")
    return None

def get_247_channels(base_url):
    scraper = get_scraper()
    url = urljoin(base_url, '24-7-channels.php')
    try:
        resp = scraper.post(url, headers={'Referer': base_url, 'User-Agent': 'Mozilla/5.0'}, timeout=15)
        card_rx = re.compile(
            r'<a\s+class="card"[^>]*?href="(?P<href>[^"]+)"[^>]*?data-title="(?P<data_title>[^"]*)"[^>]*>'
            r'.*?<div\s+class="card__title">\s*(?P<title>.*?)\s*</div>'
            r'.*?ID:\s*(?P<id>\d+)\s*</div>'
            r'.*?</a>',
            re.IGNORECASE | re.DOTALL
        )
        channels = []
        for m in card_rx.finditer(resp.text):
            title_dom = html.unescape(m.group('title').strip())
            title_attr = html.unescape(m.group('data_title').strip())
            name = title_dom or title_attr
            cid = m.group('id').strip()
            if '18+' in name.lower():
                continue
            channels.append({'name': name, 'id': cid})
        return channels
    except Exception as e:
        print(f"Error fetching channels: {e}")
        return []

def main():
    print("Fetching 24/7 Channels...")
    channels = get_247_channels(SEED_BASEURL)
    print(f"Found {len(channels)} channels. Resolving streams...")
    
    m3u_lines = ['#EXTM3U']
    for ch in channels:
        stream_url = resolve_channel_stream(ch['id'])
        if stream_url:
            m3u_lines.append(f'#EXTINF:-1 group-title="DLHD 24/7", {ch["name"]}')
            m3u_lines.append(stream_url)
            m3u_lines.append("")
            print(f"[SUCCESS] {ch['name']}")
        else:
            print(f"[FAILED] {ch['name']}")
    
    output_dir = 'daddy'
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, 'channels.m3u')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(m3u_lines))
    
    print(f"Playlist successfully saved to {file_path}")

if __name__ == '__main__':
    main()
    
