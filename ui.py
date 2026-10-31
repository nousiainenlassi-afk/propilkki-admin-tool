"""Ulkoasun apuosat: sama ilme kuin propilkkitulospalvelu.fi:n työkaluissa.

Sivuston värit, Hanken Grotesk -fontti, pyöristetyt kortit ja napit, yläpalkki
taustakuvan päällä sekä vesistöruudut. Tkinter ei osaa pyöristää kulmia, joten
pyöristetyt pinnat piirretään Pillow'lla (reunat tasoitettuna) kuviksi.
"""
import base64
import ctypes
import io
import os
import sys
import textwrap
import tkinter as tk
import tkinter.font as tkf

from PIL import Image, ImageDraw, ImageFont

RES = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

# ---- sivuston värit (propilkkitulospalvelu.fi)
SIVU = '#060c14'        # sivun tausta
PINTA = '#0c1520'       # kortti (surface)
PINTA2 = '#162330'      # kentät, valikot, ruudut (surface-2)
HOVER = '#1b2a38'
REUNA = '#233444'
REUNA2 = '#2f4558'
PRIMARY = '#3ea8d8'
JAA = '#9ad8ea'
TEKSTI = '#e8eef3'
TEKSTI2 = '#a7b8c6'
TEKSTI3 = '#71879a'
OK = '#4fcf9a'
VIRHE = '#ef7b7b'
TUMMA = '#05121a'       # teksti vaaleiden nappien päällä
VALITTU = '#173345'     # primary 20 % taustan päällä

_perhe = 'Segoe UI'


def lataa_fontit():
    """Lataa mukana tulevat Hanken Grotesk -fontit tälle prosessille (vaatii Tk-juuren)."""
    global _perhe
    try:
        for f in ('HankenGrotesk-Regular.ttf', 'HankenGrotesk-Bold.ttf'):
            polku = os.path.join(RES, 'fontit', f)
            if os.path.exists(polku):
                ctypes.windll.gdi32.AddFontResourceExW(polku, 0x10, 0)   # FR_PRIVATE
        if 'Hanken Grotesk' in tkf.families():
            _perhe = 'Hanken Grotesk'
    except Exception:
        pass


def F(koko, lihava=False):
    return (_perhe, koko, 'bold' if lihava else 'normal')


def _pil_fontti(koko, lihava=False):
    nimi = 'HankenGrotesk-Bold.ttf' if lihava else 'HankenGrotesk-Regular.ttf'
    try:
        return ImageFont.truetype(os.path.join(RES, 'fontit', nimi), koko)
    except OSError:
        try:
            return ImageFont.truetype('segoeuib.ttf' if lihava else 'segoeui.ttf', koko)
        except OSError:
            return ImageFont.load_default()


def _kuvaksi(im):
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))


def _rgb(vari, alfa=255):
    vari = vari.lstrip('#')
    return tuple(int(vari[i:i + 2], 16) for i in (0, 2, 4)) + (alfa,)


def pyoristetty(w, h, r, taytto, reuna=None, ss=3):
    """Pyöristetty suorakulmio (RGBA, läpinäkyvät kulmat), tasoitettu."""
    w, h = max(int(w), 2 * r + 2), max(int(h), 2 * r + 2)
    im = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle(
        (0, 0, w * ss - 1, h * ss - 1), r * ss, fill=_rgb(taytto),
        outline=_rgb(reuna) if reuna else None, width=ss)
    return im.resize((w, h), Image.LANCZOS)


# ============================================================ kortti
class Kortti(tk.Canvas):
    """Pyöristetty kortti. Sisältö menee kenttään .sisa."""

    def __init__(self, vanhempi, vari=PINTA, reuna=REUNA, r=14, tila=14, venyta=False,
                 sivun_vari=SIVU):
        super().__init__(vanhempi, bg=sivun_vari, highlightthickness=0, bd=0, height=60)
        self.r, self.tila, self.vari, self.reuna_v, self.venyta = r, tila, vari, reuna, venyta
        self.sisa = tk.Frame(self, bg=vari)
        self._ikkuna = self.create_window(tila, tila, window=self.sisa, anchor='nw')
        self._kuva_id = None
        self._kuva = None
        self._koko_nyt = (0, 0)
        self.bind('<Configure>', self._canvas_muuttui)
        self.sisa.bind('<Configure>', self._sisa_muuttui)

    def _sisa_muuttui(self, _=None):
        if not self.venyta:
            h = self.sisa.winfo_reqheight() + 2 * self.tila
            if int(self.cget('height')) != h:
                self.configure(height=h)

    def _canvas_muuttui(self, e):
        w, h = e.width, e.height
        self.itemconfigure(self._ikkuna, width=max(w - 2 * self.tila, 1),
                           **({'height': max(h - 2 * self.tila, 1)} if self.venyta else {}))
        if (w, h) != self._koko_nyt and w > 4 and h > 4:
            self._koko_nyt = (w, h)
            self._kuva = _kuvaksi(pyoristetty(w, h, self.r, self.vari, self.reuna_v))
            if self._kuva_id is None:
                self._kuva_id = self.create_image(0, 0, image=self._kuva, anchor='nw')
                self.tag_lower(self._kuva_id)
            else:
                self.itemconfigure(self._kuva_id, image=self._kuva)


def otsikko(vanhempi, teksti, vari=PINTA):
    return tk.Label(vanhempi, text=teksti, bg=vari, fg=TEKSTI, font=F(12, True), anchor='w')


def pieni_otsikko(vanhempi, teksti, vari=PINTA):
    return tk.Label(vanhempi, text=teksti, bg=vari, fg=TEKSTI3, font=F(9), anchor='w')


# ============================================================ nappi
VARIANTIT = {
    'primary': dict(taytto='#5ab7e1', hover='#7cc8ec', fg=TUMMA, reuna='#5ab7e1'),
    'success': dict(taytto=OK, hover='#6fdcb0', fg=TUMMA, reuna=OK),
    'danger': dict(taytto=VIRHE, hover='#f39a9a', fg=TUMMA, reuna=VIRHE),
    'secondary': dict(taytto=PINTA2, hover=HOVER, fg=TEKSTI, reuna=REUNA2),
}


class Nappi(tk.Label):
    """Pyöristetty nappi (10 px kuten sivustolla). leveys=None -> täyttää tilan."""
    _kuvat = {}

    def __init__(self, vanhempi, teksti, komento, variantti='secondary', korkeus=38,
                 leveys=None, koko=10, bg=PINTA):
        v = VARIANTIT[variantti]
        super().__init__(vanhempi, text=teksti, compound='center', bd=0, highlightthickness=0,
                         cursor='hand2', bg=bg, fg=v['fg'], font=F(koko, True), padx=0, pady=0)
        self._v, self._komento, self._korkeus, self._leveys = v, komento, korkeus, leveys
        self._tila, self._hover, self._pw = 'normal', False, 0
        self.configure(width=leveys or 1, height=korkeus)
        self.bind('<Configure>', self._koko)
        self.bind('<Enter>', lambda e: self._aseta_hover(True))
        self.bind('<Leave>', lambda e: self._aseta_hover(False))
        self.bind('<ButtonRelease-1>', self._klikattu)
        self._piirra(leveys or 40)

    def _koko(self, e):
        if self._leveys is None and abs(e.width - self._pw) > 0 and e.width > 4:
            self._piirra(e.width)

    def _aseta_hover(self, arvo):
        self._hover = arvo
        self._piirra(self._pw)

    def _klikattu(self, e):
        if self._tila == 'normal' and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self._komento()

    def _piirra(self, w):
        self._pw = w
        v = self._v
        if self._tila == 'disabled':
            taytto, reuna, fg = BG_POIS, REUNA, TEKSTI3
        else:
            taytto = v['hover'] if self._hover else v['taytto']
            reuna, fg = v['reuna'], v['fg']
        avain = (w, self._korkeus, taytto, reuna)
        if avain not in Nappi._kuvat:
            Nappi._kuvat[avain] = _kuvaksi(pyoristetty(w, self._korkeus, 10, taytto, reuna))
        tk.Label.configure(self, image=Nappi._kuvat[avain], fg=fg,
                           cursor='hand2' if self._tila == 'normal' else 'arrow')

    def configure(self, cnf=None, **kw):
        kw = dict(cnf or {}, **kw)
        if 'state' in kw:
            self._tila = kw.pop('state')
            self._piirra(self._pw)
        if 'text' in kw:
            tk.Label.configure(self, text=kw.pop('text'))
        if kw:
            tk.Label.configure(self, **kw)

    config = configure


BG_POIS = '#101b26'


# ============================================================ yläpalkki
def _lumihiutale(koko=36):
    """Sivuston tunnuskuva: lumihiutale pyöristetyssä ruudussa."""
    ss = 4
    im = Image.new('RGBA', (koko * ss, koko * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, koko * ss - 1, koko * ss - 1), 10 * ss,
                        fill=_rgb(JAA, 20), outline=_rgb(JAA, 71), width=ss)
    s = koko * ss * 0.5 / 24      # 24 yksikön viewBox -> 50 % ruudusta
    ox = oy = koko * ss * 0.25

    def p(x, y):
        return (ox + x * s, oy + y * s)
    viivat = [[(12, 21.5), (12, 2.5)], [(3.77, 16.75), (20.23, 7.25)], [(3.77, 7.25), (20.23, 16.75)],
              [(14.6, 3.2), (12, 5.8), (9.4, 3.2)], [(20.92, 9.85), (17.37, 8.9), (18.32, 5.35)],
              [(18.32, 18.65), (17.37, 15.1), (20.92, 14.15)], [(9.4, 20.8), (12, 18.2), (14.6, 20.8)],
              [(3.08, 14.15), (6.63, 15.1), (5.68, 18.65)], [(5.68, 5.35), (6.63, 8.9), (3.08, 9.85)]]
    for v in viivat:
        d.line([p(*a) for a in v], fill=_rgb(JAA), width=max(int(2 * s), 2), joint='curve')
    return im.resize((koko, koko), Image.LANCZOS)


class Ylapalkki(tk.Canvas):
    """Sivuston yläpalkki: tunnuskuva + nimi vasemmalla, napit oikealla, kuva taustalla."""
    KORKEUS = 64

    def __init__(self, vanhempi, nimi='Pro Pilkki 2', alanimi='Tulospalvelu'):
        super().__init__(vanhempi, height=self.KORKEUS, bg='#0a1017', highlightthickness=0, bd=0)
        self._tausta = None
        self._tausta_w = 0
        self._napit = []
        try:
            self._kuva_pil = Image.open(os.path.join(RES, 'kuvat', 'tausta.jpg')).convert('RGB')
        except OSError:
            self._kuva_pil = None
        self._bg_id = self.create_image(0, 0, anchor='nw')
        self._tunnus = _kuvaksi(_lumihiutale())
        self.create_image(20, self.KORKEUS // 2, image=self._tunnus, anchor='w')
        self.create_text(66, self.KORKEUS // 2 - 9, text=nimi, anchor='w', fill=TEKSTI, font=F(13, True))
        self.create_text(66, self.KORKEUS // 2 + 9, text=alanimi, anchor='w', fill=TEKSTI2, font=F(9))
        self.bind('<Configure>', self._koko)
        self._ajastin = None

    def lisaa_nappi(self, nappi):
        self._napit.append(nappi)

    def _koko(self, e):
        self._sijoita(e.width)
        if self._ajastin:
            self.after_cancel(self._ajastin)
        self._ajastin = self.after(120, lambda: self._taustakuva(e.width))

    def _sijoita(self, w):
        self.delete('nappi')
        x = w - 18
        for n in self._napit:
            self.create_window(x, self.KORKEUS // 2, window=n, anchor='e', tags=('nappi',))
            x -= n.winfo_reqwidth() + 10

    def _taustakuva(self, w):
        if w < 10 or w == self._tausta_w:
            return
        self._tausta_w = w
        h = self.KORKEUS
        pohja = Image.new('RGB', (w, h), (10, 16, 23))
        if self._kuva_pil is not None:
            k = self._kuva_pil
            sk = w / k.width
            kk = k.resize((w, max(int(k.height * sk), h)), Image.LANCZOS)
            y0 = int(kk.height * 0.32)
            pohja = kk.crop((0, y0, w, y0 + h))
        peite = Image.new('RGB', (w, h), (8, 14, 20))
        pohja = Image.blend(pohja, peite, 0.78)
        ImageDraw.Draw(pohja).line((0, h - 1, w, h - 1), fill=_rgb(REUNA)[:3])
        self._tausta = _kuvaksi(pohja.convert('RGBA'))
        self.itemconfigure(self._bg_id, image=self._tausta)
        self.tag_lower(self._bg_id)


# ============================================================ vesistöruutu
_tiilet = {}
_jarvikuvat = {}


def tyhjenna_tiilet():
    _tiilet.clear()
    _jarvikuvat.clear()


def tiili(jarvi_koodi, nimi, alateksti, kuvapolku, tila, w=160, h=186, kieli=''):
    """Vesistöruutu kuvana: kuva + nimi + alateksti. tila: normal | hover | valittu."""
    avain = (jarvi_koodi, tila, w, h, kieli)
    if avain in _tiilet:
        return _tiilet[avain]
    taytto, reuna = {'normal': (PINTA2, REUNA), 'hover': (HOVER, REUNA2),
                     'valittu': (VALITTU, PRIMARY)}[tila]
    ss = 2
    im = pyoristetty(w * ss, h * ss, 10 * ss, taytto, reuna, ss=1)
    d = ImageDraw.Draw(im)
    if kuvapolku not in _jarvikuvat:
        try:
            _jarvikuvat[kuvapolku] = Image.open(kuvapolku).convert('RGBA')
        except OSError:
            _jarvikuvat[kuvapolku] = None
    kuva = _jarvikuvat[kuvapolku]
    y = 12 * ss
    if kuva is not None:
        k = min(100 / kuva.width, 100 / kuva.height)   # mahtuu 100 x 100 -ruutuun
        kk = kuva.resize((max(int(kuva.width * k * ss), 1), max(int(kuva.height * k * ss), 1)), Image.LANCZOS)
        im.alpha_composite(kk, ((w * ss - kk.width) // 2, y + (100 * ss - kk.height) // 2))
    y += 100 * ss + 10 * ss
    fn = _pil_fontti(11 * ss, tila == 'valittu')
    rivit = textwrap.wrap(nimi, 17) or [nimi]
    for r in rivit[:2]:
        lev = d.textlength(r, font=fn)
        d.text(((w * ss - lev) / 2, y), r, font=fn, fill=_rgb(TEKSTI))
        y += 16 * ss
    if alateksti:
        fs = _pil_fontti(9 * ss)
        lev = d.textlength(alateksti, font=fs)
        d.text(((w * ss - lev) / 2, y + 1 * ss), alateksti, font=fs, fill=_rgb(TEKSTI3))
    _tiilet[avain] = _kuvaksi(im.resize((w, h), Image.LANCZOS))
    return _tiilet[avain]
