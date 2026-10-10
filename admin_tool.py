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
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import ttk

from kuvalataus import lataa_jarvikuvat
from seuranta import ChatSeuranta, hae_info
from lakes import (AJAT, JARVET, KESTOT, PELIMUODOT, TULOKSET, VIEHEITA, VIEHELAJIT,
                   VIEHETILAT, VUODENAJAT, sallitut_muodot, viehekoodi)

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
            return True, 'Lähetetty hostille: ' + ', '.join(c.split()[0] for c in komennot)
        except urllib.error.HTTPError as e:
            if e.code == 401 and kayt != kayttajat[-1]:
                continue
            if e.code == 401:
                return False, 'Host hylkäsi tunnukset (401). Tarkista admin-salasana ja käyttäjätunnus.'
            return False, f'Host vastasi virheellä {e.code}.'
        except (urllib.error.URLError, OSError) as e:
            return False, f'Yhteys hostiin {ip}:{portti} epäonnistui: {getattr(e, "reason", e)}'
    return False, 'Lähetys epäonnistui.'


# --------------------------------------------------------------------- sovellus

# Värit samat kuin propilkkitulospalvelu.fi:ssä
BG = '#0a1219'
PANEELI = '#162330'          # kentät, valikot (surface-2)
KORTTI = '#162330'           # vesistökortti
KORTTI_HOVER = '#1b2a38'
VALITTU = '#173345'          # primary 20 % taustan päällä
KOROSTE = '#3ea8d8'          # primary
JAA = '#9ad8ea'
TEKSTI = '#e8eef3'
TEKSTI2 = '#a7b8c6'
HIMMEA = '#71879a'
REUNA = '#233444'
REUNA2 = '#2f4558'
OK = '#4fcf9a'
VIRHE = '#ef7b7b'
DARK_TEXT = '#05121a'


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Pro Pilkki 2 · Admin tool')
        self.geometry('1450x975')
        self.minsize(900, 600)

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
        self.status = tk.StringVar(value='Valmis.')
        self.maara = tk.StringVar()
        self.nappi = {}
        self.kuvat = {}
        self.omat = [False] * VIEHEITA
        self.viehetila = tk.StringVar(value=VIEHETILAT[0][1])
        self.tulokset = tk.StringVar(value=dict(TULOKSET)['8'])
        self.viehe_kuvat = {}
        self.viehe_ikkuna = None
        self.seuraa_chat = tk.BooleanVar(value=True)
        self._info = None            # viimeisin info.json
        self._info_virhe = None
        self._info_tulos = None
        self._info_kaynnissa = False
        self._tikki = 0
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
            return 'Kisa käynnissä, aikaa jäljellä', a, OK
        m = re.search(r'(\d+:\d\d)', a)
        if m and re.search(r'(?i)start', a):
            return 'Lobbyssa, seuraava kisa alkaa', m.group(1), KOROSTE
        if a:
            return 'Lobbyssa', a, KOROSTE
        return 'Lobbyssa, odottaa seuraavan kisan alkua', '–', KOROSTE

    def _nayta_info(self, valmis):
        i = self._info
        if not valmis:
            piste, tila, teksti = HIMMEA, 'Ei yhteyttä', 'Anna hostin IP ja portti'
        elif i is None and self._info_virhe:
            piste, tila, teksti = VIRHE, 'Ei yhteyttä', self._info_virhe
        elif i is None:
            piste, tila, teksti = HIMMEA, 'Yhdistetään…', ''
        else:
            piste, tila, teksti = OK, 'Yhteys OK', i.get('Host', '')
        self.sk_piste.configure(fg=piste)
        self.sk_tila.configure(text=tila)
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
        rivi = f"Pelaajat {i.get('Players', len(pelaajat))} / {i.get('PlayersMax', '?')}"
        if jonossa:
            rivi += f' (jonossa {jonossa})'
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
                self._loki('Chat-seuranta käynnistyy…', 'tila')
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
        self._suodata()

    # ---- ulkoasu
    def _teema(self):
        self.configure(bg=BG)
        st = ttk.Style(self)
        st.theme_use('clam')
        st.configure('.', background=BG, foreground=TEKSTI, fieldbackground=PANEELI,
                     bordercolor=REUNA2, lightcolor=REUNA2, darkcolor=REUNA2,
                     troughcolor=BG, font=('Segoe UI', 10))
        st.configure('TFrame', background=BG)
        st.configure('TLabel', background=BG, foreground=TEKSTI2)
        st.configure('TLabelframe', background=BG, bordercolor=REUNA, relief='solid')
        st.configure('TLabelframe.Label', background=BG, foreground=TEKSTI,
                     font=('Segoe UI', 10, 'bold'))
        st.configure('TRadiobutton', background=BG, foreground=TEKSTI, indicatorcolor=PANEELI)
        st.configure('TCheckbutton', background=BG, foreground=TEKSTI, indicatorcolor=PANEELI)
        st.map('TRadiobutton', background=[('active', BG)], indicatorcolor=[('selected', KOROSTE)],
               foreground=[('active', '#ffffff')])
        st.map('TCheckbutton', background=[('active', BG)], indicatorcolor=[('selected', KOROSTE)],
               foreground=[('active', '#ffffff')])
        st.configure('TEntry', fieldbackground=PANEELI, foreground=TEKSTI,
                     insertcolor=TEKSTI, padding=5)
        st.configure('TCombobox', fieldbackground=PANEELI, background=KORTTI,
                     foreground=TEKSTI, arrowcolor=TEKSTI2, padding=5)
        st.map('TCombobox', fieldbackground=[('readonly', PANEELI), ('disabled', BG)],
               foreground=[('disabled', HIMMEA)], selectbackground=[('readonly', PANEELI)],
               selectforeground=[('readonly', TEKSTI)])
        st.configure('TButton', background=PANEELI, foreground=TEKSTI, padding=8, borderwidth=1)
        st.map('TButton', background=[('active', KORTTI_HOVER)],
               foreground=[('disabled', HIMMEA)])
        st.configure('Laheta.TButton', background='#5ab7e1', foreground=DARK_TEXT,
                     font=('Segoe UI', 10, 'bold'), bordercolor='#5ab7e1')
        st.map('Laheta.TButton', background=[('active', '#7cc8ec')])
        st.configure('Start.TButton', background=OK, foreground=DARK_TEXT,
                     font=('Segoe UI', 10, 'bold'), bordercolor=OK)
        st.map('Start.TButton', background=[('active', '#6fdcb0')])
        st.configure('Stop.TButton', background=VIRHE, foreground=DARK_TEXT,
                     font=('Segoe UI', 10, 'bold'), bordercolor=VIRHE)
        st.map('Stop.TButton', background=[('active', '#f39a9a')])
        st.configure('Vertical.TScrollbar', background=REUNA2, troughcolor=BG,
                     arrowcolor=TEKSTI2, bordercolor=BG)
        self.option_add('*TCombobox*Listbox.background', PANEELI)
        self.option_add('*TCombobox*Listbox.foreground', TEKSTI)
        self.option_add('*TCombobox*Listbox.selectBackground', KOROSTE)
        self.option_add('*TCombobox*Listbox.selectForeground', DARK_TEXT)
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
        pad = {'padx': 8, 'pady': 2}
        vasen = ttk.Frame(self)
        vasen.pack(side='left', fill='both', expand=True, padx=8, pady=8)
        sk = ttk.Frame(self, width=380)
        sk.pack(side='right', fill='y', padx=(0, 8), pady=8)
        sk.pack_propagate(False)
        ttk.Label(sk, text='SEURANTA', foreground=KOROSTE,
                  font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        ttk.Label(sk, text='Hosti nyt', foreground=TEKSTI,
                  font=('Segoe UI', 24, 'bold')).pack(anchor='w', pady=(0, 6))
        kortti = tk.Frame(sk, bg=KORTTI, highlightthickness=1, highlightbackground=REUNA)
        kortti.pack(fill='x')

        def etiketti(vanhempi, **kw):
            kw.setdefault('bg', KORTTI)
            kw.setdefault('fg', TEKSTI)
            kw.setdefault('anchor', 'w')
            kw.setdefault('justify', 'left')
            return tk.Label(vanhempi, **kw)

        ylos = tk.Frame(kortti, bg=KORTTI)
        ylos.pack(fill='x', padx=10, pady=(8, 0))
        self.sk_piste = etiketti(ylos, text='●', fg=HIMMEA, font=('Segoe UI', 12))
        self.sk_piste.pack(side='left')
        self.sk_tila = etiketti(ylos, text='Ei yhteyttä', fg=TEKSTI2, font=('Segoe UI', 10, 'bold'))
        self.sk_tila.pack(side='left', padx=(4, 0))
        self.sk_host = etiketti(kortti, text='Anna hostin IP ja portti', font=('Segoe UI', 13, 'bold'),
                                wraplength=340)
        self.sk_host.pack(fill='x', padx=10)
        self.sk_versio = etiketti(kortti, text='', fg=HIMMEA, font=('Segoe UI', 9))
        self.sk_versio.pack(fill='x', padx=10)
        keski = tk.Frame(kortti, bg=KORTTI)
        keski.pack(fill='x', padx=10, pady=8)
        self.sk_kuva = tk.Label(keski, bg=KORTTI)
        self.sk_kuva.pack(side='left')
        tied = tk.Frame(keski, bg=KORTTI)
        tied.pack(side='left', fill='x', expand=True, padx=(10, 0))
        self.sk_jarvi = etiketti(tied, text='', font=('Segoe UI', 12, 'bold'), wraplength=220)
        self.sk_jarvi.pack(fill='x')
        self.sk_peli = etiketti(tied, text='', fg=TEKSTI2, wraplength=220)
        self.sk_peli.pack(fill='x')
        self.sk_aikaotsikko = etiketti(tied, text='', fg=HIMMEA, font=('Segoe UI', 9),
                                       wraplength=220)
        self.sk_aikaotsikko.pack(fill='x', pady=(6, 0))
        self.sk_aika = etiketti(tied, text='', fg=OK, font=('Segoe UI', 24, 'bold'))
        self.sk_aika.pack(fill='x')
        self.sk_kuvaus = etiketti(kortti, text='', fg=TEKSTI2, wraplength=340)
        self.sk_kuvaus.pack(fill='x', padx=10)
        self.sk_pelaajat = etiketti(kortti, text='', fg=TEKSTI2, wraplength=340)
        self.sk_pelaajat.pack(fill='x', padx=10, pady=(4, 10))

        ttk.Label(sk, text='HOSTIN LOKI', foreground=KOROSTE,
                  font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(12, 2))
        ttk.Checkbutton(sk, text='Seuraa hostin chattia (käyttää admin-salasanaa)',
                        variable=self.seuraa_chat).pack(anchor='w', pady=(0, 4))
        lokiriv = ttk.Frame(sk)
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

        oikea = ttk.Frame(self, width=340)
        oikea.pack(side='right', fill='y', padx=8, pady=8)

        ttk.Label(vasen, text='TYÖKALUT · HOSTIN OHJAUS', foreground=KOROSTE,
                  font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        ttk.Label(vasen, text='Admin tool', foreground=TEKSTI,
                  font=('Segoe UI', 24, 'bold')).pack(anchor='w')
        ttk.Label(vasen, text='Valitse vesistö ja asetukset ja lähetä ne hostille. '
                  'Vesistöjen pelimuodot ja aloituspaikat ovat samat kuin pelissä.',
                  foreground=TEKSTI2, wraplength=640).pack(anchor='w', pady=(0, 6))
        ttk.Entry(vasen, textvariable=self.haku).pack(fill='x', pady=4)
        ttk.Label(vasen, textvariable=self.maara, foreground=HIMMEA).pack(anchor='w')
        kehys = ttk.Frame(vasen)
        kehys.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(kehys, highlightthickness=0, bg=BG)
        sb = ttk.Scrollbar(kehys, orient='vertical', command=self.canvas.yview)
        self.ruudukko = ttk.Frame(self.canvas)
        self.ruudukko.bind('<Configure>', lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox('all')))
        ikkuna_id = self.canvas.create_window((0, 0), window=self.ruudukko, anchor='nw')
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(ikkuna_id, width=e.width))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        # hiiren rulla vierittää aina vain vesistölistaa, ei vaihda muita asetuksia
        for tagi in ('all', 'TCombobox', 'Text'):
            self.bind_class(tagi, '<MouseWheel>', self._rulla)
        self._rakenna_ruudukko(JARVET)

        # oikea paneeli
        def ryhma(otsikko, arvot, var):
            f = ttk.LabelFrame(oikea, text=otsikko)
            f.pack(fill='x', **pad)
            for k, nimi in arvot.items():
                ttk.Radiobutton(f, text=nimi, value=k, variable=var).pack(
                    side='left', padx=6, pady=2)
            return f

        ryhma('Vuodenaika', VUODENAJAT, self.vuodenaika)
        self.aika_kehys = ryhma('Vuorokaudenaika', AJAT, self.aika)
        ryhma('Kesto (min)', {k: str(v) for k, v in KESTOT.items()}, self.kesto)

        f = ttk.LabelFrame(oikea, text='Pelimuoto')
        f.pack(fill='x', **pad)
        self.muoto_cb = ttk.Combobox(f, textvariable=self.muoto, state='readonly')
        self.muoto_cb.pack(fill='x', padx=6, pady=4)

        f = ttk.LabelFrame(oikea, text='Aloituspaikka')
        f.pack(fill='x', **pad)
        self.paikka_cb = ttk.Combobox(f, textvariable=self.paikka, state='readonly')
        self.paikka_cb.pack(fill='x', padx=6, pady=4)

        f = ttk.LabelFrame(oikea, text='Vieheet ja väliajat')
        f.pack(fill='x', **pad)
        ttk.Label(f, text='Vieheet').pack(anchor='w', padx=6)
        self.viehe_cb = ttk.Combobox(f, textvariable=self.viehetila, state='readonly',
                                     values=[t for _, t in VIEHETILAT])
        self.viehe_cb.pack(fill='x', padx=6, pady=(0, 2))
        self.viehe_valinta = ttk.Button(f, text='Valitse vieheet…', command=self.avaa_vieheet)
        self.viehe_valinta.pack(fill='x', padx=6, pady=(0, 4))
        ttk.Label(f, text='Väliaikatulokset kisan aikana').pack(anchor='w', padx=6)
        ttk.Combobox(f, textvariable=self.tulokset, state='readonly',
                     values=[t for _, t in TULOKSET]).pack(fill='x', padx=6, pady=(0, 4))
        ttk.Button(f, text='Lähetä vieheet ja väliajat', command=self.laheta_asetukset).pack(
            fill='x', padx=6, pady=(0, 6))

        f = ttk.LabelFrame(oikea, text='Hosti (ohjattava)')
        f.pack(fill='x', **pad)
        rivi = ttk.Frame(f)
        rivi.pack(fill='x', padx=6, pady=(4, 0))
        ip_k = ttk.Frame(rivi)
        ip_k.pack(side='left', fill='x', expand=True)
        ttk.Label(ip_k, text='IP / osoite').pack(anchor='w')
        ttk.Entry(ip_k, textvariable=self.ip).pack(fill='x')
        pt_k = ttk.Frame(rivi)
        pt_k.pack(side='left', padx=(6, 0))
        ttk.Label(pt_k, text='Portti').pack(anchor='w')
        ttk.Entry(pt_k, textvariable=self.portti, width=7).pack()
        ttk.Label(f, text='Admin-salasana (ei tallenneta levylle)').pack(anchor='w', padx=6)
        ttk.Entry(f, textvariable=self.salasana, show='•').pack(fill='x', padx=6, pady=(0, 4))
        ah = ttk.Frame(f)
        ah.pack(fill='x', padx=6, pady=(0, 6))
        ttk.Button(ah, text='Autohost ON', command=lambda: self.ohjaus('/autohost on')).pack(
            side='left', fill='x', expand=True)
        ttk.Button(ah, text='Autohost OFF', command=lambda: self.ohjaus('/autohost off')).pack(
            side='left', fill='x', expand=True, padx=(6, 0))
        ttk.Label(oikea, text='Komennot').pack(anchor='w', padx=8)
        self.esikatselu = tk.Text(oikea, height=6, width=40, state='disabled', wrap='char',
                                  font=('Consolas', 10), bg='#070d13', fg=JAA,
                                  relief='flat', padx=8, pady=6, highlightthickness=1,
                                  highlightbackground=REUNA2, highlightcolor=REUNA2)
        self.esikatselu.pack(fill='x', padx=8)

        rivi = ttk.Frame(oikea)
        rivi.pack(fill='x', padx=8, pady=8)
        ttk.Button(rivi, text='Lähetä hostille', style='Laheta.TButton', command=self.laheta).pack(
            side='left', fill='x', expand=True)
        ttk.Button(rivi, text='Kopioi', command=self.kopioi).pack(side='left', padx=(6, 0))
        ohj = ttk.Frame(oikea)
        ohj.pack(fill='x', padx=8, pady=(0, 6))
        ttk.Button(ohj, text='▶ Käynnistä (/start)', style='Start.TButton',
                   command=lambda: self.ohjaus('/start')).pack(
            side='left', fill='x', expand=True)
        ttk.Button(ohj, text='■ Pysäytä (/stop)', style='Stop.TButton',
                   command=lambda: self.ohjaus('/stop')).pack(
            side='left', fill='x', expand=True, padx=(6, 0))
        ttk.Label(oikea, textvariable=self.status, wraplength=320,
                  foreground=HIMMEA).pack(anchor='w', padx=8)

    def _rakenna_ruudukko(self, jarvet):
        for w in self.ruudukko.winfo_children():
            w.destroy()
        self.nappi.clear()
        sarakkeita = 4
        for c in range(sarakkeita):
            self.ruudukko.columnconfigure(c, weight=1, uniform='v')
        for i, j in enumerate(jarvet):
            teksti = j['nimi']
            if j['paikat']:
                teksti += f"\n{len(j['paikat'])} aloituspaikkaa"
            else:
                teksti += '\n '
            b = tk.Button(self.ruudukko, text=teksti, image=self._kuva(j), compound='top',
                          relief='flat', bg=KORTTI, fg=TEKSTI, activebackground=KORTTI_HOVER,
                          activeforeground='#ffffff', bd=0, wraplength=150, pady=6,
                          highlightthickness=1, highlightbackground=REUNA,
                          highlightcolor=KOROSTE,
                          font=('Segoe UI', 10), cursor='hand2',
                          command=lambda x=j: self._valitse(x))
            b.bind('<Enter>', lambda e, x=j: self._hover(x, True))
            b.bind('<Leave>', lambda e, x=j: self._hover(x, False))
            b.grid(row=i // sarakkeita, column=i % sarakkeita, padx=3, pady=3, sticky='nsew')
            self.nappi[j['koodi']] = b
        self._korosta()

    # ---- vieheet ja väliajat
    def viehe_komento(self):
        koodi = next(k for k, t in VIEHETILAT if t == self.viehetila.get())
        if koodi == 'custom':
            return '/lures custom ' + viehekoodi(self.omat)
        return '/lures ' + koodi

    def tulos_komento(self):
        return '/results ' + next(k for k, t in TULOKSET if t == self.tulokset.get())

    def _viehetila_vaihtui(self):
        oma = self.viehetila.get() == VIEHETILAT[3][1]
        self.viehe_valinta.configure(state='normal' if oma else 'disabled')
        self._paivita()

    def laheta_asetukset(self):
        if self.viehetila.get() == VIEHETILAT[3][1] and not any(self.omat):
            self.status.set('Oma valinta on tyhjä. Valitse vähintään yksi viehe.')
            return
        self.laheta([self.tulos_komento(), self.viehe_komento()])

    def avaa_vieheet(self):
        if self.viehe_ikkuna and self.viehe_ikkuna.winfo_exists():
            self.viehe_ikkuna.lift()
            return
        w = self.viehe_ikkuna = tk.Toplevel(self)
        w.title('Valitse vieheet')
        w.configure(bg=BG)
        w.transient(self)
        self.viehe_napit = {}
        self.laji_otsikot = {}
        ylos = ttk.Frame(w)
        ylos.pack(fill='x', padx=10, pady=(8, 0))
        self.viehe_yht = tk.StringVar()
        ttk.Label(ylos, textvariable=self.viehe_yht, foreground=KOROSTE,
                  font=('Segoe UI', 11, 'bold')).pack(side='left')
        ttk.Button(ylos, text='Valmis', command=w.destroy).pack(side='right')
        ttk.Button(ylos, text='Tyhjennä kaikki',
                   command=lambda: self._aseta_vieheet(range(VIEHEITA), False)).pack(
            side='right', padx=6)
        ttk.Button(ylos, text='Valitse kaikki',
                   command=lambda: self._aseta_vieheet(range(VIEHEITA), True)).pack(side='right')
        rivit = [ttk.Frame(w) for _ in range(3)]
        for r in rivit:
            r.pack(fill='x', padx=10, pady=4)
        paikat = [rivit[0], rivit[1], rivit[2], rivit[2]]
        for (nimi, alku, maara, kuva), vanhempi in zip(VIEHELAJIT, paikat):
            laatikko = ttk.LabelFrame(vanhempi, text=nimi)
            laatikko.pack(side='left', fill='x', expand=(maara == 16), padx=(0, 8))
            kp = ttk.Frame(laatikko)
            kp.pack(fill='x', padx=6)
            otsikko = tk.StringVar()
            self.laji_otsikot[nimi] = otsikko
            ttk.Label(kp, textvariable=otsikko, foreground=HIMMEA).pack(side='left')
            ttk.Button(kp, text='Tyhjennä', width=9, command=lambda a=alku, m=maara:
                       self._aseta_vieheet(range(a, a + m), False)).pack(side='right')
            ttk.Button(kp, text='Valitse kaikki', width=13, command=lambda a=alku, m=maara:
                       self._aseta_vieheet(range(a, a + m), True)).pack(side='right', padx=4)
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
        self.viehe_yht.set(f'Valittu {sum(self.omat)} / {VIEHEITA} viehettä')
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
            self.maara.set(f'{len(ajalla)} yövesistöä' if yo else f'{len(ajalla)} vesistöä')
        self._rakenna_ruudukko(nakyvat)

    def _aika_vaihtui(self):
        """Yöllä näytetään vain yövesistöt; ei-yövesistö vaihtuu ensimmäiseen yövesistöön."""
        if self.aika.get() == 4 and not self.jarvi['yo']:
            vanha = self.jarvi['nimi']
            uusi = next(j for j in JARVET if j['yo'])
            self.status.set(f'{vanha}: ei yöpelejä, vesistöksi vaihtui {uusi["nimi"]}.')
            self.jarvi = uusi
            self._paivita_valinnat()
        self._suodata()
        self._korosta()

    def _korosta(self):
        for koodi, b in self.nappi.items():
            valittu = koodi == self.jarvi['koodi']
            b.configure(bg=VALITTU if valittu else KORTTI,
                        highlightbackground=KOROSTE if valittu else REUNA,
                        font=('Segoe UI', 10, 'bold' if valittu else 'normal'))

    def _hover(self, jarvi, sisalla):
        b = self.nappi.get(jarvi['koodi'])
        if b and jarvi['koodi'] != self.jarvi['koodi']:
            b.configure(bg=KORTTI_HOVER if sisalla else KORTTI)

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
        return 'break'

    def _paivita_valinnat(self):
        j = self.jarvi
        muodot = sallitut_muodot(j, self.aika.get())
        self.muotolista = {PELIMUODOT[m]: m for m in muodot}
        self.muoto_cb['values'] = list(self.muotolista)
        if self.muoto.get() not in self.muotolista:
            self.muoto.set(next(iter(self.muotolista)))
        paikat = j['paikat'] or ['Ainoa paikka']
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
        uusi = [PELIMUODOT[m] for m in sallitut_muodot(self.jarvi, self.aika.get())]
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
        self.status.set('Komennot kopioitu leikepöydälle (salasana mukana).')

    def ohjaus(self, komento):
        """Lähettää yksittäisen komennon (/start, /stop) samaa reittiä kuin kisan."""
        self.laheta([komento])

    def laheta(self, kom=None):
        ip, portti = self.ip.get().strip(), self.portti.get().strip()
        if not ip or not portti.isdigit():
            self.status.set('Anna hostin IP ja portti (numero).')
            return
        if not self.salasana.get():
            self.status.set('Anna admin-salasana.')
            return
        self._tallenna_asetukset()
        kom = kom or self.komennot()
        self.status.set(f'Lähetetään hostille {ip}:{portti} ...')
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
                json.dump({'vieheet': self.viehetila.get(), 'omat': viehekoodi(self.omat),
                           'tulokset': self.tulokset.get()}, f)
        except OSError:
            pass

    def _lataa_asetukset(self):
        try:
            with open(ASETUKSET, encoding='utf-8') as f:
                d = json.load(f)
            if d.get('vieheet') in [t for _, t in VIEHETILAT]:
                self.viehetila.set(d['vieheet'])
            if d.get('tulokset') in [t for _, t in TULOKSET]:
                self.tulokset.set(d['tulokset'])
            koodi = str(d.get('omat', '')).replace('-', '')
            if len(koodi) == VIEHEITA and set(koodi) <= {'0', '1'}:
                self.omat = [c == '1' for c in koodi]
        except (OSError, ValueError):
            pass



if __name__ == '__main__':
    App().mainloop()
