"""Käyttöliittymän kielet (suomi / English).

Englanninkielinen sanasto on otettu pelistä (ProPilkki2.exe): vuodenajat,
vuorokaudenajat, pelimuodot ("Game type"), "Start place", "Competition time left",
"Game break" jne. Lisää kieli lisäämällä sanakirja TEKSTIT-rakenteeseen.
"""
import ctypes

_nyk = 'fi'
KIELET = ('fi', 'en')


def jarjestelman_kieli():
    """Windowsin käyttöliittymäkieli: suomi -> 'fi', muuten 'en'."""
    try:
        return 'fi' if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x0B else 'en'
    except Exception:
        return 'fi'


def aseta(kieli):
    global _nyk
    _nyk = kieli if kieli in KIELET else 'fi'


def nyk():
    return _nyk


def t(avain, **kw):
    s = TEKSTIT.get(_nyk, {}).get(avain)
    if s is None:
        s = TEKSTIT['fi'][avain]
    return s.format(**kw) if kw else s


# ------------------------------------------------------------------ pelin sanasto
PELIMUODOT = {
    'fi': {
        1: 'Normaali', 2: 'Kappalemäärä', 3: 'Kaikki lajit', 4: 'Kaikki lajit, kappalemäärä',
        5: 'Suurin kala', 6: 'Eniten lajeja', 7: 'Kirjo ja taimen', 8: 'Kirjo ja taimen, kappalemäärä',
        9: 'Vain pasuri', 10: 'Vain pasuri, kappalemäärä', 11: 'Vain made', 12: 'Vain made, kappalemäärä',
        13: 'Vain kiiski', 14: 'Vain kiiski, kappalemäärä', 15: 'Vain ahven', 16: 'Vain ahven, kappalemäärä',
        17: 'Vain hauki', 18: 'Suurin hauki', 19: 'Vain kuha', 20: 'Suurin kuha',
        21: 'Vain särkikalat', 22: 'Vain särkikalat, kappalemäärä', 23: 'Suurin särkikala',
        24: 'Kolme suurinta kalaa', 25: 'Viisi suurinta kalaa', 26: 'Vain siika',
        27: 'Vain siika, kappalemäärä', 28: 'Ruutupilkki', 29: 'Ruutupilkki, kappalemäärä',
    },
    'en': {   # pelin omat nimet
        1: 'Normal', 2: 'Quantity', 3: 'All species', 4: 'All species, quantity',
        5: 'Biggest fish', 6: 'Most species', 7: 'Only trout', 8: 'Only trout, quantity',
        9: 'Only silver bream', 10: 'Only silver bream, quantity', 11: 'Only burbot',
        12: 'Only burbot, quantity', 13: 'Only ruffe', 14: 'Only ruffe, quantity',
        15: 'Only perch', 16: 'Only perch, quantity', 17: 'Only pike', 18: 'Biggest pike',
        19: 'Only zander', 20: 'Biggest zander', 21: 'Carp family fish',
        22: 'Carp family fish, quantity', 23: 'Biggest carp family fish',
        24: 'Three biggest fish', 25: 'Five biggest fish', 26: 'Only whitefish',
        27: 'Only whitefish, quantity', 28: 'Area game', 29: 'Area game, quantity',
    },
}
VUODENAJAT = {'fi': {1: 'Syksy', 2: 'Talvi', 3: 'Kevät'},
              'en': {1: 'Autumn', 2: 'Winter', 3: 'Spring'}}
AJAT = {'fi': {1: 'Aamu', 2: 'Päivä', 3: 'Ilta', 4: 'Yö'},
        'en': {1: 'Morning', 2: 'Afternoon', 3: 'Evening', 4: 'Night'}}
VIEHELAJIT = {'fi': ['Pystyt', 'Tasurit', 'Muut', 'Morrit'],
              'en': ['Vertical', 'Horizontal', 'Other', 'Mormyshkas']}
VIEHETILA_KOODIT = ['all', 'off', 'on', 'custom']
VIEHETILAT = {'fi': {'all': 'Kaikki', 'off': 'Perus', 'on': 'Perus + 6 sattumanvaraista',
                     'custom': 'Oma valinta'},
              'en': {'all': 'All lures', 'off': 'Basic lures', 'on': 'Basic + 6 random lures',
                     'custom': 'Custom lures'}}
TULOS_KOODIT = ['off', '2', '5', '8', '10', '15']
TULOKSET = {'fi': {'off': 'Ei väliaikatuloksia', '2': '2 min välein', '5': '5 min välein',
                   '8': '8 min välein', '10': '10 min välein', '15': '15 min välein'},
            'en': {'off': 'No intermediate results', '2': 'Every 2 min', '5': 'Every 5 min',
                   '8': 'Every 8 min', '10': 'Every 10 min', '15': 'Every 15 min'}}


def muoto_nimi(i):
    return PELIMUODOT[_nyk][i]


def vuodenaika_nimi(i):
    return VUODENAJAT[_nyk][i]


def aika_nimi(i):
    return AJAT[_nyk][i]


def viehelaji_nimi(i):
    return VIEHELAJIT[_nyk][i]


def viehetila_nimi(koodi):
    return VIEHETILAT[_nyk][koodi]


def tulos_nimi(koodi):
    return TULOKSET[_nyk][koodi]


def koodi_nimesta(sanakirjat, nimi):
    """Etsii koodin minkä tahansa kielen nimellä (vanhat tallennetut arvot)."""
    for kieli in sanakirjat.values():
        for koodi, n in kieli.items():
            if n == nimi:
                return koodi
    return None


# ------------------------------------------------------------------ käyttöliittymä
TEKSTIT = {
    'fi': {
        'ylaotsikko': 'TYÖKALUT · HOSTIN OHJAUS',
        'alaotsikko': 'Valitse vesistö ja asetukset ja lähetä ne hostille. '
                      'Vesistöjen pelimuodot ja aloituspaikat ovat samat kuin pelissä.',
        'ohje_nappi': '?  Ohje', 'kieli_nappi': 'English',
        'jarvia': '{n} vesistöä', 'yojarvia': '{n} yövesistöä',
        'aloituspaikkoja': '{n} aloituspaikkaa',
        'vuodenaika': 'Vuodenaika', 'vuorokaudenaika': 'Vuorokaudenaika', 'kesto': 'Kesto (min)',
        'pelimuoto': 'Pelimuoto', 'aloituspaikka': 'Aloituspaikka', 'ainoa_paikka': 'Ainoa paikka',
        'viehe_ryhma': 'Vieheet ja väliajat', 'vieheet': 'Vieheet',
        'valitse_vieheet': 'Valitse vieheet…', 'valiajat': 'Väliaikatulokset kisan aikana',
        'laheta_asetukset': 'Lähetä vieheet ja väliajat',
        'hosti_ryhma': 'Hosti (ohjattava)', 'ip': 'IP / osoite', 'portti': 'Portti',
        'salasana': 'Admin-salasana (ei tallenneta levylle)',
        'komennot': 'Komennot', 'laheta': 'Lähetä hostille', 'kopioi': 'Kopioi',
        'kaynnista': '▶ Käynnistä (/start)', 'pysayta': '■ Pysäytä (/stop)',
        'valmis_status': 'Valmis.',
        'seuranta': 'SEURANTA', 'hosti_nyt': 'Hosti nyt', 'ei_yhteytta': 'Ei yhteyttä',
        'yhteys_ok': 'Yhteys OK', 'yhdistetaan': 'Yhdistetään…',
        'anna_ip': 'Anna hostin IP ja portti', 'hostin_loki': 'HOSTIN LOKI',
        'seuraa_chat': 'Seuraa hostin chattia (käyttää admin-salasanaa)',
        'tila_kaynnissa': 'Kisa käynnissä, aikaa jäljellä',
        'tila_lobby_alkaa': 'Lobbyssa, seuraava kisa alkaa', 'tila_lobby': 'Lobbyssa',
        'tila_lobby_odottaa': 'Lobbyssa, odottaa seuraavan kisan alkua',
        'pelaajat': 'Pelaajat {a} / {b}', 'jonossa': ' (jonossa {n})',
        'chat_kaynnistyy': 'Chat-seuranta käynnistyy…', 'chat_kaynnissa': 'Chat-seuranta käynnissä.',
        'chat_401': 'Admin-salasana hylättiin (401), chatia ei voi seurata.',
        'chat_ei_id': 'Chat-istunnon tunnusta ei löytynyt Admin.html-sivulta.',
        'chat_yhteys': 'Chat-yhteys: {e}',
        'info_virhe_koodi': 'Host vastasi {code}',
        'info_ei_tilaa': 'Host ei palauttanut tilatietoa (info.json)',
        'lahetetty': 'Lähetetty hostille: {k}',
        'http401': 'Host hylkäsi tunnukset (401). Tarkista admin-salasana.',
        'http_virhe': 'Host vastasi virheellä {code}.',
        'yhteys_epaonnistui': 'Yhteys hostiin {ip}:{portti} epäonnistui: {e}',
        'lahetys_epaonnistui': 'Lähetys epäonnistui.',
        'anna_ip_portti': 'Anna hostin IP ja portti (numero).',
        'anna_salasana': 'Anna admin-salasana.',
        'lahetetaan': 'Lähetetään hostille {ip}:{portti} ...',
        'kopioitu': 'Komennot kopioitu leikepöydälle.',
        'oma_tyhja': 'Oma valinta on tyhjä. Valitse vähintään yksi viehe.',
        'ei_yopelia': '{vanha}: ei yöpelejä, vesistöksi vaihtui {uusi}.',
        'viehe_ikkuna': 'Valitse vieheet', 'valmis_nappi': 'Valmis',
        'tyhjenna_kaikki': 'Tyhjennä kaikki', 'valitse_kaikki': 'Valitse kaikki',
        'tyhjenna': 'Tyhjennä', 'valittu_vieheita': 'Valittu {n} / {m} viehettä',
        'ohje_ikkuna': 'Ohje · Admin tool', 'ohje_otsikko': 'Ohje', 'versio': 'versio {v}',
        'avaa_github': 'Avaa GitHub-sivu',
    },
    'en': {
        'ylaotsikko': 'TOOLS · HOST CONTROL',
        'alaotsikko': 'Select the lake and settings and send them to the host. '
                      'Game types and start places are the same as in the game.',
        'ohje_nappi': '?  Help', 'kieli_nappi': 'Suomi',
        'jarvia': '{n} lakes', 'yojarvia': '{n} night lakes',
        'aloituspaikkoja': '{n} start places',
        'vuodenaika': 'Season', 'vuorokaudenaika': 'Day time', 'kesto': 'Game duration (min)',
        'pelimuoto': 'Game type', 'aloituspaikka': 'Start place', 'ainoa_paikka': 'Only place',
        'viehe_ryhma': 'Lures and results', 'vieheet': 'Lures',
        'valitse_vieheet': 'Select lures…', 'valiajat': 'Intermediate results during the game',
        'laheta_asetukset': 'Send lures and results',
        'hosti_ryhma': 'Host (controlled)', 'ip': 'IP / address', 'portti': 'Port',
        'salasana': 'Admin password (not saved to disk)',
        'komennot': 'Commands', 'laheta': 'Send to host', 'kopioi': 'Copy',
        'kaynnista': '▶ Start (/start)', 'pysayta': '■ Stop (/stop)',
        'valmis_status': 'Ready.',
        'seuranta': 'MONITORING', 'hosti_nyt': 'Host now', 'ei_yhteytta': 'No connection',
        'yhteys_ok': 'Connection OK', 'yhdistetaan': 'Connecting…',
        'anna_ip': 'Enter the host IP and port', 'hostin_loki': 'HOST LOG',
        'seuraa_chat': 'Follow host chat (uses the admin password)',
        'tila_kaynnissa': 'Competition time left',
        'tila_lobby_alkaa': 'Game break, next game starts in', 'tila_lobby': 'Game break',
        'tila_lobby_odottaa': 'Game break, waiting for the next game to start',
        'pelaajat': 'Players {a} / {b}', 'jonossa': ' ({n} waiting)',
        'chat_kaynnistyy': 'Chat monitoring starting…', 'chat_kaynnissa': 'Chat monitoring active.',
        'chat_401': 'Admin password was rejected (401), cannot follow the chat.',
        'chat_ei_id': 'Chat session id was not found on the Admin.html page.',
        'chat_yhteys': 'Chat connection: {e}',
        'info_virhe_koodi': 'Host replied {code}',
        'info_ei_tilaa': 'Host did not return status data (info.json)',
        'lahetetty': 'Sent to host: {k}',
        'http401': 'Host rejected the credentials (401). Check the admin password.',
        'http_virhe': 'Host replied with error {code}.',
        'yhteys_epaonnistui': 'Connection to host {ip}:{portti} failed: {e}',
        'lahetys_epaonnistui': 'Sending failed.',
        'anna_ip_portti': 'Enter the host IP and port (a number).',
        'anna_salasana': 'Enter the admin password.',
        'lahetetaan': 'Sending to host {ip}:{portti} ...',
        'kopioitu': 'Commands copied to the clipboard.',
        'oma_tyhja': 'Custom lure selection is empty. Select at least one lure.',
        'ei_yopelia': '{vanha}: no night games, lake changed to {uusi}.',
        'viehe_ikkuna': 'Select lures', 'valmis_nappi': 'Done',
        'tyhjenna_kaikki': 'Clear all', 'valitse_kaikki': 'Select all',
        'tyhjenna': 'Clear', 'valittu_vieheita': 'Selected {n} / {m} lures',
        'ohje_ikkuna': 'Help · Admin tool', 'ohje_otsikko': 'Help', 'versio': 'version {v}',
        'avaa_github': 'Open GitHub page',
    },
}

# ------------------------------------------------------------------ ohjeteksti
OHJE = {
    'fi': [
        ('h', 'Pikaohje'),
        ('p', '1. Kirjoita hostin IP-osoite ja portti. Portti on sama, jolla hostin info-sivu '
              'aukeaa selaimessa (esim. http://osoite:4500/).'),
        ('p', '2. Kirjoita admin-salasana. Silmäpainike näyttää salasanan niin kauan kuin pidät '
              'hiiren painiketta pohjassa. Salasanaa ei tallenneta levylle.'),
        ('p', '3. Valitse vesistö, vuodenaika, vuorokaudenaika, kesto, pelimuoto ja aloituspaikka.'),
        ('p', '4. Paina Lähetä hostille. Komennot näkyvät Komennot-ruudussa ennen lähetystä, ja '
              'Kopioi vie ne leikepöydälle.'),
        ('h', 'Painikkeet'),
        ('p', 'Lähetä hostille: lähettää /lake- ja /game-komennot, eli seuraavan kisan vesistön ja '
              'pelimuodon. Ne tulevat voimaan seuraavassa kisassa.'),
        ('p', 'Käynnistä (/start) ja Pysäytä (/stop): käynnistää tai pysäyttää kisat.'),
        ('p', 'Autohost ON / OFF: kytkee hostin automaattiajon päälle tai pois.'),
        ('p', 'Lähetä vieheet ja väliajat: lähettää /lures- ja /results-komennot. Oma valinta '
              'avaa kuvavalitsimen, jossa voit valita vieheet yksitellen.'),
        ('h', 'Seuranta'),
        ('p', 'Oikealla näkyy hostin tila: onko kisa käynnissä ja paljonko aikaa on jäljellä, vai '
              'onko host lobbyssa odottamassa seuraavan kisan alkua. Lisäksi näkyvät vesistö, '
              'pelimuoto ja pelaajat.'),
        ('p', 'Hostin loki näyttää lähetetyt komennot ja, kun admin-salasana on annettu, hostin '
              'chatin tapahtumat (esim. vastauksen komentoon). Chatin seurannan voi kytkeä pois.'),
        ('p', 'Vihreä pallo = yhteys OK. Punainen pallo = ei yhteyttä.'),
        ('h', 'Hyvä tietää'),
        ('p', 'Yöllä pelattavat vain yövesistöt, ja yöllä pelimuotoina ovat made, kolme suurinta ja '
              'viisi suurinta kalaa. Made-kisat pelataan vain yöllä.'),
        ('p', 'Hiiren rulla vierittää aina vesistölistaa, joten muut asetukset eivät vaihdu '
              'vahingossa.'),
        ('p', 'Kieli vaihdetaan otsikon vieressä olevasta painikkeesta (Suomi / English). '
              'Vieheiden ja väliaikatulosten valinta ja kieli säilyvät seuraavaan käynnistykseen. '
              'IP, portti ja salasana eivät tallennu.'),
        ('h', 'Ongelmatilanteita'),
        ('p', 'Punainen pallo: tarkista IP ja portti, että host on käynnissä, ja että portti on '
              'avattu reitittimestä ja palomuurista. Oman verkon sisältä oman WAN-osoitteen '
              'käyttö ei aina toimi; käytä silloin koneen sisäverkon osoitetta.'),
        ('p', 'Lähetys hylätään (401): admin-salasana on väärin.'),
        ('p', 'Host ei vastaa lainkaan, vaikka osoite on oikein: host voi olla estänyt '
              'selainkäytön asetuksistaan, jolloin web-admin ei ole käytössä.'),
    ],
    'en': [
        ('h', 'Quick start'),
        ('p', '1. Enter the host IP address and port. The port is the one the host info page '
              'opens on in a browser (e.g. http://address:4500/).'),
        ('p', '2. Enter the admin password. The eye button shows the password for as long as you '
              'hold the mouse button down. The password is not saved to disk.'),
        ('p', '3. Select the lake, season, day time, game duration, game type and start place.'),
        ('p', '4. Press Send to host. The commands are shown in the Commands box before sending, '
              'and Copy puts them on the clipboard.'),
        ('h', 'Buttons'),
        ('p', 'Send to host: sends the /lake and /game commands, i.e. the lake and game type of '
              'the next game. They take effect in the next game.'),
        ('p', 'Start (/start) and Stop (/stop): start or stop the games.'),
        ('p', 'Autohost ON / OFF: turns the automatic hosting on or off.'),
        ('p', 'Send lures and results: sends the /lures and /results commands. Custom lures '
              'opens a picture picker where you can select the lures one by one.'),
        ('h', 'Monitoring'),
        ('p', 'The host status is shown on the right: whether a competition is running and how '
              'much time is left, or whether the host is in a game break waiting for the next '
              'game to start. The lake, game type and players are shown too.'),
        ('p', 'The host log shows the commands you sent and, once the admin password is entered, '
              'the host chat events (e.g. the reply to a command). Chat monitoring can be turned '
              'off.'),
        ('p', 'Green dot = connection OK. Red dot = no connection.'),
        ('h', 'Good to know'),
        ('p', 'Only night lakes can be played at night, and the night game types are only burbot, '
              'three biggest fish and five biggest fish. Burbot games are only played at night.'),
        ('p', 'The mouse wheel always scrolls the lake list only, so other settings do not '
              'change by accident.'),
        ('p', 'Change the language with the button next to the title (Suomi / English). The lure '
              'and intermediate results selections and the language are remembered. The IP, port '
              'and password are not saved.'),
        ('h', 'Troubleshooting'),
        ('p', 'Red dot: check the IP and port, that the host is running, and that the port is '
              'forwarded in the router and allowed in the firewall. From inside your own network '
              'using your own WAN address does not always work; use the computer\'s local '
              'address instead.'),
        ('p', 'Sending is rejected (401): the admin password is wrong.'),
        ('p', 'The host does not answer at all although the address is correct: the host may have '
              'disabled browser access in its settings, in which case the web admin is not '
              'available.'),
    ],
}
