# Helter Skelter — a virtual visit

An interactive, room-by-room virtual tour of **“Helter Skelter: Arthur Jafa and Richard Prince”**
(curated by Nancy Spector, Fondazione Prada, Ca' Corner della Regina, Venice, 9 May – 23 Nov 2026),
built from photos taken in the exhibition on 15 November 2026.

- Clickable floor plans of both floors (after the booklet plans), with visited rooms tracked
- 16 real rooms + **Room 17**, an imagined virtual annex of works not shown in Venice
- 43 works, each with a short concept, medium, photos and "in dialogue with" links
- 11 thematic threads (cars & the road, monstrosity, protest, the burning sun, …)
- Notes on the palazzo itself

Plain static site: open `index.html` or serve the folder (`python3 -m http.server`).
Content lives in `data.js`. Concepts are original summaries, not the gallery's wall texts.
Photos are personal snapshots for private use.

## Videos
Rooms 9, 12 and 16 include short clips filmed in the show (`media/`). Every video work has a
**My clip / YouTube** switcher: the YouTube tab opens a YouTube search for the work plus official
museum pages. Full Jafa videos aren't officially on YouTube, so nothing pirated is embedded.

## Deploy (GitHub Pages)
Deployed automatically by `.github/workflows/pages.yml` to https://dmitrii-volokitin-job.github.io/jafa-prince-venice/
