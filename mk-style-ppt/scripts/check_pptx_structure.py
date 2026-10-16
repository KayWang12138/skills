"""Read-only PPTX checks for known OOXML structural faults; not full schema validation."""
import argparse
import json
import posixpath
import sys
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def check(path):
    errors = []
    parsed = {}
    relationships = {}
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        for name, count in Counter(names).items():
            if count > 1:
                errors.append(f'Duplicate ZIP member: {name}')
        bad = package.testzip()
        if bad:
            errors.append(f'ZIP CRC failure: {bad}')
        for name in names:
            if name.endswith(('.xml', '.rels')):
                try:
                    parsed[name] = ET.fromstring(package.read(name))
                except ET.ParseError as exc:
                    errors.append(f'{name}: XML parse failure: {exc}')
        for name, root in parsed.items():
            if not name.endswith('.rels'):
                continue
            parent = posixpath.dirname(name)
            source = '' if name == '_rels/.rels' else posixpath.join(
                posixpath.dirname(parent), posixpath.basename(name)[:-5])
            rels = {}
            for rel in root:
                rid = rel.get('Id')
                if rid in rels:
                    errors.append(f'{name}: duplicate relationship ID {rid}')
                rels[rid] = rel
                if rel.get('TargetMode') != 'External':
                    target = unquote(rel.get('Target', '').split('#', 1)[0])
                    resolved = target.lstrip('/') if target.startswith('/') else posixpath.normpath(
                        posixpath.join(posixpath.dirname(source), target))
                    if resolved not in names:
                        errors.append(f'{name}: missing target {resolved}')
            relationships[source] = rels
        order = {'bg': 0, 'spTree': 1, 'custDataLst': 2, 'controls': 3, 'extLst': 4}
        for name, root in parsed.items():
            for cs in root.iter(f'{{{P}}}cSld'):
                tags = [child.tag.rsplit('}', 1)[-1] for child in cs]
                ranks = [order.get(tag, 99) for tag in tags]
                if ranks != sorted(ranks) or any(tag not in order for tag in tags):
                    errors.append(f'{name}: invalid cSld child sequence {tags}')
                if tags.count('spTree') != 1 or len(tags) != len(set(tags)):
                    errors.append(f'{name}: missing or duplicate cSld child {tags}')
            if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                ids = [node.get('id') for node in root.iter(f'{{{P}}}cNvPr')]
                if len(ids) != len(set(ids)):
                    errors.append(f'{name}: duplicate shape ID')
            for node in root.iter():
                for attr, value in node.attrib.items():
                    if attr.startswith(f'{{{R}}}') and value not in relationships.get(name, {}):
                        errors.append(f'{name}: unresolved relationship {value}')
    return {'file': str(path), 'passed': not errors, 'errors': errors,
            'scope': 'Known structure checks only; not full schema or Office opening validation.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pptx', type=Path)
    args = parser.parse_args()
    try:
        report = check(args.pptx)
    except (OSError, zipfile.BadZipFile) as exc:
        report = {'passed': False, 'errors': [str(exc)]}
    print(json.dumps(report, ensure_ascii=True, indent=2))
    sys.exit(0 if report['passed'] else 1)
