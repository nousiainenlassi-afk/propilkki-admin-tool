"""Kehittäjän apuskripti: lataa vesistökuvat ja vieheiden kuvat kansioon kuvat/.

Vieheiden kuvat (kuvat/vieheet) kuuluvat repoon ja exeen. Vesistökuvia ei
commitoida; sovellus hakee ne itse ensimmäisellä käynnistyksellä.
"""
import os
import urllib.request

from kuvalataus import lataa_jarvikuvat
from lakes import JARVET, VIEHELAJIT

KOHDE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kuvat')
VIEHE_URL = 'https://propilkkitulospalvelu.fi/autoscript/vieheet/%s-%02d.png'

if __name__ == '__main__':
    puuttuu = lataa_jarvikuvat(KOHDE, JARVET)
    print('vesistökuvat', len(JARVET) - len(puuttuu), '/', len(JARVET), '| puuttuu:', puuttuu)
    vkohde = os.path.join(KOHDE, 'vieheet')
    os.makedirs(vkohde, exist_ok=True)
    vpuuttuu = []
    for _nimi, _alku, _maara, _kuva in VIEHELAJIT:
        for i in range(1, _maara + 1):
            try:
                data = urllib.request.urlopen(VIEHE_URL % (_kuva, i), timeout=15).read()
                with open(os.path.join(vkohde, f'{_kuva}-{i:02d}.png'), 'wb') as f:
                    f.write(data)
            except Exception:
                vpuuttuu.append(f'{_kuva}-{i:02d}')
    print('vieheet', 48 - len(vpuuttuu), '/ 48 | puuttuu:', vpuuttuu)

