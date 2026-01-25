# Spotify Playlist Automation (Replace, 05:00 Europe/Berlin)

Dieses Repo verwaltet 5 Spotify-Playlists automatisch aus einer Master-Playlist (`MASTER`).
Die Ziel-Playlists werden **täglich um 05:00 Uhr (Europe/Berlin)** komplett neu aufgebaut (**Replace-Methode**).

## Status (Hauptstrang)
- Phase 1 (GitHub vorbereitet): ✅ erledigt
- Phase 2 (Spotify Developer App erstellen): ⛔ aktuell blockiert durch Spotify ("New integrations on hold")
- Phase 3 (Scharf schalten): ⬜ offen

Solange Spotify keine neuen Apps zulässt, bleibt das Projekt im **DRY RUN**.

## Was wird verwaltet?
Quelle:
- `MASTER` (wird **nur gelesen**, niemals verändert)

Ziel-Playlists (werden vom Script verwaltet):
- `Good Vibes Rollin'`
- `Just fall.`
- `Läuft einfach.`
- `into the mind`
- `feel the exhale`


## Regeln (Energy / Valence)
- Good Vibes Rollin':  energy >= 0.80  AND valence >= 0.50
- Just fall.:          energy >= 0.80  AND valence <  0.50
- Läuft einfach.:      0.55 <= energy < 0.80 AND valence >= 0.50
- into the mind:       0.55 <= energy < 0.80 AND valence <  0.50
- feel the exhale:     energy <  0.55


## Zeitplan (05:00 Berlin, DST-sicher)
GitHub cron läuft in UTC und kennt keine Sommerzeit.
Der Workflow läuft deshalb 2× täglich (03:00 und 04:00 UTC).
`sorter.py` führt nur dann aus, wenn es **exakt 05:00** in Europe/Berlin ist.

## Sicherheit
- `MASTER` wird niemals beschrieben.
- Im aktuellen Zustand: `DRY_RUN=true` → keine Änderungen an Spotify möglich.
- Spotify-Zugangsdaten werden **nur** als GitHub Secrets gespeichert (nie im Code).

## Notfall-Stopp (sofort)
1) GitHub: Repo → Actions → Workflow deaktivieren **oder** Repo löschen.
2) Spotify: Account → Apps → Zugriff der App entziehen (sobald eine App existiert).
3) Ziel-Playlists in Spotify löschen (optional).

## Wiedereinstieg (wenn Spotify wieder Apps erlaubt)
1) Spotify Developer Dashboard: App erstellen → Client ID/Secret
2) Einmalig OAuth/Token holen (mit Anleitung aus dem Chat)
3) GitHub Secrets setzen:
   - `SPOTIFY_ACCESS_TOKEN`
   - `SPOTIFY_USER_ID`
4) In `.github/workflows/schedule.yml` `DRY_RUN` von `"true"` auf `"false"` setzen
5) Actions → Run workflow (Testlauf)
