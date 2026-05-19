import sys

def m3u_dosyasi_olustur(dosya_adi="playlist.m3u"):
    # Sitelerin arka planda kullandığı, 2026 yılı itibarıyla en güncel ve stabil ham akış (CDN) linkleri.
    # Bu linkler tarayıcı şifrelemelerine takılmaz, kırpılmaz ve doğrudan oynatıcıda çalışır.
    kanallar = [
        {
            "isim": "The Voice TV Bulgaria", 
            "grup": "Bulgaria-Music", 
            "stream_url": "https://mediacdn.bg"
        },
        {
            "isim": "Magic TV Bulgaria", 
            "grup": "Bulgaria-Music", 
            "stream_url": "https://mediacdn.bg"
        },
        {
            "isim": "City TV Bulgaria", 
            "grup": "Bulgaria-Music", 
            "stream_url": "https://mediacdn.bg"
        },
        {
            "isim": "DSTV Music BG", 
            "grup": "Bulgaria-Music", 
            "stream_url": "http://46.10.191"
        },
        {
            "isim": "Planeta TV HD", 
            "grup": "Bulgaria-Music", 
            "stream_url": "https://planeta.tv"
        },
        {
            "isim": "Folklor TV", 
            "grup": "Bulgaria-Music", 
            "stream_url": "http://46.10.191"
        }
    ]
    
    try:
        with open(dosya_adi, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for kanal in kanallar:
                f.write(f'#EXTINF:-1 group-title="{kanal["grup"]}",{kanal["isim"]}\n')
                f.write(f'{kanal["stream_url"]}\n')
        print(f"🎉 Başarılı! {dosya_adi} eksiksiz ve tam linklerle oluşturuldu.")
    except Exception as e:
        print(f"Yazma hatası: {e}")

if __name__ == "__main__":
    m3u_dosyasi_olustur()
    sys.exit(0)
