import os
import json
import time
import datetime as dt
from zoneinfo import ZoneInfo
import requests

# ============================================================
# CONFIG — Playlist-Regeln (DEIN KONZEPT)
# ============================================================

TARGET_PLAYLISTS = {
    "Good Vibes Rollin'":  lambda f: f["energy"] >= 0.80 and f["valence"] >= 0.50,
    "Just fall.":          lambda f: f["energy"] >= 0.80 and f["valence"] <  0.50,
    "Läuft einfach.":      lambda f: 0.55 <= f["energy"] < 0.80 and f["valence"] >= 0.50,
    "into the mind":       lambda f: 0.55 <= f["energy"] < 0.80 and f["valence"] <  0.50,
    "feel the exhale":     lambda f: f["energy"] <  0.55,
}


MASTER_PLAYLIST_NAME = os.getenv("MASTER_PLAYLIST_NAME", "MASTER")

# SAFETY: Master wird NIEMALS beschrieben
SAFETY_NO_WRITE_TO_MASTER = True

# ============================================================
# ZEITSTEUERUNG — 05:00 Europe/Berlin (DST-sicher)
# ============================================================

BERLIN = ZoneInfo("Europe/Berlin")
RUN_AT_LOCAL_HOUR = 5
RUN_AT_LOCAL_MIN = 0

def now_berlin():
    return dt.datetime.now(tz=BERLIN)

def should_run_now():
    t = now_berlin()
    return (t.hour == RUN_AT_LOCAL_HOUR and t.minute == RUN_AT_LOCAL_MIN)

# ============================================================
# DRY RUN (IMMER TRUE BIS SPOTIFY FREIGIBT)
# ============================================================

DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")

# ============================================================
# SPOTIFY API
# ============================================================

SPOTIFY_TOKEN = os.getenv("SPOTIFY_ACCESS_TOKEN", "").strip()
SPOTIFY_USER_ID = os.getenv("SPOTIFY_USER_ID", "").strip()

API = "https://api.spotify.com/v1"

def die(msg):
    raise SystemExit(msg)

def headers():
    if not SPOTIFY_TOKEN:
        die("Missing SPOTIFY_ACCESS_TOKEN")
    return {
        "Authorization": f"Bearer {SPOTIFY_TOKEN}",
        "Content-Type": "application/json",
    }

def request(method, url, **kwargs):
    for attempt in range(5):
        r = requests.request(method, url, headers=headers(), timeout=30, **kwargs)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", "2")) + 1)
            continue
        if r.status_code >= 500:
            time.sleep(2 * (attempt + 1))
            continue
        return r
    return r

# ============================================================
# SPOTIFY HELPER
# ============================================================

def paginate(url):
    while url:
        r = request("GET", url)
        if r.status_code != 200:
            die(f"Pagination failed: {r.status_code}")
        data = r.json()
        yield data
        url = data.get("next")

def get_me():
    r = request("GET", f"{API}/me")
    if r.status_code != 200:
        die("/me failed")
    return r.json()

def find_playlist(name):
    url = f"{API}/me/playlists?limit=50"
    for page in paginate(url):
        for p in page.get("items", []):
            if p.get("name") == name:
                return p.get("id")
    return None

def create_playlist(name):
    payload = {
        "name": name,
        "public": False,
        "description": "Auto-managed (Replace)",
    }
    r = request("POST", f"{API}/users/{SPOTIFY_USER_ID}/playlists", data=json.dumps(payload))
    if r.status_code not in (200, 201):
        die("Playlist creation failed")
    return r.json()["id"]

def get_tracks(pid):
    tracks = []
    url = f"{API}/playlists/{pid}/tracks?limit=100&fields=items(track(id,uri,is_local)),next"
    for page in paginate(url):
        for it in page.get("items", []):
            tr = it.get("track")
            if not tr or tr.get("is_local"):
                continue
            tracks.append({"id": tr["id"], "uri": tr["uri"]})
    return tracks

def get_features(ids):
    feats = {}
    for i in range(0, len(ids), 100):
        r = request("GET", f"{API}/audio-features?ids={','.join(ids[i:i+100])}")
        if r.status_code != 200:
            die("Audio features failed")
        for f in r.json().get("audio_features", []) or []:
            if f and f.get("id"):
                feats[f["id"]] = {
                    "energy": float(f.get("energy") or 0),
                    "valence": float(f.get("valence") or 0),
                }
    return feats

def replace_playlist(pid, uris):
    if DRY_RUN:
        print(f"[DRY_RUN] Would replace {pid} with {len(uris)} tracks")
        return
    r = request("PUT", f"{API}/playlists/{pid}/tracks", data=json.dumps({"uris": uris[:100]}))
    if r.status_code not in (200, 201):
        die("Replace failed")
    for i in range(100, len(uris), 100):
        r = request("POST", f"{API}/playlists/{pid}/tracks",
                    data=json.dumps({"uris": uris[i:i+100]}))
        if r.status_code not in (200, 201):
            die("Append failed")

# ============================================================
# MAIN
# ============================================================

def main():
    if not should_run_now():
        print("Not 05:00 Berlin — exit")
        return

    me = get_me()
    uid = me["id"]

    master_id = find_playlist(MASTER_PLAYLIST_NAME)
    if not master_id:
        die("Master playlist not found")

    tracks = get_tracks(master_id)
    feats = get_features([t["id"] for t in tracks])

    buckets = {k: [] for k in TARGET_PLAYLISTS}
    for t in tracks:
        f = feats.get(t["id"])
        if not f:
            continue
        for name, rule in TARGET_PLAYLISTS.items():
            if rule(f):
                buckets[name].append(t["uri"])
                break

    for name, uris in buckets.items():
        pid = find_playlist(name)
        if not pid:
            if DRY_RUN:
                print(f"[DRY_RUN] Would create playlist {name}")
                continue
            pid = create_playlist(name)
        replace_playlist(pid, uris)

    print("Done.")

if __name__ == "__main__":
    main()
