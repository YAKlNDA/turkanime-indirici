from os import system,path,mkdir
from configparser import ConfigParser
from bs4 import BeautifulSoup as bs4
from rich.progress import Progress, BarColumn, SpinnerColumn

from .players import url_getir
from .compile import dosya,get_config

class AnimeSorgula():
    def __init__(self,driver=None):
        self.driver=driver
        self.anime_ismi=None
        self.tamliste=None

    def get_seriler(self):
        """ Sitedeki tüm animeleri [{name:*,value:*}..] formatında döndürür. """
        with Progress(SpinnerColumn(), '[progress.description]{task.description}', BarColumn(bar_width=40)) as progress:
            task = progress.add_task("[cyan]Anime listesi getiriliyor..", start=False)
            if self.tamliste:
                progress.update(task,visible=False)
                return self.tamliste.keys()

            soup = bs4(
                    self.driver.execute_script("return $.get('https://www.turkanime.net/ajax/tamliste')"),
                "html.parser"
            )
            raw_series, self.tamliste = soup.findAll('span',{"class":'animeAdi'}) , {}
            for seri in raw_series:
                self.tamliste[seri.text] = seri.findParent().get('href').split('anime/')[1]
            progress.update(task,visible=False)
            return [seri.text for seri in raw_series]

    def get_bolumler(self, isim):
        """ Animenin bölümlerini {bölüm,title} formatında döndürür. """
        with Progress(SpinnerColumn(), '[progress.description]{task.description}', BarColumn(bar_width=40)) as progress:
            task = progress.add_task("[cyan]Bölümler getiriliyor..", start=False)
            anime_slug=self.tamliste[isim]
            raw = self.driver.execute_script(f"return $.get('/anime/{anime_slug}')")
            soup = bs4(raw,"html.parser")
            self.anime_ismi = soup.title.text
            anime_code = soup.find('meta',{'name':'twitter:image'}).get('content').split('lerb/')[1][:-4]

            raw = self.driver.execute_script(f"return $.get('https://www.turkanime.net/ajax/bolumler&animeId={anime_code}')")
            soup = bs4(raw,"html.parser")

            bolumler = []
            for bolum in soup.findAll("span",{"class":"bolumAdi"}):
                bolumler.append({
                    'name':bolum.text,
                    'value':bolum.findParent().get("href").split("video/")[1]
                })
            progress.update(task,visible=False)
            return bolumler


class Anime():
    """ İstenilen bölümü izle, yada bölümleri indir. """

    def __init__(self,driver,seri,bolumler):
        self.driver = driver
        self.seri = seri
        self.bolumler = bolumler

    def indir(self):
        parser = ConfigParser()
        parser.read(get_config())
        dlfolder = parser.get("TurkAnime","indirilenler")

        if not path.isdir(path.join(dlfolder,self.seri)):
            mkdir(path.join(dlfolder,self.seri))

        for bolum in self.bolumler:
            print(" "*50+"\rBölüm getiriliyor..",end="\r")
            self.driver.get(f"https://turkanime.net/video/{bolum}")
            print(" "*50+f"\r\n{self.driver.title} indiriliyor:")
            url = url_getir(self.driver)
            suffix="--referer https://video.sibnet.ru/" if "sibnet" in url else ""
            system(f'{dosya("youtube-dl.exe")} --no-warnings -o "{path.join(dlfolder,self.seri,bolum)}.%(ext)s" "{url}" {suffix}')
        return True

    def oynat(self):
        with Progress(SpinnerColumn(), '[progress.description]{task.description}', BarColumn(bar_width=40)) as progress:
            task = progress.add_task("[cyan]Sayfa yükleniyor..", start=False)
            self.driver.get(f"https://turkanime.net/video/{self.bolumler}")
            progress.update(task,visible=False)
        url = url_getir(self.driver)

        if not url:
            print("Çalışan bir video bulunamadı.")
            return False

        parser = ConfigParser()
        parser.read(get_config())

        suffix ="--referrer=https://video.sibnet.ru/ " if  "sibnet" in url else ""
        suffix+= "--msg-level=display-tags=no "
        suffix+="--stream-record={}.mp4 ".format(path.join(".","Kayıtlar",self.bolumler)) if parser.getboolean("TurkAnime","izlerken kaydet") else ""

        system(f'{dosya("mpv.exe")} "{url}" {suffix} ')
        return True
