#!/usr/bin/env python3
import os, sys, subprocess, datetime
from urllib.parse import quote

# --- CONFIG ---
BASE_URL = "https://agdistys.github.io/Schemas"  # URL publique de ton site (sans / final)
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}  # extensions incluses
OUTPUT = "sitemap.xml"
# --------------

def git_lastmod(path):
    try:
        ts = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "--", path],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if ts:
            return ts
    except Exception:
        pass
    # fallback: mtime locale → ISO 8601 (approx)
    dt = datetime.datetime.utcfromtimestamp(os.path.getmtime(path))
    return dt.replace(microsecond=0).isoformat() + "Z"

def iter_images(root="."):
    for dirpath, dirnames, filenames in os.walk(root):
        # ignore dossiers cachés
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != ".git"]
        for fn in filenames:
            if fn.startswith("."): 
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in IMAGE_EXT:
                rel = os.path.relpath(os.path.join(dirpath, fn), root)
                yield rel

def make_xml(url_entries):
    # sitemap images (namespace image:)
    head = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    )
    tail = '</urlset>\n'
    return head + "".join(url_entries) + tail

def main():
    entries = []
    count = 0
    for rel in sorted(iter_images(".")):
        # URL encodée (respecte espaces, & …)
        loc = f"{BASE_URL}/{quote(rel.replace(os.sep, '/'))}"
        lastmod = git_lastmod(rel)

        # On crée une entrée <url> par image (loc = l’URL de l’image)
        entry = (
            "  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <image:image>\n"
            f"      <image:loc>{loc}</image:loc>\n"
            f"      <image:caption>{os.path.basename(rel)}</image:caption>\n"
            f"    </image:image>\n"
            "  </url>\n"
        )
        entries.append(entry)
        count += 1

    xml = make_xml(entries)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"Generated {OUTPUT} with {count} image(s).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
