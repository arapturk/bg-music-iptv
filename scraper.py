import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def ag_trafiginden_m3u8_yakala(kanal_url):
    """Kanal sayfasını açar ve ağ üzerinden geçen gerçek m3u8 isteklerini dinler."""
    m3u8_linki = None
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = context.new_page()

            # 🚀 KRİTİK NOKTA: Arka plandaki tüm ağ isteklerini (Network Traffic) izliyoruz
            def istek_kontrolu(request):
                nonlocal m3u8_linki
                url = request.url
                # Reklam veya analiz dışındaki gerçek m3u8 akışlarını yakala
                if ".m3u8" in url and "analytics" not in url and "ads" not in url:
                    m3u8_linki = url
                    print(f"      🎯 Ağda Yakalandı -> {url[:60]}...")

            page.on("request", istek_kontrolu)

            print(f"🔗 Kanala Bağlanılıyor: {url_temizle(kanal_url)}")
            page.goto(kanal_url, wait_until="load", timeout=40000)
            
            # Oynatıcının yüklenip m3u8 isteği atması için 12 saniye ağ aktivitesini bekle
            page.wait_for_timeout(12000)
            browser.close()
            
    except Exception as e:
        print(f"❌ Tarayıcı hatası ({url_temizle(kanal_url)}): {e}")
        
    return m3u8_linki

def url_temizle(url):
    return url.split('?')[0] if url else ""

def kategori_html_oku(url):
    """Ana sayfadaki kanalları listelemek için ilk sayfayı okur."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
            return html
    except:
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
        kat_html = kategori_html_oku(kurallar["kategori_url"])
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
                    
                    print(f"   ↳ Kanal Analiz Ediliyor: {title}")
                    m3u8_adresi = ag_trafiginden_m3u8_yakala(tam_kanal_url)
                    
                    if m3u8_adresi:
                        M3U_LISTESI.append({
                            "isim": title,
                            "grup": site_adi,
                            "stream_url": m3u8_adresi
                        })
                        
    return M3U_LISTESI

def m3u_dosyasi_olustur(liste, dosya_adi="playlist.m3u"):
    if not list(filter(lambda x: x["grup"] != "Sistem", liste)):
        print("⚠️ Kritik: Yeni canlı link tespit edilemedi. Mevcut dosya korunuyor.")
        return
        
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for kanal in liste:
            f.write(f'#EXTINF:-1 group-title="{kanal["grup"]}",{kanal["isim"]}\n')
            f.write(f'{kanal["stream_url"]}\n')
    print(f"🎉 Başarılı! {dosya_adi} gerçek akış linkleriyle güncellendi.")

if __name__ == "__main__":
    bulunan_kanallar = sitelerden_veri_topla()
    m3u_dosyasi_olustur(bulunan_kanallar)
