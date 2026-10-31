"""Pro Pilkki 2 - etähallintatyökalu.

Valitse vesistö, vuorokaudenaika, vuodenaika, kesto ja pelimuoto graafisesti.
Työkalu lähettää komennot (/lake, /game, /lures, /results, /start, /stop)
hostin web-admin-sivulle IP:n ja portin kautta.
"""
import base64
import ctypes
import json
import os
import re
import sys
import threading
import time
import webbrowser
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import ttk

from kuvalataus import lataa_jarvikuvat
import kieli
import ui
from ui import (SIVU as BG, Kortti, Nappi, Ylapalkki, F, JAA, OK, PINTA, PINTA2 as PANEELI, REUNA,
                REUNA2, TEKSTI, TEKSTI2, TEKSTI3 as HIMMEA, TUMMA as DARK_TEXT, VALITTU, VIRHE,
                PRIMARY as KOROSTE, HOVER as KORTTI_HOVER, PINTA2 as KORTTI, otsikko,
                pieni_otsikko, tiili)
from kieli import (OHJE, TULOKSET, TULOS_KOODIT, VIEHETILA_KOODIT, VIEHETILAT, aika_nimi,
                   koodi_nimesta, muoto_nimi, t, tulos_nimi, viehelaji_nimi, viehetila_nimi,
                   vuodenaika_nimi)
from seuranta import ChatSeuranta, hae_info
from lakes import AJAT, JARVET, KESTOT, VIEHEITA, VIEHELAJIT, VUODENAJAT, sallitut_muodot, viehekoodi

# ------------------------------------------------------------------------ HTTP
RES = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
if getattr(sys, 'frozen', False):   # exe: käyttäjän omat tiedostot AppData-kansioon
    DATA = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
                        'ProPilkkiAdminTool')
else:
    DATA = RES
ASETUKSET = os.path.join(DATA, 'asetukset.json')
JARVIKUVAT = os.path.join(DATA, 'kuvat')            # ladataan ensimmäisellä käynnistyksellä
VIEHEKUVAT = os.path.join(RES, 'kuvat', 'vieheet')  # mukana exessä


def http_laheta(ip, portti, kayttaja, salasana, komennot, viive=0.5):
    """Lähettää komennot hostin web-admin-sivulle (POST /Admin.html, kenttä c).

    Palauttaa (onnistui, viesti). Jos käyttäjätunnus on tyhjä ja palvelin
    vastaa 401, yritetään vielä tunnuksella "admin".
    """
    url = f'http://{ip}:{portti}/Admin.html'
    kayttajat = [kayttaja] if kayttaja else ['', 'admin']
    for kayt in kayttajat:
        tunnus = base64.b64encode(f'{kayt}:{salasana}'.encode('latin-1', 'replace')).decode()
        try:
            for k in komennot:
                data = urllib.parse.urlencode({'c': k}, encoding='iso-8859-1').encode()
                req = urllib.request.Request(url, data=data, headers={
                    'Authorization': 'Basic ' + tunnus,
                    'Content-Type': 'application/x-www-form-urlencoded'})
                with urllib.request.urlopen(req, timeout=6) as r:
                    r.read()
                time.sleep(viive)
            return True, t('lahetetty', k=', '.join(c.split()[0] for c in komennot))
        except urllib.error.HTTPError as e:
            if e.code == 401 and kayt != kayttajat[-1]:
                continue
            if e.code == 401:
                return False, t('http401')
            return False, t('http_virhe', code=e.code)
        except (urllib.error.URLError, OSError) as e:
            return False, t('yhteys_epaonnistui', ip=ip, portti=portti, e=getattr(e, 'reason', e))
    return False, t('lahetys_epaonnistui')


# --------------------------------------------------------------------- sovellus

VERSIO = '1.4.0'
REPO_URL = 'https://github.com/nousiainenlassi-afk/propilkki-admin-tool'

TYOKALUT_URL = 'https://propilkkitulospalvelu.fi/#/tyokalut'
RUUTU_W, RUUTU_H = 136, 172


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        ui.lataa_fontit()
        self._aseta_kieli_alussa()
        self.title('Pro Pilkki 2 · Admin tool')
        self.geometry('1450x990')
        self.minsize(1240, 700)

        self.jarvi = JARVET[0]
        self.vuodenaika = tk.IntVar(value=3)
        self.aika = tk.IntVar(value=1)
        self.kesto = tk.IntVar(value=3)
        self.muoto = tk.StringVar()
        self.paikka = tk.StringVar()
        self.salasana = tk.StringVar()
        self.ip = tk.StringVar()
        self.portti = tk.StringVar()
        self.haku = tk.StringVar()
        self.status = tk.StringVar(value=t('valmis_status'))
        self.maara = tk.StringVar()
        self.nappi = {}
        self.kuvat = {}
        self.omat = [False] * VIEHEITA
        self.viehetila = tk.StringVar(value=viehetila_nimi('all'))
        self.tulokset = tk.StringVar(value=tulos_nimi('8'))
        self.viehe_kuvat = {}
        self.viehe_ikkuna = None
        self.seuraa_chat = tk.BooleanVar(value=True)
        self._info = None            # viimeisin info.json
        self._info_virhe = None
        self._info_tulos = None
        self._info_kaynnissa = False
        self._tikki = 0
        self._sarakkeita = 4
        self._chat = None
        self._chat_avain = None
        self._chat_edell = None
        self.sk_kuvaviite = None

        self._teema()
        self._ui()
        self.haku.trace_add('write', lambda *_: self._suodata())
        for v in (self.vuodenaika, self.aika, self.kesto, self.muoto, self.paikka,
                  self.salasana):
            v.trace_add('write', lambda *_: self._paivita())
        self.aika.trace_add('write', lambda *_: self._aika_vaihtui())
        self.viehetila.trace_add('write', lambda *_: self._viehetila_vaihtui())
        self.tulokset.trace_add('write', lambda *_: self._paivita())
        self._lataa_asetukset()
        self._hae_kuvat()
        self.after(500, self._seuranta_tikki)
        self._viehetila_vaihtui()
        self._suodata()
        self._valitse(self.jarvi)

    # ---- ohje
    def avaa_ohje(self):
        if getattr(self, 'ohje_ikkuna', None) and self.ohje_ikkuna.winfo_exists():
            self.ohje_ikkuna.lift()
            return
        w = self.ohje_ikkuna = tk.Toplevel(self)
        w.title(t('ohje_ikkuna'))
        w.configure(bg=PINTA)
        w.geometry(f'640x640+{self.winfo_rootx() + 60}+{self.winfo_rooty() + 40}')
        ylos = ttk.Frame(w)
        ylos.pack(fill='x', padx=14, pady=(12, 0))
        ttk.Label(ylos, text=t('ohje_otsikko'), foreground=TEKSTI,
                  font=('Segoe UI', 20, 'bold')).pack(side='left')
        ttk.Label(ylos, text=t('versio', v=VERSIO), foreground=HIMMEA).pack(
            side='left', padx=10, pady=(8, 0))
        Nappi(ylos, t('avaa_github'), lambda: webbrowser.open(REPO_URL), 'secondary', 36, 150).pack(
            side='right')
        kehys = ttk.Frame(w)
        kehys.pack(fill='both', expand=True, padx=14, pady=12)
        tx = tk.Text(kehys, wrap='word', bg=KORTTI, fg=TEKSTI2, relief='flat', padx=14, pady=10,
                    font=('Segoe UI', 10), highlightthickness=1, highlightbackground=REUNA,
                    spacing3=6, cursor='arrow')
        sb = ttk.Scrollbar(kehys, orient='vertical', command=tx.yview)
        tx.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        tx.pack(side='left', fill='both', expand=True)
        tx.tag_configure('h', foreground=KOROSTE, font=('Segoe UI', 11, 'bold'), spacing1=10)
        for tyyppi, teksti in OHJE[kieli.nyk()]:
            tx.insert('end', teksti + '\n', tyyppi)
        tx.configure(state='disabled')

    # ---- seuranta
    def _loki(self, teksti, tagi='oma'):
        self.loki.configure(state='normal')
        self.loki.insert('end', time.strftime('%H:%M:%S ') , 'aika')
        self.loki.insert('end', teksti + '\n', tagi)
        rivit = int(self.loki.index('end-1c').split('.')[0])
        if rivit > 500:
            self.loki.delete('1.0', f'{rivit - 500}.0')
        self.loki.configure(state='disabled')
        self.loki.see('end')

    def _seuranta_tikki(self):
        """Kerran sekunnissa: hakee tilan (2 s välein) ja chatin ja päivittää paneelin."""
        self._tikki += 1
        ip, portti = self.ip.get().strip(), self.portti.get().strip()
        valmis = bool(ip) and portti.isdigit()
        if self._info_tulos is not None:
            hip, hportti, info, virhe = self._info_tulos
            self._info_tulos = None
            if (hip, hportti) == (ip, portti):
                self._info, self._info_virhe = info, virhe
        if valmis and self._tikki % 2 == 0 and not self._info_kaynnissa:
            self._info_kaynnissa = True

            def tyo():
                info, virhe = hae_info(ip, portti)
                self._info_tulos = (ip, portti, info, virhe)
                self._info_kaynnissa = False
            threading.Thread(target=tyo, daemon=True).start()
        if not valmis:
            self._info, self._info_virhe = None, None
        self._nayta_info(valmis)
        self._chat_tikki(ip, portti)
        self.after(1000, self._seuranta_tikki)

    @staticmethod
    def _kisan_tila(aika):
        """TimeLeft -> (otsikko, teksti, väri). Tyhjä = ei kisaa käynnissä (lobby)."""
        a = (aika or '').strip()
        if re.fullmatch(r'\d+:\d\d', a):
            return t('tila_kaynnissa'), a, OK
        m = re.search(r'(\d+:\d\d)', a)
        if m and re.search(r'(?i)start', a):
            return t('tila_lobby_alkaa'), m.group(1), KOROSTE
        if a:
            return t('tila_lobby'), a, KOROSTE
        return t('tila_lobby_odottaa'), '–', KOROSTE

    def _nayta_info(self, valmis):
        i = self._info
        if not valmis:
            piste, tila, teksti = VIRHE, t('ei_yhteytta'), t('anna_ip')
        elif i is None and self._info_virhe:
            piste, tila, teksti = VIRHE, t('ei_yhteytta'), self._info_virhe
        elif i is None:
            piste, tila, teksti = HIMMEA, t('yhdistetaan'), ''
        else:
            piste, tila, teksti = OK, t('yhteys_ok'), i.get('Host', '')
        self.sk_piste.configure(fg=piste)
        self.sk_tila.configure(text=tila)
        self.yht_piste.configure(fg=piste)
        self.yht_teksti.configure(text=tila)
        self.sk_host.configure(text=teksti)
        if i is None:
            for w in (self.sk_versio, self.sk_jarvi, self.sk_peli, self.sk_aikaotsikko,
                      self.sk_aika, self.sk_kuvaus, self.sk_pelaajat):
                w.configure(text='')
            self.sk_kuva.configure(image='')
            return
        self.sk_versio.configure(text=i.get('Version', ''))
        jarvi = i.get('Lake', '')
        self.sk_jarvi.configure(text=jarvi)
        pituus = i.get('GameLength')
        self.sk_peli.configure(text=' · '.join(
            x for x in (i.get('GameType', ''), f'{pituus} min' if pituus else '') if x))
        otsikko, aika, vari = self._kisan_tila(i.get('TimeLeft'))
        self.sk_aikaotsikko.configure(text=otsikko)
        self.sk_aika.configure(text=aika, fg=vari)
        self.sk_kuvaus.configure(text=i.get('Description', '').strip())
        pelaajat = [p.get('Name', '?') for p in i.get('PlayerList', [])]
        jonossa = i.get('PlayersWaiting', 0)
        rivi = t('pelaajat', a=i.get('Players', len(pelaajat)), b=i.get('PlayersMax', '?'))
        if jonossa:
            rivi += t('jonossa', n=jonossa)
        if pelaajat:
            rivi += ': ' + ', '.join(pelaajat)
        self.sk_pelaajat.configure(text=rivi)
        kuva = next((self._kuva(j) for j in JARVET if j['nimi'] == jarvi), '')
        self.sk_kuvaviite = kuva
        self.sk_kuva.configure(image=kuva)

    def _chat_tikki(self, ip, portti):
        pw = self.salasana.get()
        avain = (ip, portti, pw) if (ip and portti.isdigit() and pw
                                    and self.seuraa_chat.get()) else None
        if avain == self._chat_edell and avain != self._chat_avain:   # vakaa kaksi tikkiä
            if self._chat:
                self._chat.lopeta()
                self._chat = None
            self._chat_avain = avain
            if avain:
                self._chat = ChatSeuranta(ip, portti, pw)
                self._chat.aloita()
                self._loki(t('chat_kaynnistyy'), 'tila')
        self._chat_edell = avain
        if self._chat:
            while not self._chat.jono.empty():
                tyyppi, teksti = self._chat.jono.get()
                self._loki(teksti, {'chat': 'chat', 'virhe': 'virhe', 'tila': 'tila'}[tyyppi])

    def _hae_kuvat(self):
        """Hakee puuttuvat vesistökuvat taustalla (kuvat tulevat pelin omalta sivulta)."""
        puuttuu = [j for j in JARVET
                   if not os.path.exists(os.path.join(JARVIKUVAT, j['koodi'] + '.png'))]
        if not puuttuu:
            return
        self._kuvat_valmis = False

        def tyo():
            try:
                lataa_jarvikuvat(JARVIKUVAT, puuttuu)
            finally:
                self._kuvat_valmis = True
        threading.Thread(target=tyo, daemon=True).start()
        self._odota_kuvat()

    def _odota_kuvat(self):
        if not self._kuvat_valmis:
            self.after(500, self._odota_kuvat)
            return
        self.kuvat.clear()
        ui.tyhjenna_tiilet()
        self._suodata()

    # ---- ulkoasu
    def _teema(self):
        self.configure(bg=BG)
        try:
            self.iconbitmap(os.path.join(RES, 'ikoni.ico'))
        except Exception:
            pass
        st = ttk.Style(self)
        st.theme_use('clam')
        st.configure('.', background=PINTA, foreground=TEKSTI, fieldbackground=PANEELI,
                     bordercolor=REUNA2, lightcolor=REUNA2, darkcolor=REUNA2,
                     troughcolor=PINTA, font=F(10))
        st.configure('TFrame', background=PINTA)
        st.configure('TLabel', background=PINTA, foreground=TEKSTI2)
        st.configure('TLabelframe', background=PINTA, bordercolor=REUNA, relief='solid')
        st.configure('TLabelframe.Label', background=PINTA, foreground=TEKSTI, font=F(10, True))
        st.configure('TRadiobutton', background=PINTA, foreground=TEKSTI, indicatorcolor=PANEELI)
        st.configure('TCheckbutton', background=PINTA, foreground=TEKSTI, indicatorcolor=PANEELI)
        st.map('TRadiobutton', background=[('active', PINTA)], indicatorcolor=[('selected', KOROSTE)],
               foreground=[('active', '#ffffff')])
        st.map('TCheckbutton', background=[('active', PINTA)], indicatorcolor=[('selected', KOROSTE)],
               foreground=[('active', '#ffffff')])
        st.configure('TEntry', fieldbackground=PANEELI, foreground=TEKSTI,
                     insertcolor=TEKSTI, padding=6)
        st.configure('TCombobox', fieldbackground=PANEELI, background=PANEELI,
                     foreground=TEKSTI, arrowcolor=TEKSTI2, padding=6)
        st.map('TCombobox', fieldbackground=[('readonly', PANEELI), ('disabled', PINTA)],
               foreground=[('disabled', HIMMEA)], selectbackground=[('readonly', PANEELI)],
               selectforeground=[('readonly', TEKSTI)])
        st.configure('Vertical.TScrollbar', background=REUNA2, troughcolor=PINTA,
                     arrowcolor=TEKSTI2, bordercolor=PINTA)
        self.option_add('*TCombobox*Listbox.background', PANEELI)
        self.option_add('*TCombobox*Listbox.foreground', TEKSTI)
        self.option_add('*TCombobox*Listbox.selectBackground', KOROSTE)
        self.option_add('*TCombobox*Listbox.selectForeground', DARK_TEXT)
        self.option_add('*TCombobox*Listbox.font', F(10))
        try:   # tumma otsikkopalkki Windows 10/11:ssa
            self.update()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            arvo = ctypes.c_int(1)
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(arvo), ctypes.sizeof(arvo))
        except Exception:
            pass

    # ---- käyttöliittymä
    def _ui(self):
        yp = Ylapalkki(self)
        yp.pack(side='top', fill='x')
        for teksti, komento, lev in ((t('kieli_nappi'), self.vaihda_kieli, 56),
                                     (t('ohje_nappi'), self.avaa_ohje, 100),
                                     (t('tyokalut_nappi'), lambda: webbrowser.open(TYOKALUT_URL), 120)):
            yp.lisaa_nappi(Nappi(yp, teksti, komento, 'secondary', 40, lev, bg='#0a1017'))

        runko = tk.Frame(self, bg=BG)
        runko.pack(fill='both', expand=True, padx=16, pady=(14, 14))
        vasen = tk.Frame(runko, bg=BG)
        vasen.pack(side='left', fill='both', expand=True)
        sk = tk.Frame(runko, bg=BG, width=372)
        sk.pack(side='right', fill='y', padx=(12, 0))
        sk.pack_propagate(False)
        oikea = tk.Frame(runko, bg=BG, width=372)
        oikea.pack(side='right', fill='y', padx=(12, 0))
        oikea.pack_propagate(False)

        # ------------------------------------------------ vasen: otsikko + vesistölista
        tk.Label(vasen, text=t('ylaotsikko'), bg=BG, fg=JAA, font=F(9, True), anchor='w').pack(fill='x')
        tk.Label(vasen, text='Admin tool', bg=BG, fg=TEKSTI, font=F(28, True), anchor='w').pack(fill='x')
        tk.Label(vasen, text=t('alaotsikko'), bg=BG, fg=TEKSTI2, font=F(10), anchor='w',
                 justify='left', wraplength=620).pack(fill='x', pady=(0, 10))
        lista = Kortti(vasen, venyta=True)
        lista.pack(fill='both', expand=True)
        ls = lista.sisa
        pieni_otsikko(ls, t('hae_vesistoa')).pack(fill='x')
        ttk.Entry(ls, textvariable=self.haku).pack(fill='x')
        tk.Label(ls, textvariable=self.maara, bg=PINTA, fg=HIMMEA, font=F(9), anchor='w').pack(
            fill='x', pady=(4, 6))
        kehys = tk.Frame(ls, bg=PINTA)
        kehys.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(kehys, highlightthickness=0, bg=PINTA)
        sb = ttk.Scrollbar(kehys, orient='vertical', command=self.canvas.yview)
        self.ruudukko = tk.Frame(self.canvas, bg=PINTA)
        self.ruudukko.bind('<Configure>', lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox('all')))
        ikkuna_id = self.canvas.create_window((0, 0), window=self.ruudukko, anchor='nw')
        self.canvas.bind('<Configure>', lambda e: self._canvas_leveys(e, ikkuna_id))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        # hiiren rulla vierittää aina vain vesistölistaa, ei vaihda muita asetuksia
        for tagi in ('all', 'TCombobox', 'Text'):
            self.bind_class(tagi, '<MouseWheel>', self._rulla)
        self._rakenna_ruudukko(JARVET)

        # ------------------------------------------------ keskellä: erän asetukset, vieheet, komennot
        def kortti(vanhempi, **kw):
            k = Kortti(vanhempi, **kw)
            return k

        def ryhma(s, otsikko_txt, arvot, var):
            pieni_otsikko(s, otsikko_txt).pack(fill='x')
            f = tk.Frame(s, bg=PINTA)
            f.pack(fill='x', pady=(0, 6))
            for k, nimi in arvot.items():
                ttk.Radiobutton(f, text=nimi, value=k, variable=var).pack(side='left', padx=(0, 12))

        a = kortti(oikea)
        a.pack(fill='x', pady=(0, 10))
        s = a.sisa
        otsikko(s, t('era_asetukset')).pack(fill='x', pady=(0, 6))
        ryhma(s, t('vuodenaika'), {k: vuodenaika_nimi(k) for k in VUODENAJAT}, self.vuodenaika)
        ryhma(s, t('vuorokaudenaika'), {k: aika_nimi(k) for k in AJAT}, self.aika)
        ryhma(s, t('kesto'), {k: str(v) for k, v in KESTOT.items()}, self.kesto)
        pieni_otsikko(s, t('pelimuoto')).pack(fill='x')
        self.muoto_cb = ttk.Combobox(s, textvariable=self.muoto, state='readonly')
        self.muoto_cb.pack(fill='x', pady=(0, 6))
        pieni_otsikko(s, t('aloituspaikka')).pack(fill='x')
        self.paikka_cb = ttk.Combobox(s, textvariable=self.paikka, state='readonly')
        self.paikka_cb.pack(fill='x')

        b = kortti(oikea)
        b.pack(fill='x', pady=(0, 10))
        s = b.sisa
        otsikko(s, t('viehe_ryhma')).pack(fill='x', pady=(0, 6))
        pieni_otsikko(s, t('vieheet')).pack(fill='x')
        r = tk.Frame(s, bg=PINTA)
        r.pack(fill='x', pady=(0, 6))
        self.viehe_cb = ttk.Combobox(r, textvariable=self.viehetila, state='readonly',
                                     values=[viehetila_nimi(k) for k in VIEHETILA_KOODIT])
        self.viehe_cb.pack(side='left', fill='x', expand=True)
        self.viehe_valinta = Nappi(r, t('valitse_vieheet'), self.avaa_vieheet, 'secondary', 34, 150)
        self.viehe_valinta.pack(side='left', padx=(8, 0))
        pieni_otsikko(s, t('valiajat')).pack(fill='x')
        ttk.Combobox(s, textvariable=self.tulokset, state='readonly',
                     values=[tulos_nimi(k) for k in TULOS_KOODIT]).pack(fill='x', pady=(0, 8))
        Nappi(s, t('laheta_asetukset'), self.laheta_asetukset, 'secondary', 38).pack(fill='x')

        d = kortti(oikea)
        d.pack(fill='x')
        s = d.sisa
        otsikko(s, t('komennot')).pack(fill='x', pady=(0, 6))
        self.esikatselu = tk.Text(s, height=6, width=10, state='disabled', wrap='char',
                                  font=('Consolas', 10), bg='#070d13', fg=JAA,
                                  relief='flat', padx=10, pady=8, highlightthickness=1,
                                  highlightbackground=REUNA2, highlightcolor=REUNA2)
        self.esikatselu.pack(fill='x', pady=(0, 10))
        r = tk.Frame(s, bg=PINTA)
        r.pack(fill='x', pady=(0, 8))
        Nappi(r, t('kopioi'), self.kopioi, 'secondary', 40, 96).pack(side='right', padx=(8, 0))
        Nappi(r, t('laheta'), self.laheta, 'primary', 40).pack(side='left', fill='x', expand=True)
        r = tk.Frame(s, bg=PINTA)
        r.pack(fill='x')
        Nappi(r, t('kaynnista'), lambda: self.ohjaus('/start'), 'success', 40).pack(
            side='left', fill='x', expand=True)
        Nappi(r, t('pysayta'), lambda: self.ohjaus('/stop'), 'danger', 40).pack(
            side='left', fill='x', expand=True, padx=(8, 0))
        tk.Label(s, textvariable=self.status, bg=PINTA, fg=HIMMEA, font=F(9), anchor='w',
                 justify='left', wraplength=320).pack(fill='x', pady=(8, 0))

        # ------------------------------------------------ oikealla: host, tila, loki
        tk.Label(sk, text=t('seuranta'), bg=BG, fg=JAA, font=F(9, True), anchor='w').pack(fill='x')
        h = kortti(sk)
        h.pack(fill='x', pady=(4, 10))
        s = h.sisa
        otsikko(s, t('hosti_ryhma')).pack(fill='x', pady=(0, 6))
        rivi = tk.Frame(s, bg=PINTA)
        rivi.pack(fill='x')
        ip_k = tk.Frame(rivi, bg=PINTA)
        ip_k.pack(side='left', fill='x', expand=True)
        ipr = tk.Frame(ip_k, bg=PINTA)
        ipr.pack(fill='x')
        pieni_otsikko(ipr, t('ip')).pack(side='left')
        self.yht_teksti = tk.Label(ipr, text=t('ei_yhteytta'), bg=PINTA, fg=TEKSTI2, font=F(9))
        self.yht_teksti.pack(side='right')
        self.yht_piste = tk.Label(ipr, text='●', bg=PINTA, fg=VIRHE, font=F(10))
        self.yht_piste.pack(side='right', padx=(0, 3))
        ttk.Entry(ip_k, textvariable=self.ip).pack(fill='x')
        pt_k = tk.Frame(rivi, bg=PINTA)
        pt_k.pack(side='left', padx=(8, 0))
        pieni_otsikko(pt_k, t('portti')).pack(fill='x')
        ttk.Entry(pt_k, textvariable=self.portti, width=7).pack()
        pieni_otsikko(s, t('salasana')).pack(fill='x', pady=(6, 0))
        pwr = tk.Frame(s, bg=PINTA)
        pwr.pack(fill='x', pady=(0, 8))
        self.pw_kentta = ttk.Entry(pwr, textvariable=self.salasana, show='•')
        self.pw_kentta.pack(side='left', fill='x', expand=True)
        silma = tk.Label(pwr, text='👁', bg=PANEELI, fg=TEKSTI2, font=('Segoe UI Emoji', 11),
                         width=3, cursor='hand2', highlightthickness=1,
                         highlightbackground=REUNA2)
        silma.pack(side='left', padx=(6, 0), fill='y')
        # silmä: salasana näkyy vain niin kauan kuin hiiren painike on pohjassa
        silma.bind('<ButtonPress-1>', lambda e: (self.pw_kentta.configure(show=''),
                                                 silma.configure(fg=KOROSTE)))
        silma.bind('<ButtonRelease-1>', lambda e: (self.pw_kentta.configure(show='•'),
                                                   silma.configure(fg=TEKSTI2)))
        silma.bind('<Leave>', lambda e: (self.pw_kentta.configure(show='•'),
                                         silma.configure(fg=TEKSTI2)))
        ah = tk.Frame(s, bg=PINTA)
        ah.pack(fill='x')
        Nappi(ah, 'Autohost ON', lambda: self.ohjaus('/autohost on'), 'secondary', 36).pack(
            side='left', fill='x', expand=True)
        Nappi(ah, 'Autohost OFF', lambda: self.ohjaus('/autohost off'), 'secondary', 36).pack(
            side='left', fill='x', expand=True, padx=(8, 0))

        def etiketti(vanhempi, **kw):
            kw.setdefault('bg', PINTA)
            kw.setdefault('fg', TEKSTI)
            kw.setdefault('anchor', 'w')
            kw.setdefault('justify', 'left')
            return tk.Label(vanhempi, **kw)

        tila_k = kortti(sk)
        tila_k.pack(fill='x', pady=(0, 10))
        kortti_s = tila_k.sisa
        otsikko(kortti_s, t('hosti_nyt')).pack(fill='x', pady=(0, 6))
        ylos = tk.Frame(kortti_s, bg=PINTA)
        ylos.pack(fill='x')
        self.sk_piste = etiketti(ylos, text='●', fg=HIMMEA, font=F(12))
        self.sk_piste.pack(side='left')
        self.sk_tila = etiketti(ylos, text=t('ei_yhteytta'), fg=TEKSTI2, font=F(10, True))
        self.sk_tila.pack(side='left', padx=(4, 0))
        self.sk_host = etiketti(kortti_s, text=t('anna_ip'), font=F(13, True), wraplength=330)
        self.sk_host.pack(fill='x')
        self.sk_versio = etiketti(kortti_s, text='', fg=HIMMEA, font=F(9))
        self.sk_versio.pack(fill='x')
        keski = tk.Frame(kortti_s, bg=PINTA)
        keski.pack(fill='x', pady=8)
        self.sk_kuva = tk.Label(keski, bg=PINTA)
        self.sk_kuva.pack(side='left')
        tied = tk.Frame(keski, bg=PINTA)
        tied.pack(side='left', fill='x', expand=True, padx=(10, 0))
        self.sk_jarvi = etiketti(tied, text='', font=F(12, True), wraplength=210)
        self.sk_jarvi.pack(fill='x')
        self.sk_peli = etiketti(tied, text='', fg=TEKSTI2, wraplength=210)
        self.sk_peli.pack(fill='x')
        self.sk_aikaotsikko = etiketti(tied, text='', fg=HIMMEA, font=F(9), wraplength=210)
        self.sk_aikaotsikko.pack(fill='x', pady=(6, 0))
        self.sk_aika = etiketti(tied, text='', fg=OK, font=F(24, True))
        self.sk_aika.pack(fill='x')
        self.sk_kuvaus = etiketti(kortti_s, text='', fg=TEKSTI2, wraplength=330)
        self.sk_kuvaus.pack(fill='x')
        self.sk_pelaajat = etiketti(kortti_s, text='', fg=TEKSTI2, wraplength=330)
        self.sk_pelaajat.pack(fill='x', pady=(4, 0))

        loki_k = kortti(sk, venyta=True)
        loki_k.pack(fill='both', expand=True)
        ls = loki_k.sisa
        otsikko(ls, t('hostin_loki')).pack(fill='x')
        ttk.Checkbutton(ls, text=t('seuraa_chat'), variable=self.seuraa_chat).pack(
            anchor='w', pady=(2, 6))
        lokiriv = tk.Frame(ls, bg=PINTA)
        lokiriv.pack(fill='both', expand=True)
        self.loki = tk.Text(lokiriv, width=10, height=8, state='disabled', wrap='word',
                            font=('Consolas', 9), bg='#070d13', fg=TEKSTI, relief='flat',
                            padx=8, pady=6, highlightthickness=1, highlightbackground=REUNA2,
                            highlightcolor=REUNA2)
        lsb = ttk.Scrollbar(lokiriv, orient='vertical', command=self.loki.yview)
        self.loki.configure(yscrollcommand=lsb.set)
        lsb.pack(side='right', fill='y')
        self.loki.pack(side='left', fill='both', expand=True)
        self.loki.tag_configure('aika', foreground=HIMMEA)
        self.loki.tag_configure('oma', foreground=JAA)
        self.loki.tag_configure('chat', foreground=TEKSTI)
        self.loki.tag_configure('virhe', foreground=VIRHE)
        self.loki.tag_configure('tila', foreground=OK)

    def _canvas_leveys(self, e, ikkuna_id):
        self.canvas.itemconfigure(ikkuna_id, width=e.width)
        n = max(1, e.width // (RUUTU_W + 8))
        if n != self._sarakkeita:
            self._sarakkeita = n
            if getattr(self, '_sarake_ajastin', None):
                self.after_cancel(self._sarake_ajastin)
            self._sarake_ajastin = self.after(150, self._suodata)

    def _tiili(self, j, tila):
        alateksti = t('aloituspaikkoja', n=len(j['paikat'])) if j['paikat'] else ''
        return tiili(j['koodi'], j['nimi'], alateksti, os.path.join(JARVIKUVAT, j['koodi'] + '.png'),
                     tila, RUUTU_W, RUUTU_H, kieli.nyk())

    def _rakenna_ruudukko(self, jarvet):
        for w in self.ruudukko.winfo_children():
            w.destroy()
        self.nappi.clear()
        sarakkeita = self._sarakkeita
        for i, j in enumerate(jarvet):
            b = tk.Label(self.ruudukko, image=self._tiili(j, 'normal'), bg=PINTA, bd=0,
                         cursor='hand2')
            b.bind('<Button-1>', lambda e, x=j: self._valitse(x))
            b.bind('<Enter>', lambda e, x=j: self._hover(x, True))
            b.bind('<Leave>', lambda e, x=j: self._hover(x, False))
            b.grid(row=i // sarakkeita, column=i % sarakkeita, padx=3, pady=3)
            self.nappi[j['koodi']] = b
        self._korosta()

    # ---- vieheet ja väliajat
    def viehe_komento(self):
        koodi = self.viehe_koodi()
        if koodi == 'custom':
            return '/lures custom ' + viehekoodi(self.omat)
        return '/lures ' + koodi

    def viehe_koodi(self):
        return koodi_nimesta({'x': {k: viehetila_nimi(k) for k in VIEHETILA_KOODIT}},
                             self.viehetila.get()) or 'all'

    def tulos_koodi(self):
        return koodi_nimesta({'x': {k: tulos_nimi(k) for k in TULOS_KOODIT}},
                             self.tulokset.get()) or '8'

    def tulos_komento(self):
        return '/results ' + self.tulos_koodi()

    def _viehetila_vaihtui(self):
        oma = self.viehe_koodi() == 'custom'
        self.viehe_valinta.configure(state='normal' if oma else 'disabled')
        self._paivita()

    def laheta_asetukset(self):
        if self.viehe_koodi() == 'custom' and not any(self.omat):
            self.status.set(t('oma_tyhja'))
            return
        self.laheta([self.tulos_komento(), self.viehe_komento()])

    def avaa_vieheet(self):
        if self.viehe_ikkuna and self.viehe_ikkuna.winfo_exists():
            self.viehe_ikkuna.lift()
            return
        w = self.viehe_ikkuna = tk.Toplevel(self)
        w.title(t('viehe_ikkuna'))
        w.configure(bg=PINTA)
        w.transient(self)
        self.viehe_napit = {}
        self.laji_otsikot = {}
        ylos = ttk.Frame(w)
        ylos.pack(fill='x', padx=10, pady=(8, 0))
        self.viehe_yht = tk.StringVar()
        ttk.Label(ylos, textvariable=self.viehe_yht, foreground=KOROSTE,
                  font=('Segoe UI', 11, 'bold')).pack(side='left')
        Nappi(ylos, t('valmis_nappi'), w.destroy, 'primary', 36, 90).pack(side='right')
        Nappi(ylos, t('tyhjenna_kaikki'), lambda: self._aseta_vieheet(range(VIEHEITA), False),
              'secondary', 36, 130).pack(side='right', padx=8)
        Nappi(ylos, t('valitse_kaikki'), lambda: self._aseta_vieheet(range(VIEHEITA), True),
              'secondary', 36, 130).pack(side='right')
        rivit = [ttk.Frame(w) for _ in range(3)]
        for r in rivit:
            r.pack(fill='x', padx=10, pady=4)
        paikat = [rivit[0], rivit[1], rivit[2], rivit[2]]
        for ind, ((nimi, alku, maara, kuva), vanhempi) in enumerate(zip(VIEHELAJIT, paikat)):
            laatikko = ttk.LabelFrame(vanhempi, text=viehelaji_nimi(ind))
            laatikko.pack(side='left', fill='x', expand=(maara == 16), padx=(0, 8))
            kp = ttk.Frame(laatikko)
            kp.pack(fill='x', padx=6)
            otsikko = tk.StringVar()
            self.laji_otsikot[nimi] = otsikko
            ttk.Label(kp, textvariable=otsikko, foreground=HIMMEA).pack(side='left')
            Nappi(kp, t('tyhjenna'), lambda a=alku, m=maara: self._aseta_vieheet(range(a, a + m), False),
                  'secondary', 30, 90, 9).pack(side='right')
            Nappi(kp, t('valitse_kaikki'), lambda a=alku, m=maara: self._aseta_vieheet(range(a, a + m), True),
                  'secondary', 30, 130, 9).pack(side='right', padx=6)
            rivi = ttk.Frame(laatikko)
            rivi.pack(padx=4, pady=4)
            for i in range(maara):
                n = alku + i
                b = tk.Button(rivi, text=str(i + 1), image=self._viehekuva(kuva, i + 1),
                              compound='top', relief='flat', bd=0, bg=KORTTI, fg=TEKSTI,
                              highlightthickness=1, highlightbackground=REUNA,
                              activebackground=KORTTI_HOVER, cursor='hand2',
                              font=('Segoe UI', 9), command=lambda x=n: self._vaihda_viehe(x))
                b.grid(row=0, column=i, padx=2, pady=2)
                self.viehe_napit[n] = b
        self._piirra_vieheet()
        w.update_idletasks()
        w.geometry(f'+{self.winfo_rootx() + 30}+{self.winfo_rooty() + 30}')

    def _viehekuva(self, kuva, nro):
        avain = (kuva, nro)
        if avain not in self.viehe_kuvat:
            polku = os.path.join(VIEHEKUVAT, f'{kuva}-{nro:02d}.png')
            try:
                self.viehe_kuvat[avain] = tk.PhotoImage(file=polku).subsample(2)
            except tk.TclError:
                self.viehe_kuvat[avain] = ''
        return self.viehe_kuvat[avain]

    def _vaihda_viehe(self, n):
        self.omat[n] = not self.omat[n]
        self._piirra_vieheet()

    def _aseta_vieheet(self, alue, arvo):
        for n in alue:
            self.omat[n] = arvo
        self._piirra_vieheet()

    def _piirra_vieheet(self):
        for n, b in self.viehe_napit.items():
            on = self.omat[n]
            b.configure(bg=VALITTU if on else KORTTI,
                        highlightbackground=KOROSTE if on else REUNA)
        for nimi, alku, maara, _ in VIEHELAJIT:
            self.laji_otsikot[nimi].set(f'{sum(self.omat[alku:alku + maara])}/{maara}')
        self.viehe_yht.set(t('valittu_vieheita', n=sum(self.omat), m=VIEHEITA))
        self._paivita()

    def _kuva(self, jarvi):
        """Vesistön kuva kansiosta kuvat/ (lataa_kuvat.py). Puuttuessa ei kuvaa."""
        if jarvi['koodi'] not in self.kuvat:
            polku = os.path.join(JARVIKUVAT, jarvi['koodi'] + '.png')
            try:
                self.kuvat[jarvi['koodi']] = tk.PhotoImage(file=polku)
            except tk.TclError:
                self.kuvat[jarvi['koodi']] = ''
        return self.kuvat[jarvi['koodi']]

    def _suodata(self):
        q = self.haku.get().strip().lower()
        yo = self.aika.get() == 4
        ajalla = [j for j in JARVET if j['yo'] or not yo]
        nakyvat = [j for j in ajalla if q in j['nimi'].lower()]
        if q:
            self.maara.set(f'{len(nakyvat)} / {len(ajalla)}')
        else:
            self.maara.set(t('yojarvia' if yo else 'jarvia', n=len(ajalla)))
        self._rakenna_ruudukko(nakyvat)

    def _aika_vaihtui(self):
        """Yöllä näytetään vain yövesistöt; ei-yövesistö vaihtuu ensimmäiseen yövesistöön."""
        if self.aika.get() == 4 and not self.jarvi['yo']:
            vanha = self.jarvi['nimi']
            uusi = next(j for j in JARVET if j['yo'])
            self.status.set(t('ei_yopelia', vanha=vanha, uusi=uusi['nimi']))
            self.jarvi = uusi
            self._paivita_valinnat()
        self._suodata()
        self._korosta()

    def _korosta(self):
        for j in JARVET:
            b = self.nappi.get(j['koodi'])
            if b is not None:
                b.configure(image=self._tiili(j, 'valittu' if j['koodi'] == self.jarvi['koodi'] else 'normal'))

    def _hover(self, jarvi, sisalla):
        b = self.nappi.get(jarvi['koodi'])
        if b and jarvi['koodi'] != self.jarvi['koodi']:
            b.configure(image=self._tiili(jarvi, 'hover' if sisalla else 'normal'))

    # ---- logiikka
    def _valitse(self, jarvi):
        self.jarvi = jarvi
        self._korosta()
        self._paivita_valinnat()
        self._paivita()

    def _rulla(self, e):
        if e.widget is self.loki:
            self.loki.yview_scroll(-1 * (e.delta // 120), 'units')
        elif e.widget.winfo_toplevel() is self:
            self.canvas.yview_scroll(-1 * (e.delta // 120), 'units')
        elif isinstance(e.widget, tk.Text):
            e.widget.yview_scroll(-1 * (e.delta // 120), 'units')
        return 'break'

    def _paivita_valinnat(self):
        j = self.jarvi
        muodot = sallitut_muodot(j, self.aika.get())
        self.muotolista = {muoto_nimi(m): m for m in muodot}
        self.muoto_cb['values'] = list(self.muotolista)
        if self.muoto.get() not in self.muotolista:
            self.muoto.set(next(iter(self.muotolista)))
        paikat = j['paikat'] or [t('ainoa_paikka')]
        self.paikka_cb['values'] = paikat
        self.paikka_cb.configure(state='readonly' if j['paikat'] else 'disabled')
        if self.paikka.get() not in paikat:
            self.paikka.set(paikat[0])

    def komennot(self):
        j = self.jarvi
        aika = self.aika.get()
        muoto = self.muotolista.get(self.muoto.get(), 1)
        paikat = j['paikat'] or ['x']
        paikka = paikat.index(self.paikka.get()) + 1 if self.paikka.get() in paikat else 1
        kom = []
        kom.append(f"/lake {j['koodi']},{self.vuodenaika.get()},{aika},{self.kesto.get()}")
        kom.append(f'/game {muoto},{paikka}')
        return kom

    def _paivita(self):
        if not hasattr(self, 'muotolista'):
            return
        # yöruudun muutos voi vaihtaa muotolistan
        vanha = list(self.muoto_cb['values'])
        uusi = [muoto_nimi(m) for m in sallitut_muodot(self.jarvi, self.aika.get())]
        if vanha != uusi:
            self._paivita_valinnat()
        kom = self.komennot()
        nayta = [('/admin ' + '•' * len(self.salasana.get())) if k.startswith('/admin') else k
                 for k in kom]
        self.esikatselu.configure(state='normal')
        self.esikatselu.delete('1.0', 'end')
        self.esikatselu.insert('1.0', '\n'.join(
            nayta + ['', self.tulos_komento(), self.viehe_komento()]))
        self.esikatselu.configure(state='disabled')

    def kopioi(self):
        self.clipboard_clear()
        self.clipboard_append('\n'.join(self.komennot()))
        self.status.set(t('kopioitu'))

    def ohjaus(self, komento):
        """Lähettää yksittäisen komennon (/start, /stop) samaa reittiä kuin kisan."""
        self.laheta([komento])

    def laheta(self, kom=None):
        ip, portti = self.ip.get().strip(), self.portti.get().strip()
        if not ip or not portti.isdigit():
            self.status.set(t('anna_ip_portti'))
            return
        if not self.salasana.get():
            self.status.set(t('anna_salasana'))
            return
        self._tallenna_asetukset()
        kom = kom or self.komennot()
        self.status.set(t('lahetetaan', ip=ip, portti=portti))
        self._loki('→ ' + '  '.join(kom), 'oma')

        kayttaja, salasana = '', self.salasana.get()

        def tyo():
            self._tulos = http_laheta(ip, portti, kayttaja, salasana, kom)
        self._tulos = None
        threading.Thread(target=tyo, daemon=True).start()
        self._odota_tulosta()

    def _odota_tulosta(self):
        if self._tulos is None:
            self.after(100, self._odota_tulosta)
        else:
            self._valmis(*self._tulos)

    def _valmis(self, ok, viesti):
        self.status.set(viesti)
        self._loki(('✓ ' if ok else '✗ ') + viesti, 'tila' if ok else 'virhe')

    def _tallenna_asetukset(self):
        try:
            with open(ASETUKSET, 'w', encoding='utf-8') as f:
                json.dump({'kieli': kieli.nyk(), 'vieheet': self.viehe_koodi(),
                           'omat': viehekoodi(self.omat), 'tulokset': self.tulos_koodi()}, f)
        except OSError:
            pass

    def _aseta_kieli_alussa(self):
        """Kieli: tallennettu valinta, muuten Windowsin kieli (suomi -> suomi, muuten English)."""
        k = None
        try:
            with open(ASETUKSET, encoding='utf-8') as f:
                k = json.load(f).get('kieli')
        except (OSError, ValueError):
            pass
        kieli.aseta(k if k in kieli.KIELET else kieli.jarjestelman_kieli())

    def vaihda_kieli(self):
        """Vaihtaa kielen lennossa: tallentaa tilan koodeina, rakentaa ikkunan uudelleen."""
        muoto_id = self.muotolista.get(self.muoto.get(), 1)
        viehe, tulos = self.viehe_koodi(), self.tulos_koodi()
        loki = self.loki.dump('1.0', 'end-1c', tag=True, text=True)
        paikka_ind = self.paikka_cb['values'].index(self.paikka.get()) \
            if self.paikka.get() in self.paikka_cb['values'] else 0
        for ikkuna in (self.viehe_ikkuna, getattr(self, 'ohje_ikkuna', None)):
            if ikkuna is not None and ikkuna.winfo_exists():
                ikkuna.destroy()
        kieli.aseta('en' if kieli.nyk() == 'fi' else 'fi')
        for w in self.winfo_children():
            w.destroy()
        self.nappi.clear()
        self._ui()
        self.viehetila.set(viehetila_nimi(viehe))
        self.tulokset.set(tulos_nimi(tulos))
        self.status.set(t('valmis_status'))
        self._viehetila_vaihtui()
        self._suodata()
        self._valitse(self.jarvi)
        if muoto_id in self.muotolista.values():
            self.muoto.set(muoto_nimi(muoto_id))
        arvot = list(self.paikka_cb['values'])
        if arvot:
            self.paikka.set(arvot[min(paikka_ind, len(arvot) - 1)])
        # lokin palautus
        self.loki.configure(state='normal')
        paalla = set()
        for tyyppi, arvo, _ in loki:
            if tyyppi == 'tagon':
                paalla.add(arvo)
            elif tyyppi == 'tagoff':
                paalla.discard(arvo)
            elif tyyppi == 'text':
                self.loki.insert('end', arvo, tuple(paalla))
        self.loki.configure(state='disabled')
        self.loki.see('end')
        self._tallenna_asetukset()

    def _lataa_asetukset(self):
        try:
            with open(ASETUKSET, encoding='utf-8') as f:
                d = json.load(f)
            v = d.get('vieheet')
            v = v if v in VIEHETILA_KOODIT else koodi_nimesta(VIEHETILAT, v)   # vanhat: nimi
            if v:
                self.viehetila.set(viehetila_nimi(v))
            tul = d.get('tulokset')
            tul = tul if tul in TULOS_KOODIT else koodi_nimesta(TULOKSET, tul)
            if tul:
                self.tulokset.set(tulos_nimi(tul))
            koodi = str(d.get('omat', '')).replace('-', '')
            if len(koodi) == VIEHEITA and set(koodi) <= {'0', '1'}:
                self.omat = [c == '1' for c in koodi]
        except (OSError, ValueError):
            pass



if __name__ == '__main__':
    App().mainloop()
