"""Vesistökuvien lataus pelin omalta sivulta (propilkki.fi).

Kuvia ei jaeta tämän työkalun mukana: sovellus hakee puuttuvat kuvat itse
ensimmäisellä käynnistyksellä käyttäjän omaan kansioon.
"""
import os
import urllib.request

# /lake-koodi -> kuvan nimi LakePics-kansiossa
KUVA_TIEDOSTO = {
    'haapolahti': 'haapolahti', 'harjukankaan': 'harjukankaanmonttu', 'haukilahti': 'haukilahti',
    'hossalaislammet': 'hossalais', 'ruuhi': 'ruuhijarvi', 'söimi': 'isosoimi',
    'jormuanlahti': 'jormuanlahti', 'kivijoki': 'kivijoki', 'koivusaaren': 'koivusaari',
    'kolmisoppi': 'kolmisoppi', 'korpipuro': 'korpipuro', 'korte': 'kortejarvi',
    'kuikansalmi': 'kuikansalmi', 'kuopionlahti': 'kuopionlahti', 'lahnalammet': 'lahnalammet',
    'lehmilampi': 'lehmilampi', 'linlonlahti': 'linlonlahti', 'lokkiluoto': 'lokkiluoto',
    'meri': 'meri', 'mets': 'metsalampi', 'muddus': 'muddusjarvi', 'mustalampi': 'mustalampi',
    'mäntylahti': 'mantylahti', 'niemis': 'niemisjarvet', 'palus': 'palusjarvi',
    'per': 'perajarvi', 'pieni': 'pienisarkinen', 'pitk': 'pitkalampi', 'pohjalampi': 'pohjalampi',
    'rautupuro': 'rautupuro', 'ruippo': 'ruippo', 'räväjärvi': 'ravajarvi',
    'rönttäoja': 'ronttaoja', 'saari': 'saarijarvi', 'savilahti': 'savilahti',
    'valkeinen': 'siikavalkeinen', 'siikakoski': 'siikakoski', 'surrinlampi': 'Surrinlampi',
    'särkijärvi': 'sarkijarvi', 'taivallampi': 'taivallampi', 'telk': 'telkanlampi',
    'ullava': 'ullava', 'venetjoen': 'venetjarvi', 'viitalampi': 'viitalampi',
    'vuolasniva': 'vuolasniva', 'vuontele': 'vuontele',
}
URL = 'https://www.propilkki.fi/propilkki2/LakePics/%s.png'


def lataa_jarvikuvat(kohde, jarvet):
    """Lataa annettujen vesistöjen kuvat kansioon kohde. Palauttaa puuttuvien nimet."""
    os.makedirs(kohde, exist_ok=True)
    puuttuu = []
    for j in jarvet:
        nimi = KUVA_TIEDOSTO.get(j['koodi'])
        polku = os.path.join(kohde, j['koodi'] + '.png')
        if not nimi:
            puuttuu.append(j['nimi'])
            continue
        for yritys in dict.fromkeys([nimi, nimi.lower(), nimi.capitalize()]):
            try:
                data = urllib.request.urlopen(URL % yritys, timeout=15).read()
                if data[:4] != b'\x89PNG':
                    continue
                with open(polku, 'wb') as f:
                    f.write(data)
                break
            except Exception:
                continue
        else:
            puuttuu.append(j['nimi'])
    return puuttuu
