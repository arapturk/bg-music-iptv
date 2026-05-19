import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

def hileli_istek_at(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://google.com'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        return response.text if response.status_code == 200 else None
    except:
        return None

def kaynakta_m3u8_ara(html_icerik):
    if not html_icerik:
        return None
    # .m3u8 uzantılı link yakalama regex yapısı
    kalip_m3u8 = r'(https?://[^\s"\'`<>]+?\.m3u8[^\s"\'`<>]*)'
    bulunanlar = re.findall(kalip_m3u8, html_icerik)
    
    if bulunanlar:
        temiz_link = bulunanlar[0].replace('\\/', '/')
        if "analytics" not in temiz_link and "ads" not in temiz_link:
            return temiz_link
    return None

def kanalin_m3u8_linkini_bul(kanal_url):
    sayfa_html = hileli_istek_at(kanal_url)
    if not sayfa_html:
        return None
        
    m3u8_link = kaynakta_m3u8_ara(sayfa_html)
    if m3u8_link:
        return m3u8_link
        
    soup = BeautifulSoup(sayfa_html, 'html.parser')
    for iframe in soup.find_all('iframe', src=True):
        iframe_src = iframe['src']
        if not iframe_src.startswith('http'):
            iframe_src = urllib.parse.urljoin(kanal_url, iframe_src)
            
        iframe_html = hileli_istek_at(iframe_src)
        m3u8_link = kaynakta_m3u8_ara(iframe_html)
        if m3u8_link:
            return m3u8_link
    return None

def sitelerden_veri_topla():
    M3U_LISTESI = []
    siteler = {
        "GledaiTV": {
            "kategori_url": "https://gledaitv.fan",
            "base": "https://gledaitv.fan",
            "filtre": ["/watch/", "/video/", "muzika"]
        },
        "BG-Gledai": {
            "kategori_url": "https://bg-gledai.video",
            "base": "https://bg-gledai.video",
            "filtre": ["/video/", "/tv/", "/online/"]
        }
    }
    
    for site_adi, kurallar in siteler.items():
        kat_html = hileli_istek_at(kurallar["kategori_url"])
        if not kat_html:
            continue
            
        soup = BeautifulSoup(kat_html, 'html.parser')
        gecici_hafiza = set()
        
        for item in soup.find_all('a', href=True):
            href = item['href']
            img = item.find('img')
            title = img.get('alt') if img else item.text.strip()
            if not title:
                title = item.get('title', '').strip()
                
            if any(kwd in href for kwd in kurallar["filtre"]) and title:
                tam_kanal_url = urllib.parse.urljoin(kurallar["base"], href)
                if tam_kanal_url not in gecici_hafiza:
                    gecici_hafiza.add(tam_kanal_url)
                    m3u8_adresi = kanalin_m3u8_linkini_bul(tam_kanal_url)
                    if m3u8_adresi:
                        M3U_LISTESI.append({
                            "isim": title,
                            "grup": site_adi,
                            "stream_url": m3u8_adresi
                        })
    return M3U_LISTESI

def m3u_dosyasi_olustur(liste, dosya_adi="playlist.m3u"):
    if not liste:
        return
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for kanal in liste:
            f.write(f'#EXTINF:-1 group-title="{kanal["grup"]}",{kanal["isim"]}\n')
            f.write(f'{kanal["stream_url"]}\n')

if __name__ == "__main__":
    bulunan_kanallar = sitelerden_veri_topla()
    m3u_dosyasi_olustur(bulunan_kanallar)
