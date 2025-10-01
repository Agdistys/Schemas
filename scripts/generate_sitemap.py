#!/usr/bin/env python3
import os, sys, subprocess, datetime
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

# --- CONFIG ---
BASE_URL = "https://agdistys.github.io/Schemas"  # sans slash final
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
OUTPUT_SITEMAP = "sitemap.xml"
OUTPUT_UPDATES = "latest-updates.json"
# --------------

# --- SECTION 1 : FONCTIONS POUR LE SITEMAP ---
def git_lastmod(path):
    """Dernière date ISO 8601 depuis git, sinon mtime fichier."""
    try:
        ts = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "--", path],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if ts:
            return ts
    except Exception:
        pass
    dt = datetime.datetime.utcfromtimestamp(os.path.getmtime(path))
    return dt.replace(microsecond=0).isoformat() + "Z"

def iter_images(root="."):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != ".git"]
        for fn in filenames:
            if fn.startswith("."):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in IMAGE_EXT:
                rel = os.path.relpath(os.path.join(dirpath, fn), root)
                yield rel

def make_entry(rel_path):
    encoded = quote(rel_path.replace(os.sep, "/"), safe="/")
    url = f"{BASE_URL}/{encoded}"
    lastmod = git_lastmod(rel_path)
    url_xml = xml_escape(url)
    caption_xml = xml_escape(os.path.basename(rel_path))
    return (
        " <url>\n"
        f" <loc>{url_xml}</loc>\n"
        f" <lastmod>{lastmod}</lastmod>\n"
        f" <image:image>\n"
        f" <image:loc>{url_xml}</image:loc>\n"
        f" <image:caption>{caption_xml}</image:caption>\n"
        f" </image:image>\n"
        " </url>\n"
    )

# --- SECTION 2 : FONCTION POUR TOUS LES DERNIERS AJOUTS ---
def get_all_updates():
    """Récupère tous les commits avec message et date formatée."""
    result = subprocess.run(['git', 'log', '--pretty=format:%s|%ad'],
                           capture_output=True, text=True)
    commits = result.stdout.strip().split('\n')
    updates = []
    for commit in commits:
        if commit:
            message, date_str = commit.split('|', 1)
            date = datetime.datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y %z').strftime('%d/%m/%Y')
            updates.append({"title": message, "date": date, "url": f"{BASE_URL}/{quote(message.replace(' ', '_'), safe='/')}.png"})
    return updates

# --- SECTION 3 : FONCTION PRINCIPALE ---
def main():
    # Génère le sitemap
    entries = [make_entry(rel) for rel in sorted(iter_images("."))]
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' +
        "".join(entries) +
        "</urlset>\n"
    )
    with open(OUTPUT_SITEMAP, "w", encoding="utf-8") as f:
        f.write(xml)

    # Génère tous les ajouts
    updates = get_all_updates()
    with open(OUTPUT_UPDATES, "w", encoding="utf-8") as f:
        import json
        json.dump(updates, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    sys.exit(main())
