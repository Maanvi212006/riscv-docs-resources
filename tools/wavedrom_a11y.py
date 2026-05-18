import re
import sys
import json
import subprocess
import tempfile
import os

def extract_json(edn_path):
    with open(edn_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'\.\.\.\.(.+?)\.\.\.\.', content, re.DOTALL)
    if not match:
        raise ValueError(f"No wavedrom JSON found in {edn_path}")
    # Try to extract title from comment line
    # Try to extract title from section comment (e.g. //## 9.4 Atomic Memory Operations)
    comment_match = re.search(r'//#+\s*(.+)', content)
    if comment_match:
        comment_title = comment_match.group(1).strip()
    else:
        # Fall back to filename without extension
        basename = os.path.splitext(os.path.basename(edn_path))[0]
        comment_title = basename.replace('-', ' ').replace('_', ' ').upper() + " instruction encoding"
    return match.group(1).strip(), comment_title

def build_accessibility_text(json_text, comment_title=None):
    # Extract label from config if present
    label_match = re.search(r'label\s*:\s*\{[^}]*right\s*:\s*[\'"]([^\'"]+)[\'"]', json_text)
    if label_match:
        title = f"{label_match.group(1)} instruction encoding"
    elif comment_title:
        title = comment_title
    else:
        title = comment_title if comment_title else "Instruction encoding"

    # Extract fields
    fields = re.findall(r'\{bits\s*:\s*(\d+)\s*,\s*name\s*:\s*[\'"]([^\'"]+)[\'"]', json_text)

    desc_parts = [f"{bits} bit{'s' if int(bits) > 1 else ''}: {name}" for bits, name in fields]
    desc = "Fields from bit 0: " + ", ".join(desc_parts)

    return title, desc

def inject_accessibility(svg_text, title, desc):
    insertion = f'<title>{title}</title><desc>{desc}</desc>'
    return svg_text.replace('<svg ', f'<svg role="img" aria-label="{title}" ', 1)\
                   .replace('>', f'>{insertion}', 1)

def process(edn_path, output_svg_path):
    json_text, comment_title = extract_json(edn_path)

    # Write temp JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
        tmp.write(json_text)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ['npx.cmd', 'wavedrom-cli', '-i', tmp_path, '-o', '-'],
            capture_output=True, text=True
        )
        svg = result.stdout
    finally:
        os.unlink(tmp_path)

    title, desc = build_accessibility_text(json_text, comment_title)
    svg = inject_accessibility(svg, title, desc)

    with open(output_svg_path, 'w', encoding='utf-8') as f:
        f.write(svg)

    print(f"Done: {output_svg_path}")
    print(f"Title: {title}")
    print(f"Desc: {desc}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python wavedrom_a11y.py <input.edn> <output.svg>")
        sys.exit(1)
    process(sys.argv[1], sys.argv[2])