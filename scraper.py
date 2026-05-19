import re
import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def gercek_tarayici_ile_oku(url):
    """Sitelerin korumasını geçmek için arkada gizli bir Chrome açar."""
    try:
        with sync_playwright() as p:
            # Tarayıcıyı görünmez (headless) modda başlatıyoruz
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()
            
            # Sayfaya git ve tamamen yüklenmesi için 8 saniye bekle
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(8000) 
            
            html_content = page.content()
            browser.close()
            return html_content
    except Exception as e:
        print(f"Tarayıcı hatası ({url}): {e}")
        return None

def kaynakta_m3u8_ara(html_icerik):
    if not html_icerik:
        return None
    
    # Gelişmiş m3u8 yakalama kalıpları
    kalip_m3u8 = r'(https?://[^\s"\'`<>]+?\.m3u8[^\s"\'`<>]*)'
    bulunanlar = re.findall(kalip_m3u8, html_icerik)
    
    if bulunanlar:
        temiz_link = bulunanlar.replace('\\/', '/')
        if "analytics" not in temiz_link and "ads" not in temiz_link:
            return temiz_link
            
    return None

def kanalin_m3u8_linkini_bul(kanal_url):
    sayfa_html = gercek_tarayici_ile_oku(kanal_url)
    if not sayfa_html:
        return None
        
    m3u8_link = kaynakta_m3u8_ara(sayfa_html)
    if m3u8_link:
        return m3u8_link
        
    soup = BeautifulSoup(sayfa_html, 'html.parser')
    for iframe in soup.find_all(['iframe', 'embed'], src=True):
        iframe_src = iframe['src']
        if not iframe_src.startswith('http'):
            iframe_src = urllib.parse.urljoin(kanal_url, iframe_src)
            
        iframe_html = gercek_tarayici_ile_oku(iframe_src)
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
        print(f"🌐 {site_adi} sitesine gerçek tarayıcı simülasyonu ile bağlanılıyor...")
        kat_html = gercek_tarayici_ile_oku(kurallar["kategori_url"])
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
                    
                    print(f"   ↳ {title} kanalı taranıyor...")
                    m3u8_adresi = kanalin_m3u8_linkini_bul(tam_kanal_url)
                    if m3u8_adresi:
                        print(f"      ✅ M3U8 Linki Yakalandı!")
                        M3U_LISTESI.append({
                            "isim": title,
                            "grup": site_adi,
                            "stream_url": m3u8_adresi
                        })
                        
    return M3U_LISTESI

def m3u_dosyasi_olustur(liste, dosya_adi="playlist.m3u"):
    if not liste:
        print("⚠️ Uyarı: Hiçbir aktif kanal linki ayıklanamadı.")
        return
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for kanal in liste:
            f.write(f'#EXTINF:-1 group-title="{kanal["grup"]}",{kanal["isim"]}\n')
            f.write(f'{kanal["stream_url"]}\n')
    print(f"🎉 İşlem tamam! {dosya_adi} güncellendi.")

if __name__ == "__main__":
    bulunan_kanallar = sitelerden_veri_topla()
    m3u_dosyasi_olustur(bulunan_kanallar)
