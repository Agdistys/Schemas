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
    """Dernière date ISO 8601 depuis git, sinon mtime fichier. Debug prints."""
    print(f"DEBUG: git_lastmod called for path: {path}", file=sys.stderr)
    try:
        # Assure-toi que le path est absolu pour git
        abs_path = os.path.abspath(path)
        ts = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "--", abs_path],
            stderr=subprocess.STDOUT,  # Capture stderr pour debug
            cwd=os.getcwd()  # Force cwd
        ).decode().strip()
        if ts:
            print(f"DEBUG: Git ts found: {ts}", file=sys.stderr)
            return ts
    except subprocess.CalledProcessError as e:
        print(f"DEBUG: Git subprocess error for {path}: {e.returncode}, output: {e.output.decode()}", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: Unexpected error in git_lastmod for {path}: {e}", file=sys.stderr)
    
    # Fallback mtime
    try:
        if os.path.exists(path):
            dt = datetime.datetime.fromtimestamp(os.path.getmtime(path), tz=datetime.timezone.utc)
            ts = dt.replace(microsecond=0).isoformat() + "Z"
            print(f"DEBUG: Using mtime: {ts}", file=sys.stderr)
            return ts
        else:
            print(f"DEBUG: Path {path} does not exist for mtime", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: mtime error: {e}", file=sys.stderr)
    
    # Ultimate fallback
    ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    print(f"DEBUG: Using now: {ts}", file=sys.stderr)
    return ts

def iter_images(root="."):
    """Itère sur les images, debug count."""
    images = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != ".git"]
        for fn in filenames:
            if fn.startswith("."):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in IMAGE_EXT:
                rel = os.path.relpath(os.path.join(dirpath, fn), root)
                images.append(rel)
    print(f"DEBUG: Found {len(images)} images", file=sys.stderr)
    return sorted(images)

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
    """Récupère les 10 derniers commits, debug."""
    print("DEBUG: Starting get_latest_commits", file=sys.stderr)
    try:
        result = subprocess.run(['git', 'log', '--pretty=format:%s|%ad', '-n', '10'],
                               capture_output=True, text=True, check=True, cwd=os.getcwd())
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
        print(f"DEBUG: Found {len(updates)} commits", file=sys.stderr)
        return updates
    except subprocess.CalledProcessError as e:
        print(f"DEBUG: Git log called error: {e.returncode}, output: {e.output}", file=sys.stderr)
    except ValueError as e:  # Pour strptime
        print(f"DEBUG: Date parse error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: Unexpected in get_latest_commits: {e}", file=sys.stderr)
    return []

# --- SECTION 3 : FONCTION PRINCIPALE ---
def main():
    print("DEBUG: Starting main()", file=sys.stderr)
    try:
        # Images
        images = list(iter_images("."))
        entries = [make_entry(rel) for rel in images]
        print(f"DEBUG: Generated {len(entries)} entries", file=sys.stderr)
        
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' +
            "".join(entries) +
            "</urlset>\n"
        )
        with open(OUTPUT_SITEMAP, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"DEBUG: Wrote sitemap with {len(entries)} urls", file=sys.stderr)

        # Updates
        updates = get_latest_commits()
        with open(OUTPUT_UPDATES, "w", encoding="utf-8") as f:
            json.dump(updates, f, ensure_ascii=False, indent=2)
        print(f"DEBUG: Wrote updates with {len(updates)} items", file=sys.stderr)

        print("DEBUG: All good, exit 0", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"ERREUR FATALE: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
