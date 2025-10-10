#!/usr/bin/env python3
import os
import sys
import subprocess
import datetime
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape
import json

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
    try:
        dt = datetime.datetime.fromtimestamp(os.path.getmtime(path), tz=datetime.timezone.utc)
        return dt.replace(microsecond=0).isoformat() + "Z"
    except Exception:
        return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"  # Fallback actuel si erreur

def iter_images(root="."):
    """Itère sur les images, ignorant .git et fichiers cachés."""
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
    """Crée une entrée XML pour l'image."""
    encoded = quote(rel_path.replace(os.sep, "/"), safe="/")
    url = f"{BASE_URL}/{encoded}"
    lastmod = git_lastmod(rel_path)
    url_xml = xml_escape(url)
    caption_xml = xml_escape(os.path.basename(rel_path))
    return (
        "  <url>\n"
        f"    <loc>{url_xml}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        "    <image:image>\n"
        f"      <image:loc>{url_xml}</image:loc>\n"
        f"      <image:caption>{caption_xml}</image:caption>\n"
        "    </image:image>\n"
        "  </url>\n"
    )

# --- SECTION 2 : FONCTION POUR LES DERNIERS AJOUTS ---
def get_latest_commits():
    """Récupère les 10 derniers commits avec message et date formatée, gérant erreurs."""
    try:
        result = subprocess.run(['git', 'log', '--pretty=format:%s|%ad', '-n', '10'],
                               capture_output=True, text=True, check=True)
        commits = result.stdout.strip().split('\n')
        updates = []
        for commit in commits:
            if commit:
                parts = commit.split('|', 1)
                message = parts[0]
                date_str = parts[1] if len(parts) > 1 else ""
                if date_str:
                    date = datetime.datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y %z').strftime('%d/%m/%Y')
                else:
                    date = datetime.datetime.utcnow().strftime('%d/%m/%Y')
                updates.append({"title": message, "date": date})
        return updates
    except Exception as e:
        print(f"Erreur git log: {e}", file=sys.stderr)
        return []  # Retourne vide si erreur, évite crash

# --- SECTION 3 : FONCTION PRINCIPALE ---
def main():
    try:
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

        # Génère les updates
        updates = get_latest_commits()
        with open(OUTPUT_UPDATES, "w", encoding="utf-8") as f:
            json.dump(updates, f, ensure_ascii=False, indent=2)

        return 0
    except Exception as e:
        print(f"Erreur principale: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
