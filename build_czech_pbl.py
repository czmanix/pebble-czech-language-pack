import ast
import csv
import datetime
import gettext
import io
import json
import re
import struct
from pathlib import Path


POT_PATH = Path("tintin.pot")
CURRENT_POT_PATH = Path("pebbleos-current.pot")
CSV_PATH = Path("PebbleOS-en-cs-review.csv")
EXTRA_CSV_PATH = Path("PebbleOS-extra-en-cs-review.csv")
BASE_PBL_PATH = Path("Czech-v1.pbl")
PO_PATH = Path("tintin.po")
PBL_PATH = Path("Czech-v3.pbl")
FIELD_RE = re.compile(r"(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(.*)")
PLACEHOLDER_RE = re.compile(r"%(?:[-+#0-9.*hlLzjt]*[A-Za-z%])")
MO_MAGIC = 0x950412DE
APP_RESOURCE_COUNT = 256
PACK_HEADER_SIZE = 12
TABLE_ENTRY_SIZE = 16
CONTENT_OFFSET = PACK_HEADER_SIZE + APP_RESOURCE_COUNT * TABLE_ENTRY_SIZE


def normalize_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_pot(path):
    entries = []
    entry = {}
    comments = []
    active_field = None

    def finish_entry():
        if "msgid" in entry and entry["msgid"]:
            entries.append({
                "msgid": entry["msgid"],
                "msgctxt": entry.get("msgctxt", ""),
                "msgid_plural": entry.get("msgid_plural", ""),
                "comments": list(comments),
            })

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            finish_entry()
            entry = {}
            comments = []
            active_field = None
        elif line.startswith("#-#-#-#-"):
            continue
        elif line.startswith("#"):
            comments.append(line)
        elif line.startswith('"') and active_field:
            entry[active_field] += ast.literal_eval(line)
        else:
            match = FIELD_RE.fullmatch(line)
            if match:
                active_field = match.group(1)
                entry[active_field] = ast.literal_eval(match.group(2))

    finish_entry()
    return entries


def load_translations(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source, delimiter=";"))
    if not rows or set(rows[0]) != {"Anglicky", "Česky – návrh", "Kontext / poznámka"}:
        raise ValueError("Unexpected CSV header")
    return [
        (normalize_newlines(row["Anglicky"]), normalize_newlines(row["Česky – návrh"]))
        for row in rows
    ]


def load_extra_translations(path, current_entries):
    source_entries = {
        (entry["msgctxt"], normalize_newlines(entry["msgid"])): entry
        for entry in current_entries
    }
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source, delimiter=";"))

    expected_fields = {"gettext kontext", "Anglicky", "Česky – návrh", "Poznámka"}
    if not rows or set(rows[0]) != expected_fields:
        raise ValueError("Unexpected supplemental CSV header")

    extras = []
    for index, row in enumerate(rows, start=1):
        context = row["gettext kontext"]
        source_text = normalize_newlines(row["Anglicky"])
        target_text = normalize_newlines(row["Česky – návrh"])
        entry = source_entries.get((context, source_text))
        if entry is None:
            raise ValueError("Supplemental CSV row %d is not in the current POT" % index)
        if sorted(PLACEHOLDER_RE.findall(source_text)) != sorted(PLACEHOLDER_RE.findall(target_text)):
            raise ValueError("Supplemental CSV row %d changes format placeholders" % index)
        if not target_text.strip():
            raise ValueError("Supplemental CSV row %d has an empty translation" % index)
        extras.append((entry, source_text, target_text))
    return extras


def po_quote(text):
    return json.dumps(text, ensure_ascii=False)


def write_po(entries, translations, path, extra_entries=()):
    if len(entries) != len(translations):
        raise ValueError("POT and CSV entry counts differ")

    translated_entries = []
    seen = set()
    for index, (entry, (source, target)) in enumerate(zip(entries, translations), start=1):
        if source != normalize_newlines(entry["msgid"]):
            raise ValueError("CSV row %d does not match POT msgid" % index)
        if sorted(PLACEHOLDER_RE.findall(source)) != sorted(PLACEHOLDER_RE.findall(target)):
            raise ValueError("CSV row %d has changed format placeholders" % index)
        if not source.strip() and target != source:
            raise ValueError("Whitespace-only msgid must remain unchanged")
        if source.strip() and not target.strip():
            raise ValueError("CSV row %d has an empty translation" % index)

        key = (entry["msgctxt"], source)
        if key in seen:
            raise ValueError("Duplicate gettext key at CSV row %d" % index)
        seen.add(key)
        translated_entries.append((entry, source, target))

    for entry, source, target in extra_entries:
        key = (entry["msgctxt"], source)
        if key in seen:
            raise ValueError("Supplemental gettext key duplicates an existing entry")
        seen.add(key)
        translated_entries.append((entry, source, target))

    revision_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M%z")
    header = (
        "Project-Id-Version: 3.0\n"
        "Report-Msgid-Bugs-To: \n"
        "POT-Creation-Date: 2025-11-27 17:47+0000\n"
        "PO-Revision-Date: %s\n"
        "Name: Czech\n"
        "Language-Team: Czech\n"
        "Language: cs\n"
        "MIME-Version: 1.0\n"
        "Content-Type: text/plain; charset=UTF-8\n"
        "Content-Transfer-Encoding: 8bit\n"
        "X-Generator: POEditor.com\n"
    ) % revision_date

    lines = ['msgid ""', 'msgstr ""']
    lines.extend(po_quote(line + "\n") for line in header.splitlines())
    lines.append("")
    for entry, source, target in translated_entries:
        lines.extend(entry["comments"])
        if entry["msgctxt"]:
            lines.append("msgctxt " + po_quote(entry["msgctxt"]))
        lines.append("msgid " + po_quote(source))
        if entry["msgid_plural"]:
            raise ValueError("Plural PO entries are not supported by this CSV")
        lines.append("msgstr " + po_quote(target))
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return translated_entries, header


def compile_mo(entries, header):
    messages = {b"": header.encode("utf-8")}
    for entry, source, target in entries:
        key = source if not entry["msgctxt"] else entry["msgctxt"] + "\x04" + source
        messages[key.encode("utf-8")] = target.encode("utf-8")

    ordered = sorted(messages.items())
    count = len(ordered)
    original_table_offset = 7 * 4
    translated_table_offset = original_table_offset + count * 8
    hash_size = next_prime((count * 4 + 2) // 3)
    hash_table_offset = translated_table_offset + count * 8
    string_offset = hash_table_offset + hash_size * 4
    originals = bytearray()
    translations = bytearray()
    original_table = []
    translated_table = []

    for original, _ in ordered:
        original_table.append((len(original), string_offset + len(originals)))
        originals.extend(original + b"\0")
    for _, translated in ordered:
        translated_table.append((len(translated), string_offset + len(originals) + len(translations)))
        translations.extend(translated + b"\0")

    hash_table = [0] * hash_size
    for index, (original, _) in enumerate(ordered, start=1):
        hash_value = gnu_hash(original)
        slot = hash_value % hash_size
        increment = 1 + hash_value % (hash_size - 2)
        while hash_table[slot]:
            slot = (slot + increment) % hash_size
        hash_table[slot] = index

    header_data = struct.pack(
        "<7I", MO_MAGIC, 0, count, original_table_offset,
        translated_table_offset, hash_size, hash_table_offset,
    )
    tables = b"".join(struct.pack("<II", *item) for item in original_table + translated_table)
    hashes = struct.pack("<%dI" % hash_size, *hash_table)
    return header_data + tables + hashes + bytes(originals) + bytes(translations)


def gnu_hash(data):
    value = 0
    for byte in data:
        value = (value << 4) + byte
        high_bits = value & 0xF0000000
        if high_bits:
            value ^= high_bits >> 24
            value &= ~high_bits
    return value & 0xFFFFFFFF


def next_prime(value):
    candidate = max(value, 3)
    while True:
        if all(candidate % divisor for divisor in range(2, int(candidate ** 0.5) + 1)):
            return candidate
        candidate += 1


def stm32_crc32(data):
    polynomial = 0x04C11DB7
    table = []
    for value in range(256):
        crc = value << 24
        for _ in range(8):
            crc = ((crc << 1) ^ polynomial) & 0xFFFFFFFF if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
        table.append(crc)

    crc = 0xFFFFFFFF
    for start in range(0, len(data), 4):
        word = data[start:start + 4]
        if len(word) < 4:
            word = word[::-1] + b"\0" * (4 - len(word))
        for byte in reversed(word):
            crc = ((crc << 8) ^ table[(crc >> 24) ^ byte]) & 0xFFFFFFFF
    return crc


def unpack_pbl(data):
    count, manifest_crc, _ = struct.unpack_from("<III", data)
    if count > APP_RESOURCE_COUNT or len(data) < CONTENT_OFFSET:
        raise ValueError("Invalid application resource pack header")

    resources = []
    unique_content = {}
    for index in range(count):
        file_id, offset, length, expected_crc = struct.unpack_from(
            "<IIII", data, PACK_HEADER_SIZE + index * TABLE_ENTRY_SIZE)
        if file_id != index + 1:
            raise ValueError("Invalid resource ID %d" % file_id)
        start = CONTENT_OFFSET + offset
        content = data[start:start + length]
        if len(content) != length or stm32_crc32(content) != expected_crc:
            raise ValueError("Resource %d failed length/CRC validation" % file_id)
        resources.append(content)
        unique_content[(offset, length)] = content

    content_data = b"".join(value for _, value in sorted(unique_content.items()))
    if stm32_crc32(content_data) != manifest_crc:
        raise ValueError("Resource pack manifest CRC validation failed")
    return resources


def pack_pbl(resources):
    if len(resources) > APP_RESOURCE_COUNT:
        raise ValueError("Too many language pack resources")

    content_indexes = []
    unique_contents = []
    unique_map = {}
    for content in resources:
        index = unique_map.get(content)
        if index is None:
            index = len(unique_contents)
            unique_map[content] = index
            unique_contents.append(content)
        content_indexes.append(index)

    offsets = {}
    current_offset = sum(map(len, unique_contents))
    for index in reversed(content_indexes):
        content_index = index
        if content_index not in offsets:
            current_offset -= len(unique_contents[content_index])
            offsets[content_index] = current_offset

    entries = []
    for index, content_index in enumerate(content_indexes, start=1):
        content = unique_contents[content_index]
        entries.append(struct.pack(
            "<IIII", index, offsets[content_index], len(content), stm32_crc32(content)))
    entries.extend([struct.pack("<IIII", 0, 0, 0, 0)] * (APP_RESOURCE_COUNT - len(entries)))

    payload = b"".join(
        unique_contents[index]
        for index in sorted(range(len(unique_contents)), key=lambda i: offsets[i])
    )
    manifest = struct.pack("<III", len(resources), stm32_crc32(payload), 0)
    return manifest + b"".join(entries) + payload


def main():
    entries = parse_pot(POT_PATH)
    translations = load_translations(CSV_PATH)
    current_entries = parse_pot(CURRENT_POT_PATH)
    extra_entries = load_extra_translations(EXTRA_CSV_PATH, current_entries)
    translated_entries, po_header = write_po(entries, translations, PO_PATH, extra_entries)
    mo_data = compile_mo(translated_entries, po_header)
    catalog = gettext.GNUTranslations(io.BytesIO(mo_data))
    if len(catalog._catalog) != len(translated_entries) + 1:
        raise ValueError("Compiled MO catalog has an unexpected entry count")

    base_resources = unpack_pbl(BASE_PBL_PATH.read_bytes())
    if len(base_resources) != 19:
        raise ValueError("Expected 19 resources in the existing Czech language pack")
    output_data = pack_pbl([mo_data] + base_resources[1:])
    verified_resources = unpack_pbl(output_data)
    if verified_resources[0] != mo_data or verified_resources[1:] != base_resources[1:]:
        raise ValueError("Packed output did not preserve the original Czech font resources")
    catalog_check = gettext.GNUTranslations(io.BytesIO(verified_resources[0]))
    PBL_PATH.write_bytes(output_data)

    print("PO: %s (%d messages)" % (PO_PATH, len(translated_entries)))
    print("PBL: %s (%d bytes, %d resources, %d-byte strings MO)" % (
        PBL_PATH, len(output_data), len(verified_resources), len(verified_resources[0])))
    print("Preserved %d Czech font resource slots; %d contain data" % (
        len(verified_resources) - 1,
        sum(bool(resource) for resource in verified_resources[1:])))
    print("Compiled gettext entries: %d" % (len(catalog_check._catalog) - 1))
    print("Added %d verified Core Devices gettext keys" % len(extra_entries))


if __name__ == "__main__":
    main()