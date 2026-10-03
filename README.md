# PebbleOS Czech language pack

Czech translation pack for Pebble watches running current Core Devices PebbleOS.

## Download

Download [`Czech-v3.pbl`](Czech-v3.pbl) and install it through the Pebble mobile app. Remove an older Czech pack before importing this one so the app does not reuse a cached copy.

## Compatibility and scope

- Tested by the maintainer on Pebble Time 2 with current Core Devices PebbleOS.
- The pack contains 795 translated gettext entries from the current Core Devices catalog and Czech font resources inherited from the earlier Czech pack.
- The translation has been checked against the current catalog. Some firmware surfaces or strings outside this catalog may still appear in English.
- The firmware uses one gettext key for both abbreviated and full `May`; this pack uses `Kvě` for both forms.

## Source files

- `PebbleOS-en-cs-review.csv` contains the reviewed English/Czech translation table.
- `PebbleOS-extra-en-cs-review.csv` contains additional strings from the current Core Devices catalog.
- `PebbleOS-missing-en-cs.csv` lists keys that were absent from the previous pack.
- `PebbleOS-missing-en-cs-review.csv` contains their reviewed Czech translations.
- `tintin.po` is the gettext catalog used to build the pack.
- `build_czech_pbl.py` builds the PBL while preserving the existing Czech font resources.
- `pebbleos-current.pot` is the Core Devices source catalog used for the additional strings.

The upstream projects are [Core Devices PebbleOS](https://github.com/coredevices/PebbleOS) and [PebbleOS translations](https://github.com/coredevices/pebbleos-translations).

## Installation and feedback

Only one language pack can be installed at a time. Report translation issues with the English string and the screen where it appears.