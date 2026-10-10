# Pro Pilkki 2 · Admin tool

Graafinen etähallintatyökalu Pro Pilkki 2 -hostille. Valitse vesistö, vuodenaika,
vuorokaudenaika, kesto, pelimuoto, aloituspaikka, vieheet ja väliaikatulokset, ja
lähetä ne hostille suoraan IP-osoitteen ja portin kautta. Ulkoasu ja vesistödata
perustuvat [Pro Pilkki 2 Tulospalvelun autoscript-työkaluun](https://propilkkitulospalvelu.fi/autoscript/).

Epävirallinen työkalu. Ei liity Procyon Productsiin.

## Lataa

Lataa uusin `ProPilkki2-AdminTool.exe` [Releases-sivulta](../../releases/latest) ja käynnistä se.
Asennusta tai Pythonia ei tarvita.

Windows voi näyttää SmartScreen-varoituksen, koska exeä ei ole allekirjoitettu:
valitse *Lisätietoja → Suorita kuitenkin*.

## Käyttö

1. Kirjoita hostin **IP-osoite** ja **portti** (sama portti, jolla hostin info-sivu aukeaa selaimessa).
2. Kirjoita **admin-salasana**. Sitä ei tallenneta levylle.
3. Valitse vesistö ja asetukset ja paina **Lähetä hostille**.

Muut painikkeet: **Käynnistä** (`/start`), **Pysäytä** (`/stop`), **Autohost ON/OFF**
(`/autohost on|off`) sekä **Lähetä vieheet ja väliajat** (`/lures`, `/results`).
Komennot näkyvät ruudussa ennen lähetystä, ja **Kopioi** vie ne leikepöydälle.

Työkalu käyttää hostin omaa web-admin-sivua (`/Admin.html`, HTTP Basic -tunnistus).
Host voi estää selainkäytön asetuksistaan, jolloin yhteys ei toimi.

Vesistökuvat haetaan pelin omalta sivulta ensimmäisellä käynnistyksellä ja tallennetaan
kansioon `%LOCALAPPDATA%\ProPilkkiAdminTool`. Siellä on myös `asetukset.json`
(vieheiden ja väliaikatulosten valinta).

## Komennot

| Komento | Merkitys |
|---|---|
| `/lake <koodi>,<vuodenaika 1-3>,<aika 1-4>,<kesto 1-6>` | seuraavan kisan vesistö |
| `/game <pelimuoto>,<aloituspaikka>` | pelimuoto ja aloituspaikka |
| `/lures all\|off\|on\|custom <48 bittiä>` | vieheet |
| `/results off\|2\|5\|8\|10\|15` | väliaikatulokset |
| `/start`, `/stop`, `/autohost on\|off` | kisan ja autohostin ohjaus |

## Kehittäjälle

```
python admin_tool.py                    # ajaa suoraan (Python 3.10+, ei lisäpaketteja)
python lataa_kuvat.py                   # lataa kuvat kehityskäyttöön
python -m PyInstaller --noconfirm --onefile --noconsole --name ProPilkki2-AdminTool ^
  --icon ikoni.ico --add-data "kuvat/vieheet;kuvat/vieheet" admin_tool.py
```
