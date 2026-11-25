# Losse OHPA VFM Exporter

Deze interactieve terminaltool maakt referentie-CSV’s voor het trainen van de virtuele flowmeter in OHPA. Hij haalt de historie rechtstreeks uit je eigen Home Assistant en draait ook als je OHPA zelf niet gebruikt. Je beoordeelt het voorbeeld en kiest zelf of je een CSV opslaat en deelt.

## Wat heb je nodig?

- Een Amber 65, 95 of 120 met OpenAmber en Home Assistant Recorder-historie.
- Een fysieke flowmeter en een externe meter voor het actuele actieve elektrische vermogen van de warmtepomp.
- OpenAmber-status voor ruimteverwarming (onderscheid van tapwater en koeling), defrost, aanvoer, retour, compressorfrequentie en lokale buitentemperatuur.
- Bij elektrische bijverwarming is een aparte vermogensmeting nodig. Pomp P0 PWM is optioneel voor Thermal en nodig voor een PWM- of Hybrid-model.
- Een tijdelijk voor deze export aangemaakt Home Assistant-toegangstoken. Gebruik de instructies onder Authentication in de [Home Assistant REST API-documentatie](https://developers.home-assistant.io/docs/api/rest/). Trek het token na je laatste export in via je HA-profiel.

## Exporteren

Gebruik de repositoryversie die `vfm_export.py` bevat. Vanuit de hoofdmap met Python 3.12:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python vfm_export.py --hours 168
```

Gebruik op Windows `.venv\Scripts\python.exe` in plaats van `.venv/bin/python`. Als je Docker gebruikt op Linux of Unraid:

```sh
docker build --target standalone -t ohpa-vfm-exporter .
mkdir -p vfm-export
docker run --rm -it --user "$(id -u):$(id -g)" \
  -v "$PWD/vfm-export:/exports" ohpa-vfm-exporter \
  python vfm_export.py --hours 168 --output-dir /exports
```

Voer het HA-adres en het toegangstoken in bij de prompts. Bevestig de voorgestelde OpenAmber-entiteiten of kies zelf een alternatief met `?`. Laat de export eerst de afgelopen zeven dagen bekijken. Beschikbare vensters zijn `--hours 24`, `72` en `168`. Wil je opeenvolgende gegevens aanleveren, geef dan per export een eigen eindtijd met offset op, bijvoorbeeld `--end 2026-11-24T00:00:00+01:00`. Vermijd overlappende periodes van dezelfde installatie; het CSV bevat relatieve minuten. Houd die periodes desgewenst zelf lokaal bij.

Het minimum is 30 geschikte minuten per installatie. Richt je voor een eerste bijdrage op een paar honderd minuten verspreid over meerdere compressorfrequenties of pompstanden. Bij weinig geschikte data kun je de sensorhistorie en bedrijfsstatus nalopen. De exporter gebruikt dezelfde filters en CSV-kolommen als OHPA Research / VFM. Heb je OHPA al, dan kun je ook daar **Referentiedata exporteren → 7 d → Voorbeeld maken → CSV downloaden** gebruiken.

## Delen

Controleer het opgeslagen CSV en stuur alleen dat bestand via de afgesproken privéroute. Het bevat technische meetwaarden, een willekeurig installatie-ID en relatieve minuten. Gebruik voor herhaalde exports dezelfde lokale exportmap zodat het installatie-ID gelijk blijft. Het verborgen bestand `.installation-id` is alleen voor lokaal gebruik. Exporteer een installatie bij voorkeur steeds via dezelfde tool, zodat de ontvanger die als één installatie kan tellen.

De module bewaart het toegangstoken alleen tijdens het draaien en verwijdert tijdelijke sensorhistorie bij afsluiten. Er is geen automatische upload. De ontvanger kan de CSV selecteren in OHPA Research / VFM en per Amber-model trainen.
