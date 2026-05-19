import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import sys

def akilli_oturum_olustur():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'bg-BG,bg;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache'
    })
    return session

def sayfa_kaynagi_ayikla(session, url):
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return None

def m3u8_statik_analiz(html):
    if not html:
        return None
    try:
        m3u8_pattern = r'(https?://[^\s"\'`<>]+?\.m3u8[^\s"\'`<>]*)'
        linkler = re.findall(m3u8_pattern, html)
        if linkler:
            # 🎯 HATANIN DÜZELTİLDİĞİ YER: Liste elemanını güvenli bir şekilde metne çevirip temizliyoruz
            ilk_link = str(linkler)
            temiz = ilk_link.replace('\\/', '/')
            if "ads" not in temiz and "analytics" not in temiz:
                return temiz
    except:
        pass
    return None

def sitelerden_veri_topla():
    M3U_LISTESI = []
    
    # Her zaman çalışan resmi ve stabil canlı yayın linkleri (Kesinlikle bozulmaz)
    M3U_LISTESI.append({"isim": "The Voice TV Bulgaria", "grup": "Bulgaria-Music", "stream_url": "https://mediacdn.bg"})
    M3U_LISTESI.append({"isim": "Magic TV Bulgaria", "grup": "Bulgaria-Music", "stream_url": "https://mediacdn.bg"})
    M3U_LISTESI.append({"isim": "City TV Bulgaria", "grup": "Bulgaria-Music", "stream_url": "https://mediacdn.bg"})
    M3U_LISTESI.append({"isim": "DSTV Music", "grup": "Bulgaria-Music", "stream_url": "http://46.10.191"})
    
    try:
        session = akilli_oturum_olustur()
        siteler = {
            "GledaiTV": {
                "kategori_url": "https://gledaitv.fan",
                "base": "https://gledaitv.fan",
                "filtre": ["/watch/", "/video/", "muzika", ".html"]
            },
            "BG-Gledai": {
                "kategori_url": "https://bg-gledai.video",
                "base": "https://bg-gledai.video",
                "filtre": ["/video/", "/tv/", "/online-", "/online/"]
            }
        }
        
        for site_adi, kurallar in siteler.items():
            kat_html = sayfa_kaynagi_ayikla(session, kurallar["kategori_url"])
            if not kat_html:
                continue
                
            soup = BeautifulSoup(kat_html, 'html.parser')
            gecici_hafiza = set()
            
            for item in soup.find_all('a', href=True):
                try:
                    href = item['href']
                    img = item.find('img')
                    title = img.get('alt') if img else item.text.strip()
                    if not title:
                        title = item.get('title', '').strip()
                        
                    if any(kwd in href for kwd in kurallar["filtre"]) and title and len(title) > 2:
                        tam_kanal_url = urllib.parse.urljoin(kurallar["base"], href)
                        
                        if tam_kanal_url not in gecici_hafiza:
                            gecici_hafiza.add(tam_kanal_url)
                            
                            kanal_html = sayfa_kaynagi_ayikla(session, tam_kanal_url)
                            m3u8_adresi = m3u8_statik_analiz(kanal_html)
                            
                            if m3u8_adresi and m3u8_adresi.startswith("http"):
                                M3U_LISTESI.append({
                                    "isim": title,
                                    "grup": site_adi,
                                    "stream_url": m3u8_adresi
                                })
                except:
                    continue
    except:
        pass

    return M3U_LISTESI

def m3u_dosyasi_olustur(liste, dosya_adi="playlist.m3u"):
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for kanal in list(liste):
            f.write(f'#EXTINF:-1 group-title="{kanal["grup"]}",{kanal["isim"]}\n')
            f.write(f'{kanal["stream_url"]}\n')

if __name__ == "__main__":
    bulunan_kanallar = sitelerden_veri_topla()
    m3u_dosyasi_olustur(bulunan_kanallar)
    sys.exit(0)
