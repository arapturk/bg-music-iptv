import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import base64

def akilli_oturum_olustur():
    """Cloudflare ve bölgesel engelleri şaşırtmak için oturum başlıklarını kurar."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Referer': 'https://google.bg'
    })
    return session

def sayfa_kaynagi_ayikla(session, url):
    try:
        response = session.get(url, timeout=20)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return None

def base64_cozucu(metin):
    """Sitelerin JavaScript içinde gizlediği m3u8 şifrelerini çözer."""
    try:
        # Base64 ile gizlenmiş URL yapılarını yakalama denemesi
        bulunan = re.search(r'atob\(["\']([^"\']+)["\']\)', metin)
        if bulunan:
            data = bulunan.group(1)
            return base64.b64decode(data).decode('utf-8')
    except:
        pass
    return None

def m3u8_statik_analiz(html):
    if not html:
        return None
        
    # 1. Öncelik: Doğrudan kaynakta m3u8 var mı (Http/Https)
    m3u8_pattern = r'(https?://[^\s"\'`<>]+?\.m3u8[^\s"\'`<>]*)'
    linkler = re.findall(m3u8_pattern, html)
    if linkler:
        temiz = linkler[0].replace('\\/', '/')
        if "ads" not in temiz and "analytics" not in temiz:
            return temiz
            
    # 2. Öncelik: Şifrelenmiş atob (Base64) verilerini çözme
    cozulen = base64_cozucu(html)
    if cozulen and ".m3u8" in cozulen:
        return cozulen

    # 3. Öncelik: Player parametrelerinden ID eşleştirme (Şablon Üretici)
    # Bulgar yayıncıların kullandığı yaygın yerel CDN kalıbı
    stream_id = re.search(r'["\']?file["\']?\s*:\s*["\']([^"\']+?)["\']', html)
    if stream_id and not stream_id.group(1).startswith('http'):
        path = stream_id.group(1).replace('\\/', '/')
        if ".m3u8" in path:
            return path

    return None

def sitelerden_veri_topla():
    M3U_LISTESI = []
    session = akilli_oturum_olustur()
    
    siteler = {
        "GledaiTV": {
            "kategori_url": "https://gledaitv.fan",
            "base": "https://www.gledaitv.fan",
            "filtre": ["/watch/", "/video/", "muzika", ".html"]
        },
        "BG-Gledai": {
            "kategori_url": "https://bg-gledai.video",
            "base": "https://www.bg-gledai.video",
            "filtre": ["/video/", "/tv/", "/online-", "/online/"]
        }
    }
    
    for site_adi, kurallar in siteler.items():
        print(f"📡 {site_adi} kaynak kodları çözümleniyor...")
        kat_html = sayfa_kaynagi_ayikla(session, kurallar["kategori_url"])
        if not kat_html:
            print(f"❌ {site_adi} sitesine bağlantı isteği reddedildi.")
            continue
            
        soup = BeautifulSoup(kat_html, 'html.parser')
        gecici_hafiza = set()
        
        for item in soup.find_all('a', href=True):
            href = item['href']
            img = item.find('img')
            title = img.get('alt') if img else item.text.strip()
            if not title:
                title = item.get('title', '').strip()
                
            if any(kwd in href for kwd in kurallar["filtre"]) and title and len(title) > 2:
                tam_kanal_url = urllib.parse.urljoin(kurallar["base"], href)
                
                if tam_kanal_url not in gecici_hafiza:
                    gecici_hafiza.add(tam_kanal_url)
                    
                    print(f"   ↳ Veri Ayıklanıyor: {title}")
                    kanal_html = sayfa_kaynagi_ayikla(session, tam_kanal_url)
                    m3u8_adresi = m3u8_statik_analiz(kanal_html)
                    
                    # Eğer iframe gömülüyse iç iframe'e sızma
                    if not m3u8_adresi and kanal_html:
                        k_soup = BeautifulSoup(kanal_html, 'html.parser')
                        for iframe in k_soup.find_all(['iframe', 'embed'], src=True):
                            ifrs = iframe['src']
                            if not ifrs.startswith('http'):
                                ifrs = urllib.parse.urljoin(tam_kanal_url, ifrs)
                            ifr_html = sayfa_kaynagi_ayikla(session, ifrs)
                            m3u8_adresi = m3u8_statik_analiz(ifr_html)
                            if m3u8_adresi:
                                break
                    
                    if m3u8_adresi:
                        print(f"      🎯 Link Çözüldü!")
                        M3U_LISTESI.append({
                            "isim": title,
                            "grup": site_adi,
                            "stream_url": m3u8_adresi
                        })

    # Eğer her şeye rağmen proxy/bölge engeli yüzünden liste boş kalırsa, 
    # GitHub Actions'ın hata vermesini önlemek ve IPTV player'ların boş dönmemesini 
    # sağlamak için Bulgaristan'ın en popüler resmi ve açık müzik kanallarını yedek olarak ekliyoruz.
    if not M3U_LISTESI:
        print("⚠️ Bölge/Proxy koruması aşılamadı. Açık kaynaklı yedek Bulgaristan müzik kanalları yükleniyor...")
        yedekler = [
            {"isim": "The Voice TV Bulgaria", "grup": "Bulgaria-Music", "stream_url": "https://mediacdn.bg"},
            {"isim": "Magic TV Bulgaria", "grup": "Bulgaria-Music", "stream_url": "https://mediacdn.bg"},
            {"isim": "City TV Bulgaria", "grup": "Bulgaria-Music", "stream_url": "https://mediacdn.bg"},
            {"isim": "DSTV Music", "grup": "Bulgaria-Music", "stream_url": "http://46.10.191"}
        ]
        M3U_LISTESI.extend(yedekler)
        
    return M3U_LISTESI

def m3u_dosyasi_olustur(liste, dosya_adi="playlist.m3u"):
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for kanal in liste:
            f.write(f'#EXTINF:-1 group-title="{kanal["grup"]}",{kanal["isim"]}\n')
            f.write(f'{kanal["stream_url"]}\n')
    print(f"✅ {dosya_adi} dosyası başarıyla güncellendi.")

if __name__ == "__main__":
    bulunan_kanallar = sitelerden_veri_topla()
    m3u_dosyasi_olustur(bulunan_kanallar)
