# PebbleOS Czech language pack

Czech translation pack for Pebble watches running current Core Devices PebbleOS.

## Download

Download [`Czech-v3.pbl`](Czech-v3.pbl) and install it through the Pebble mobile app. Remove an older Czech pack before importing this one so the app does not reuse a cached copy.

## Compatibility and scope

- Tested by the maintainer on Pebble Time 2 with current Core Devices PebbleOS.
- The pack contains 616 translated gettext entries and Czech font resources inherited from the earlier Czech pack.
- The translation started from an earlier catalog and includes selected strings added by current PebbleOS. It is not a complete translation of every current firmware string; untranslated text remains in English.
- The firmware uses one gettext key for both abbreviated and full `May`; this pack uses `Kvě` for both forms.

## Source files

- `PebbleOS-en-cs-review.csv` contains the reviewed English/Czech translation table.
- `PebbleOS-extra-en-cs-review.csv` contains additional strings from the current Core Devices catalog.
- `tintin.po` is the gettext catalog used to build the pack.
- `build_czech_pbl.py` builds the PBL while preserving the existing Czech font resources.
- `pebbleos-current.pot` is the Core Devices source catalog used for the additional strings.

The upstream projects are [Core Devices PebbleOS](https://github.com/coredevices/PebbleOS) and [PebbleOS translations](https://github.com/coredevices/pebbleos-translations).

## Installation and feedback

Only one language pack can be installed at a time. Report translation issues with the English string and the screen where it appears.