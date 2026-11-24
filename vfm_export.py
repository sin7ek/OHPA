"""Interactive, export-only OpenAmber reference-data collector."""

import argparse
import datetime as dt
import getpass
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
import uuid

import httpx

import collector
import core
import research_flow
import virtual_flow

SUGGESTIONS = {
    'frequency': 'compressor_frequentie',
    'outside': 'buitentemperatuur_ta',
    'supply': 'cv_aanvoertemperatuur_tuo',
    'return': 'cv_retourtemperatuur_tui',
    'defrost': 'defrost',
    'pump_pwm': 'pomp_p0_pwm',
}
LABELS = {
    'frequency': 'Compressorfrequentie',
    'outside': 'Lokale buitentemperatuur (Ta)',
    'supply': 'Aanvoer (Tuo)',
    'return': 'Retour (Tui)',
    'power': 'Extern gemeten actief elektrisch vermogen (W of kW)',
    'heating': 'Ruimteverwarming actief (geen tapwater of koeling)',
    'defrost': 'Defrost actief',
    'flow': 'Debiet van fysieke flowmeter',
    'flow_counter': 'Cumulatief volume van fysieke flowmeter',
    'buh': 'Afzonderlijk gemeten vermogen van elektrische bijverwarming',
    'pump_pwm': 'Pomp P0 PWM',
}


def ask_choice(prompt, choices, default=None):
    suffix = f' [{default}]' if default is not None else ''
    while True:
        value = input(f'{prompt} ({"/".join(choices)}){suffix}: ').strip().lower() or default
        if value in choices:
            return value
        print('Kies een van de aangegeven opties.')


def pick_entity(role, entities, optional=False):
    accepted = core.ROLES[role][4]
    boolean = accepted == ['on/off']
    units = {core.unit_norm(unit): unit for unit in accepted}
    suffix = SUGGESTIONS.get(role)
    eligible = {
        row['entity_id']: row for row in entities
        if (boolean and row['entity_id'].startswith(('sensor.', 'binary_sensor.', 'input_boolean.')))
        or (not boolean and core.unit_norm(row.get('unit')) in units)
    }
    matches = [eid for eid in eligible if suffix and eid.split('.', 1)[1].endswith('_'+suffix)]
    default = matches[0] if len(matches) == 1 else None
    print(f'\n{LABELS[role]}')
    if default:
        print(f'  Voorstel: {default} ({eligible[default]["name"]})')
    while True:
        hint = ' [Enter accepteert voorstel]' if default else ''
        if optional:
            hint += ' [- slaat over]'
        entity = input(f'Entity-ID of ? voor keuzelijst{hint}: ').strip().lower() or default
        if entity == '-' and optional:
            return None
        if entity in eligible:
            row = eligible[entity]
            unit = 'on/off' if boolean else units[core.unit_norm(row.get('unit'))]
            on_value = 'on'
            if boolean and entity.startswith('sensor.'):
                on_value = ''
                while not on_value:
                    on_value = input(f'Exacte actieve status (huidig: {row["state"]}): ').strip()
            return {'entity': entity, 'unit': unit, 'attribute': '', 'on_value': on_value}
        if entity == '?':
            filter_text = input('Filter op naam of ID (Enter = alle): ').strip().casefold()
            for eid, row in sorted(eligible.items()):
                if filter_text in (eid+' '+row['name']).casefold():
                    print(f'  {eid} — {row["name"]}')
        else:
            print('Deze entiteit bestaat niet in de keuzelijst of heeft een andere eenheid.')


def read_installation_id(folder):
    path = folder / '.installation-id'
    if not path.exists():
        try:
            with path.open('x', encoding='ascii') as file:
                file.write(uuid.uuid4().hex + '\n')
        except FileExistsError:
            pass
    try:
        return uuid.UUID(path.read_text(encoding='ascii').strip()).hex
    except ValueError:
        raise ValueError('Ongeldig installatie-ID in .installation-id. Controleer het lokale bestand.') from None


def export_history(cfg, start, end, installation_id):
    """Use the same normalization, steady-state filter and schema as Research / VFM."""
    mappings = list(core.mapping(cfg).items())
    previous_data = core.DATA
    with tempfile.TemporaryDirectory(prefix='ohpa-vfm-') as directory:
        core.DATA = Path(directory)
        try:
            core.init()
            cursor = start - 300
            imported = 0
            while cursor < end:
                next_cursor = min(cursor + 86400, end)
                imported += collector.fetch_history(mappings, cursor, next_cursor)
                cursor = next_cursor
            if not imported:
                raise ValueError('Geen sensorhistorie ontvangen. Controleer de gekozen periode en HA Recorder.')
            setup = {
                'enabled': True,
                'confirmed': True,
                'installation_id': installation_id,
                'mapping_hash': research_flow.fingerprint(cfg),
            }
            return research_flow.observations(cfg, start, end, setup)
        finally:
            core.DATA = previous_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Adres van Home Assistant, bijvoorbeeld https://home.example')
    parser.add_argument('--hours', type=int, choices=(24, 72, 168), default=168)
    parser.add_argument('--end', help='Einde van het venster met UTC-offset, bijvoorbeeld 2026-11-24T00:00:00+01:00')
    parser.add_argument('--output-dir', type=Path, default=Path('vfm-export'))
    args = parser.parse_args()

    try:
        url = (args.url or os.getenv('HA_URL') or input('Home Assistant URL: ')).strip().rstrip('/')
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username is not None or parsed.query or parsed.fragment:
            raise ValueError('Gebruik een geldige HTTP(S)-URL zonder inloggegevens, query of fragment.')
        raw_end = dt.datetime.fromisoformat(args.end) if args.end else dt.datetime.now(dt.timezone.utc)
        if raw_end.utcoffset() is None:
            raise ValueError('Geef voor --end een datum en tijd met UTC-offset op.')
        end = min(raw_end.timestamp(), core.now())
        end = int(end // 60) * 60
        start = end - args.hours * 3600

        print('Gebruik HTTPS als je Home Assistant buiten je lokale netwerk benadert.')
        token = getpass.getpass('Home Assistant toegangstoken (verborgen): ').strip()
        if not token:
            raise ValueError('Een Home Assistant toegangstoken is vereist.')
        collector.HA_URL, collector.HA_TOKEN = url, token
        entities = collector.entities()
        cfg = {**core.DEFAULT, 'mapping': {}}
        cfg['model'] = ask_choice('Amber-model', sorted(virtual_flow.MODELS))
        for role in research_flow.REQUIRED:
            cfg['mapping'][role] = pick_entity(role, entities)
        flow_role = ask_choice('Type flowmeting', ['flow', 'flow_counter'], default='flow')
        cfg['mapping'][flow_role] = pick_entity(flow_role, entities)
        cfg['buh_mode'] = ask_choice('Elektrische bijverwarming (none = afwezig, separate = apart gemeten)', ['none', 'separate'])
        if cfg['buh_mode'] == 'separate':
            cfg['mapping']['buh'] = pick_entity('buh', entities)
        pump = pick_entity('pump_pwm', entities, optional=True)
        if pump:
            cfg['mapping']['pump_pwm'] = pump
        cfg['water_factor'] = float((input('Waterfactor in Wh/l/K [1.163 voor water]: ').strip() or '1.163').replace(',', '.'))
        if not 0.5 <= cfg['water_factor'] <= 1.5:
            raise ValueError('Waterfactor buiten bereik 0,5–1,5 Wh/l/K.')
        if ask_choice('Bevestig fysieke flowmeter, externe vermogensmeter, bedrijfsstatus en meetgrenzen', ['ja', 'nee'], default='nee') != 'ja':
            return 0

        args.output_dir.mkdir(parents=True, exist_ok=True)
        installation_id = read_installation_id(args.output_dir)
        print('Home Assistant-historie ophalen en stabiele verwarmingsminuten selecteren…')
        rows = export_history(cfg, start, end, installation_id)
        print(f'{len(rows)} geschikte minuten in het gekozen venster.')
        if not rows:
            print('Controleer de dekking van de gekoppelde sensoren, defrost, bijverwarming en verwarmingsstatus.')
            return 1
        if len(rows) < 30:
            print('OHPA heeft minstens 30 geschikte minuten per installatie nodig voor training.')
        for row in rows[:3]:
            print(f'  {row["frequency_hz"]:.0f} Hz | {row["power_w"]:.0f} W | {row["measured_flow_lh"]:.0f} l/h')
        if ask_choice('CSV lokaal opslaan', ['ja', 'nee'], default='ja') == 'ja':
            path = args.output_dir / f'ohpa-vfm-{cfg["model"]}-{uuid.uuid4().hex[:8]}.csv'
            with path.open('x', encoding='utf-8', newline='') as file:
                file.write(research_flow.export_csv(rows))
            print(f'Opgeslagen: {path}. Controleer het bestand en deel het via een privé-kanaal.')
        return 0
    except (ValueError, OSError, RuntimeError, httpx.HTTPError, EOFError) as error:
        if isinstance(error, httpx.HTTPError):
            print('Verbinding met Home Assistant mislukt. Controleer adres, bereikbaarheid en certificaat.')
        else:
            print(f'Export afgebroken: {error}')
        return 1
    except KeyboardInterrupt:
        print('\nExport afgebroken.')
        return 130
    finally:
        collector.HA_TOKEN = ''


if __name__ == '__main__':
    raise SystemExit(main())
