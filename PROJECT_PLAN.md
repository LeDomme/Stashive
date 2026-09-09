# Stashive — Gesamtplan

## 1. Vision

Stashive wird eine selbst gehostete Webanwendung zur Verwaltung physischer Sammlungen.

Der erste Fokus ist die Verwaltung von:
- DVDs
- Blu-rays
- UHD Blu-rays

Danach folgt:
- Brettspiele

Langfristig soll Stashive auch andere physische Sammlungen verwalten können, ohne dass der Kern auf Filme oder Brettspiele fest verdrahtet wird.

Die zentrale Frage lautet immer:

> Was ist der Gegenstand, welche konkrete Edition besitze ich, wo befindet sich mein physisches Exemplar und welchen aktuellen Zustand hat es?

## 2. Kernfunktionen

### Sammlungen
- mehrere Sammlungen pro Installation
- Sammlungen können unterschiedliche Typen besitzen
- Sammlungen können mit anderen Benutzern geteilt werden
- Rollen: Owner, Admin, Editor, Viewer

### Katalog / Inventar
- Trennung zwischen Werk/Titel, Edition und physischem Exemplar
- mehrere Editionen desselben Titels
- mehrere physische Exemplare derselben Edition
- eigene Notizen
- Zustand
- Kaufdaten später optional
- Tags später optional

### Standorte
Hierarchischer Standortbaum, z. B.:

```text
Haus
└── Keller
    └── Regal 2
        ├── Kiste BD-001
        └── Kiste BD-002
```

Funktionen:
- Gegenstand verschieben
- mehrere Gegenstände gemeinsam verschieben
- Inhalt eines Standortes anzeigen
- druckbare Inventarliste
- QR-Code für Standorte/Kisten

### Ausleihen
- Gegenstand ausleihen
- Freitextname oder später optional interner Benutzer
- Ausleihdatum
- erwartetes Rückgabedatum
- Rückgabedatum
- Notiz
- vollständige Historie

### Barcode-Aufnahme
- EAN / UPC scannen
- Produkt-/Editionsdaten über austauschbaren Provider suchen
- Film-/Spieldaten über spezialisierten Metadatenprovider ergänzen
- Ergebnis vor dem Speichern bestätigen
- Zielstandort vor dem Scan festlegen
- schneller Mehrfachscan einer ganzen Kiste

### Metadaten
- Provider-Abstraktion
- lokaler Cache
- manuelle Änderungen haben Vorrang
- Provider-Refresh darf manuelle Felder nicht still überschreiben

### Kostenregel für Barcode-Lookups
Barcode-Lookup muss im normalen Betrieb ohne kostenpflichtiges Abo nutzbar sein.

Geplanter Fallback:
```text
lokaler Cache
-> UPCitemdb Free
-> optional UPC Database Free
-> manuelle Eingabe / manuelles Matching
```

Kostenpflichtige Barcode-Provider gehören nicht zum erforderlichen Standardbetrieb.

## 3. Medienmodell

Für Filmmedien gilt:

```text
Film / Werk
└── Edition / Produkt
    └── physisches Exemplar
```

Beispiel:

```text
Alien (1979)
├── Blu-ray DE
│   └── EAN 123...
│       └── Exemplar #1 -> Keller > BD-001
└── UHD Steelbook DE
    └── EAN 456...
        └── Exemplar #1 -> Wohnzimmer > Regal
```

### Film-Metadaten
Geplant:
- Titel
- Originaltitel
- Jahr
- Beschreibung
- Genres
- Laufzeit
- Regie
- Cast
- Poster
- externe IDs

### Editionsdaten
Geplant:
- Barcode
- Medium
- Region
- Publisher/Distributor
- Release-Datum
- Editionsname
- Disc-Anzahl

Medientypen:
- DVD
- Blu-ray
- UHD Blu-ray
- HD DVD
- VHS
- Other

### Rip-Status
Nicht als Boolean modellieren.

Geplanter Status:
- `not_ripped`
- `queued`
- `ripped`
- `verified`
- `failed`
- `not_needed`

Später optional:
- Rip-Datum
- Dateipfad
- Format
- Dateigröße
- externe Media-Server-Verknüpfung

## 4. Brettspielmodell

Das Brettspielmodul kommt nach dem stabilen Medienworkflow.

Geplante Metadaten:
- Name
- Erscheinungsjahr
- Spieler min/max
- Alter
- Spieldauer
- Designer
- Verlag
- Kategorien
- Mechaniken
- Cover
- externe IDs

Besitz-/Inventardaten bleiben im generischen Kern.

Später möglich:
- Vollständigkeitsstatus
- fehlende Teile
- Erweiterungen
- Sprachversion
- Edition

## 5. Architektur

```text
Vue 3 / TypeScript
        |
        | REST / JSON
        v
FastAPI
        |
        +-- Services / Domain
        |
        +-- Metadata Provider
        |
        +-- SQLAlchemy
                |
                +-- SQLite (Default)
                +-- PostgreSQL (optional später)
```

Monorepo:

```text
backend/
frontend/
docs/
assets/
```

## 6. Datenbankstrategie

### Default
SQLite.

Anforderungen:
- WAL
- Foreign Keys
- busy timeout
- DB-Pfad per Konfiguration
- DB-Datei persistent außerhalb des Container-Layers

### Später
PostgreSQL optional.

Daher von Anfang an vermeiden:
- SQLite-only Business-SQL
- PostgreSQL ARRAY
- PostgreSQL ENUM
- JSONB-Abhängigkeiten
- Postgres-only Volltextsuche im Kern

Alembic wird ab der ersten Schema-Version verwendet.

## 7. Auth und Multiuser

Lokale Benutzerverwaltung.

Registrierung:
- keine öffentliche/Self-Service-Registrierung nach dem Erstsetup
- wenn noch kein Benutzer existiert, erzeugt Stashive einen einmaligen Setup-Token
- der Token wird dem Betreiber über Server-/Container-Logs angezeigt
- gespeichert wird nur ein Hash des Tokens
- über eine Setup-Seite werden Setup-Token und Zugangsdaten für den ersten Benutzer eingegeben
- der erste Benutzer wird Instance Administrator
- der Setup-Token ist nach erfolgreicher Erstellung sofort ungültig
- sobald ein Benutzer existiert, ist der Bootstrap-Endpunkt deaktiviert
- weitere Benutzer werden ausschließlich durch einen Administrator angelegt

Ziel:
- sichere Cookie-basierte Sessions
- kein langfristiges Token in LocalStorage
- serverseitige Rechteprüfung
- Collection ACLs

Rollen:
- Owner
- Admin
- Editor
- Viewer

## 8. UI-Struktur

Geplanter Hauptaufbau:

```text
Dashboard

SAMMLUNGEN
  Filme
  Brettspiele

INVENTAR
  Standorte
  Ausgeliehen
  Barcode Scan

TOOLS
  Import
  Export
  Drucken

ADMIN
  Benutzer
  Einstellungen
  Metadaten
```

Die sichtbaren Punkte hängen später von Rolle und aktivierten Features ab.

## 9. Wichtige UX-Flows

### Schnellscan

```text
Barcode Scan öffnen
-> Zielstandort wählen
-> Barcode scannen
-> Produkt erkennen
-> Metadaten-Kandidat ermitteln
-> bestätigen / korrigieren
-> speichern
-> sofort nächstes Objekt scannen
```

### Standort

```text
Standort öffnen
-> Inhalt sehen
-> drucken
-> QR-Code erzeugen
-> Elemente markieren
-> gesammelt verschieben
```

### Ausleihen

```text
Exemplar öffnen
-> Ausleihen
-> Name
-> optional Rückgabedatum
-> speichern
```

Rückgabe erzeugt einen Historieneintrag statt vorhandene Daten zu überschreiben.

## 10. Nicht-Ziele für den Anfang

Nicht in den frühen MVP ziehen:
- Redis
- Microservices
- Elasticsearch
- komplexe Event-Systeme
- Pluginsystem
- benutzerdefinierte EAV-Felder
- native mobile App
- HA/Clusterbetrieb
- automatische Jellyfin-Synchronisierung
- komplexer PDF-Designer

## 11. Roadmap

Siehe `docs/ROADMAP.md`.

Kurzfassung:

- v0.1 Foundation
- v0.2 Movie Core
- v0.3 Barcode & Metadata
- v0.4 Locations & Printing
- v0.5 Loans
- v0.6 Board Games
- v0.7 Bulk / Import / Export
- v0.8 PWA & Scan Hardening
- v0.9 Security / Permissions / Polish
- v1.0 Stable

## 12. Qualitätsziel

Stashive soll sich wie eine fertige Sammlungsanwendung anfühlen und nicht wie ein Datenbank-Frontend.

Besonders wichtig:
- schnelle Bedienung
- gute Filter
- mobile Scan-Nutzung
- nachvollziehbare Rechte
- einfache Backups
- einfache Self-Hosting-Installation
- migrationssichere Datenhaltung


## 13. Lizenz

Stashive verwendet wie Meshive:

```text
AGPL-3.0-only
```

Repository- und Paketmetadaten verwenden den SPDX-Identifier `AGPL-3.0-only`.
