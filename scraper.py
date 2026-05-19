import re
import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def gercek_tarayici_ile_oku(url):
    """Gelişmiş otomasyon engellerini aşmak için gerçekçi bir insan tarayıcısı simüle eder."""
    try:
        with sync_playwright() as p:
            # 1. Aşama: Cloudflare ve gelişmiş bot korumalarını atlatmak için argümanlar ekliyoruz
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled', # Otomasyon izlerini gizler
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # 2. Aşama: Gerçek bir Windows tarayıcı ortamı (Context) oluşturuyoruz
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="tr-TR,tr;q=0.9,en-US;q=0.8",
                timezone_id="Europe/Istanbul"
            )
            
            # webdriver=true izini silerek siteye "ben bir insanım" diyoruz
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            
            # 3. Aşama: Sayfaya git ve sitenin JavaScript ile m3u8 üretmesi için bekle
            print(f"🔗 Bağlanılıyor: {url}")
            page.goto(url, wait_until="load", timeout=45000)
            
            # Sayfa içinde hafifçe aşağı kaydırma simülasyonu (Tetikleyici)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(10000) # İçeriğin yüklenmesi için 10 saniye tam bekleme
            
            html_content = page.content()
            browser.close()
            return html_content
    except Exception as e:
        print(f"❌ Tarayıcı hatası ({url}): {e}")
        return None

def kaynakta_m3u8_ara(html_icerik):
    if not html_icerik:
        return None
    
    # Kapsamlı regex kalıpları
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
        
    # İframe ve oyuncu taraması
    soup = BeautifulSoup(sayfa_html, 'html.parser')
    for iframe in soup.find_all(['iframe', 'embed', 'video'], src=True):
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
        print(f"\n📺 {site_adi} ana kategorisi taranıyor...")
        kat_html = gercek_tarayici_ile_oku(kurallar["kategori_url"])
        if not kat_html:
            print(f"⚠️ {site_adi} ana sayfasına erişilemedi.")
            continue
            
        soup = BeautifulSoup(kat_html, 'html.parser')
        gecici_hafiza = set()
        
        # Sitedeki tüm link etiketlerini tara
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
                    
                    print(f"   ↳ Kanal İnceleniyor: {title}")
                    m3u8_adresi = kanalin_m3u8_linkini_bul(tam_kanal_url)
                    if m3u8_adresi:
                        print(f"      ✅ Başarılı! .m3u8 linki alındı.")
                        M3U_LISTESI.append({
                            "isim": title,
                            "grup": site_adi,
                            "stream_url": m3u8_adresi
                        })
                        
    return M3U_LISTESI

def m3u_dosyasi_olustur(liste, dosya_adi="playlist.m3u"):
    # 🚨 EĞER HİÇBİR KANAL BULUNAMAZSA: Dosyayı sıfırlayıp silmek yerine hata korumalı kapatıyoruz.
    if not liste:
        print("⚠️ Kritik: Canlı taramada sıfır link yakalandı. Mevcut dosya korunuyor.")
        return
        
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for kanal in liste:
            f.write(f'#EXTINF:-1 group-title="{kanal["grup"]}",{kanal["isim"]}\n')
            f.write(f'{kanal["stream_url"]}\n')
    print(f"🎉 Harika! {dosya_adi} başarıyla güncellendi.")

if __name__ == "__main__":
    bulunan_kanallar = sitelerden_veri_topla()
    m3u_dosyasi_olustur(bulunan_kanallar)
