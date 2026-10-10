"""Pro Pilkki 2 -vesistöt ja pelimuodot.

Data on otettu https://propilkkitulospalvelu.fi/autoscript/ -sivun tiedoista.
Kentät: nimi, /lake-koodi, sallitut pelimuodot, aloituspaikat (jos useita),
yö = vesistössä voi pelata yöllä.
"""

PELIMUODOT = {
    1: 'Normaali', 2: 'Kappalemäärä', 3: 'Kaikki lajit', 4: 'Kaikki lajit, kappalemäärä',
    5: 'Suurin kala', 6: 'Eniten lajeja', 7: 'Kirjo ja taimen', 8: 'Kirjo ja taimen, kappalemäärä',
    9: 'Vain pasuri', 10: 'Vain pasuri, kappalemäärä', 11: 'Vain made', 12: 'Vain made, kappalemäärä',
    13: 'Vain kiiski', 14: 'Vain kiiski, kappalemäärä', 15: 'Vain ahven', 16: 'Vain ahven, kappalemäärä',
    17: 'Vain hauki', 18: 'Suurin hauki', 19: 'Vain kuha', 20: 'Suurin kuha',
    21: 'Vain särkikalat', 22: 'Vain särkikalat, kappalemäärä', 23: 'Suurin särkikala',
    24: 'Kolme suurinta kalaa', 25: 'Viisi suurinta kalaa', 26: 'Vain siika',
    27: 'Vain siika, kappalemäärä', 28: 'Ruutupilkki', 29: 'Ruutupilkki, kappalemäärä',
}

VUODENAJAT = {1: 'Syksy', 2: 'Talvi', 3: 'Kevät'}
AJAT = {1: 'Aamu', 2: 'Päivä', 3: 'Ilta', 4: 'Yö'}
KESTOT = {1: 10, 2: 15, 3: 30, 4: 60, 5: 90, 6: 120}

MADE = (11, 12)              # ei aamulla, päivällä eikä illalla
YON_MUODOT = (11, 12, 24, 25)  # yöllä vain nämä


def _l(nimi, koodi, muodot, paikat=None, yo=False):
    return {'nimi': nimi, 'koodi': koodi, 'muodot': muodot, 'paikat': paikat or [], 'yo': yo}


JARVET = [
    _l('Haapolahti', 'haapolahti', [1,2,3,4,5,6,9,10,11,12,13,14,15,16,21,22,23,24,25,28,29], yo=True),
    _l('Harjukankaan monttu', 'harjukankaan', [1,2,3,4,5,6,13,14,15,16,21,22,24,25,26,27,28,29]),
    _l('Haukilahti', 'haukilahti', [1,2,3,4,5,6,11,12,13,14,15,16,21,22,23,24,25,26,27,28,29], yo=True),
    _l('Hossalaislammet', 'hossalaislammet', [1,2,3,4,5,6,7,8,24,25,26,27,28,29]),
    _l('Iso-Ruuhijärvi', 'ruuhi', [1,3,4,5,6,7,24,25,28,29]),
    _l('Iso-Söimi', 'söimi', [1,2,5,6,24,25,26,27,28,29]),
    _l('Jormuanlahti', 'jormuanlahti', [1,2,3,4,5,6,11,12,13,14,15,16,21,22,23,24,25,28,29],
       ['Hietalahti', 'Vaajalahti', 'Pöyhölänniemi'], yo=True),
    _l('Kivijoki', 'kivijoki', [1,2,3,4,5,6,13,14,15,16,17,18,21,22,23,24,25,28,29],
       ['Jokisuvanto', 'Kellokoski', 'Ryhäjoki']),
    _l('Koivusaaren matalikko', 'koivusaaren', [1,2,3,4,5,6,11,12,15,16,19,20,21,22,23,24,25,28,29], yo=True),
    _l('Kolmisoppi', 'kolmisoppi', [1,2,3,4,5,7,15,16,24,25,28,29]),
    _l('Korpipuro', 'korpipuro', [1,2,5,24,25,28,29]),
    _l('Kortejärvi', 'korte', [1,2,3,4,5,6,13,14,15,16,17,18,21,22,24,25,28,29]),
    _l('Kuikansalmi', 'kuikansalmi', [1,2,3,4,5,6,7,11,12,15,16,21,22,23,24,25,28,29], yo=True),
    _l('Kuopionlahti', 'kuopionlahti', [1,2,3,4,5,6,11,12,13,14,15,16,21,22,23,24,25,28,29], yo=True),
    _l('Lahnalammet', 'lahnalammet', [1,2,3,4,5,6,9,10,13,14,15,16,17,18,21,22,23,24,25,28,29]),
    _l('Lehmilampi', 'lehmilampi', [1,3,4,5,6,9,10,15,16,21,22,23,24,25,28,29]),
    _l('Linlonlahti', 'linlonlahti', [1,3,4,5,6,11,12,13,15,16,19,20,21,22,23,24,25,28,29], yo=True),
    _l('Lokkiluoto', 'lokkiluoto', [1,2,3,4,5,6,11,12,13,14,15,16,17,18,21,22,24,25,28,29], yo=True),
    _l('Meri', 'meri', [1,2,3,4,5,6,13,14,15,16,24,25,28,29]),
    _l('Metsälampi', 'mets', [1,2,3,4,5,6,15,16,21,22,23,24,25,28,29]),
    _l('Muddusjärvi', 'muddus', [1,2,3,4,5,6,15,16,24,25,28,29]),
    _l('Mustalampi', 'mustalampi', [1,2,5,15,16,17,18,21,22,23,24,25,28,29]),
    _l('Mäntylahti', 'mäntylahti', [1,2,3,4,5,6,9,10,15,16,19,20,21,22,23,24,25,28,29]),
    _l('Niemisjärvet', 'niemis', [1,3,4,5,6,7,24,25,26,27,28,29]),
    _l('Palusjärvi', 'palus', [1,2,3,4,5,6,9,10,13,14,15,16,17,18,21,22,23,24,25,28,29]),
    _l('Peräjärvi', 'per', [1,2,3,4,5,6,11,12,13,14,15,16,17,18,21,22,23,24,25,28,29], yo=True),
    _l('Pieni Särkinen', 'pieni', [1,2,3,4,5,6,13,14,15,16,21,22,23,24,25,28,29]),
    _l('Pitkälampi', 'pitk', [1,2,3,4,5,13,14,15,16,17,18,24,25,28,29]),
    _l('Pohjalampi', 'pohjalampi', [1,2,3,4,5,15,16,24,25,28,29]),
    _l('Rautupuro', 'rautupuro', [1,2,5,24,25,26,27,28,29]),
    _l('Ruippo', 'ruippo', [1,2,3,4,5,6,13,14,15,16,17,18,21,22,24,25,28,29]),
    _l('Räväjärvi', 'räväjärvi', [1,2,3,4,5,6,13,14,15,16,21,22,24,25,26,27,28,29],
       ['Rävä', 'Virtaniemi']),
    _l('Rönttäoja', 'rönttäoja', [1,2,3,4,5,6,11,12,13,14,15,16,21,22,23,24,25,28,29], yo=True),
    _l('Saarijärvi', 'saari', [1,2,3,4,5,6,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,28,29],
       ['Läntinen', 'Itäinen'], yo=True),
    _l('Savilahti', 'savilahti', [1,2,3,4,5,6,9,10,11,12,13,14,15,16,21,22,23,24,25,28,29], yo=True),
    _l('Siika-valkeinen', 'valkeinen', [1,2,3,4,5,11,12,13,14,24,25,26,27,28,29], yo=True),
    _l('Siikakoski', 'siikakoski', [1,2,5,24,25,26,27,28,29]),
    _l('Surrinlampi', 'surrinlampi', [1,2,3,4,5,6,15,16,21,22,23,24,25,28,29]),
    _l('Särkijärvi', 'särkijärvi', [1,2,3,4,5,9,10,15,16,21,22,23,24,25,28,29]),
    _l('Taivallampi', 'taivallampi', [1,2,3,4,5,6,15,16,17,18,21,22,23,24,25,28,29],
       ['Pohjoinen', 'Eteläinen']),
    _l('Telkänlampi', 'telk', [1,2,5,15,16,24,25,28,29]),
    _l('Ullavanjärvi', 'ullava', [1,2,3,4,5,6,11,12,13,14,15,16,17,18,21,22,23,24,25,28,29],
       ['Haapamaa', 'Ojansuu', 'Selkäsaari'], yo=True),
    _l('Venetjoen tekojärvi', 'venetjoen', [1,2,3,4,5,6,11,12,13,14,15,16,17,18,21,22,23,24,25,26,28,29], yo=True),
    _l('Viitalampi', 'viitalampi', [1,2,3,4,5,15,16,17,18,21,22,24,25,28,29]),
    _l('Vuolasniva', 'vuolasniva', [1,2,5,24,25,26,27,28,29]),
    _l('Vuontele', 'vuontele', [1,2,3,4,5,6,11,12,13,14,15,16,17,18,21,22,23,24,25,28,29],
       ['Aittojoki', 'Koskenkorva', 'Järvenpäänlahti'], yo=True),
]


def sallitut_muodot(jarvi, aika):
    """Vesistön pelimuodot annetulle vuorokaudenajalle (1-4)."""
    if aika == 4:
        return [m for m in jarvi['muodot'] if m in YON_MUODOT]
    return [m for m in jarvi['muodot'] if m not in MADE]


# Vieheet: (nimi, alku, määrä, kuvan tiedostonimen alku). 3 ryhmää x 16 = 48 viehettä.
VIEHELAJIT = [
    ('Pystyt', 0, 16, 'pysty'),
    ('Tasurit', 16, 16, 'tasuri'),
    ('Muut', 32, 8, 'muu'),
    ('Morrit', 40, 8, 'morri'),
]
VIEHEITA = 48
VIEHETILAT = [('all', 'Kaikki'), ('off', 'Perus'), ('on', 'Perus + 6 sattumanvaraista'),
              ('custom', 'Oma valinta')]


def viehekoodi(valitut):
    """48 bittiä -> 'xxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx' (/lures custom)."""
    bitit = ''.join('1' if v else '0' for v in valitut)
    return '-'.join(bitit[i:i + 16] for i in range(0, 48, 16))


# Väliaikatulokset (/results): (arvo, valikon teksti)
TULOKSET = [('off', 'Ei väliaikatuloksia'), ('2', '2 min välein'), ('5', '5 min välein'),
            ('8', '8 min välein'), ('10', '10 min välein'), ('15', '15 min välein')]
