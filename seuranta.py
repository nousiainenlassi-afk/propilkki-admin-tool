"""Hostin seuranta: tila (info.json) ja admin-chatin tapahtumat (refresh.html).

Pro Pilkki 2 -hostin web-palvelu:
  /info.json                  julkinen tila: kisa, aika, pelaajat
  /Admin.html                 web-admin (HTTP Basic), sivulla chat-istunnon id
  /refresh.html?id=<id>       chatin uudet rivit: "1\\n<aika>\\n<uudet rivit html>\\n<taulukko>"
"""
import base64
import html
import json
import queue
import re
import threading
import time
import urllib.error
import urllib.request

from kieli import t


def _pyynto(url, tunnus=None, timeout=6):
    req = urllib.request.Request(url)
    if tunnus is not None:
        req.add_header('Authorization', 'Basic ' + tunnus)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        merkisto = r.headers.get_content_charset() or 'utf-8'
    return data.decode(merkisto, 'replace')


def _tunnus(kayttaja, salasana):
    return base64.b64encode(f'{kayttaja}:{salasana}'.encode('latin-1', 'replace')).decode()


def hae_info(ip, portti):
    """Palauttaa (info-dict, virheviesti). Toinen on None."""
    try:
        return json.loads(_pyynto(f'http://{ip}:{portti}/info.json')), None
    except urllib.error.HTTPError as e:
        return None, t('info_virhe_koodi', code=e.code)
    except json.JSONDecodeError:
        return None, t('info_ei_tilaa')
    except Exception as e:
        return None, str(getattr(e, 'reason', e))


def puhdista_chat(osa):
    """Chatin html-pätkä -> rivit tekstinä."""
    osa = re.sub(r'(?is)</p>\s*<p class="(?:text|ptext|com2)">', ' ', osa)
    osa = re.sub(r'(?i)<br\s*/?>|</p>|</tr>|</div>', '\n', osa)
    osa = re.sub(r'<[^>]+>', '', osa)
    rivit = [html.unescape(r).replace('\xa0', ' ').strip() for r in osa.split('\n')]
    return [r for r in rivit if r]


class ChatSeuranta:
    """Lukee hostin web-admin-chatia taustasäikeessä. Tulokset jonoon (tyyppi, teksti)."""

    def __init__(self, ip, portti, salasana, viive=1.0):
        self.ip, self.portti, self.salasana, self.viive = ip, portti, salasana, viive
        self.jono = queue.Queue()
        self._pysayta = threading.Event()
        self._viime_virhe = None

    def aloita(self):
        threading.Thread(target=self._tyo, daemon=True).start()

    def lopeta(self):
        self._pysayta.set()

    def _virhe(self, teksti):
        if teksti != self._viime_virhe:
            self._viime_virhe = teksti
            self.jono.put(('virhe', teksti))

    def _hae_id(self):
        pohja = f'http://{self.ip}:{self.portti}'
        for kayt in ('', 'admin'):
            tunnus = _tunnus(kayt, self.salasana)
            try:
                sivu = _pyynto(pohja + '/Admin.html', tunnus)
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    continue
                raise
            m = re.search(r'refresh\.html\?id=([0-9A-Za-z]+)', sivu)
            if not m:
                self._virhe(t('chat_ei_id'))
                return None, None
            return m.group(1), tunnus
        self._virhe(t('chat_401'))
        return None, None

    def _tyo(self):
        pohja = f'http://{self.ip}:{self.portti}'
        chat_id = tunnus = None
        while not self._pysayta.is_set():
            try:
                if chat_id is None:
                    chat_id, tunnus = self._hae_id()
                    if chat_id is None:
                        self._pysayta.wait(5)
                        continue
                    self._viime_virhe = None
                    self.jono.put(('tila', t('chat_kaynnissa')))
                vastaus = _pyynto(f'{pohja}/refresh.html?id={chat_id}', tunnus)
                rivit = vastaus.split('\n')
                if rivit[0].strip() != '1':
                    chat_id = None
                    self._pysayta.wait(2)
                    continue
                if len(rivit) > 2:
                    for r in puhdista_chat(rivit[2]):
                        self.jono.put(('chat', r))
                self._pysayta.wait(self.viive)
            except Exception as e:
                self._virhe(t('chat_yhteys', e=getattr(e, 'reason', e)))
                chat_id = None
                self._pysayta.wait(5)
