# Stashive mit Codex starten

## 1. Repository anlegen

Leeres Repository für `Stashive` anlegen und dieses Starterpaket in den Repository-Root kopieren.

Empfohlener Startzustand:

```text
Stashive/
├── AGENTS.md
├── CODEX_BOOTSTRAP_PROMPT.md
├── PROJECT_PLAN.md
├── README.md
├── START_HERE.md
├── TASKS.md
├── assets/
└── docs/
```

## 2. Initialer Commit

Vor der ersten Codex-Implementierung ist ein sauberer Dokumentations-Baseline-Commit sinnvoll:

```bash
git add .
git commit -m "docs: add Stashive project specification"
```

## 3. Erste Codex-Aufgabe

Codex soll zuerst ausschließlich das Repository-Grundgerüst erstellen.

Prompt:
- `CODEX_BOOTSTRAP_PROMPT.md`

Wichtig:
- noch keine Auth
- noch keine Movie-Datenbank
- noch keine Barcode-API
- noch kein Redis
- noch kein Production-Docker

## 4. Danach

Die nächsten Aufgaben stehen in `TASKS.md`.

Empfohlene Reihenfolge:

```text
T01 Repository Foundation
T02 Database Core
T03 Local Authentication
T04 Collections & ACL
T05 Location Tree
T06 Generic Inventory Core
T07 Movie Domain
T08 Movie UI
T09 Metadata Providers
T10 Barcode Intake
T11 Printing / QR
T12 Loans
```

Jede Aufgabe einzeln umsetzen und testen.

## 5. Arbeitsweise

Für größere Aufgaben:

```text
feature/0.1-database-core
feature/0.1-auth
feature/0.1-collections
...
```

Nicht mehrere große Domänen in einen PR packen.

Wenn du wie bei Meshive mit Worktrees arbeitest, sollte Codex ausschließlich im Worktree der aktuellen Aufgabe arbeiten.


## Festgelegte Auth-Richtung

Beim Auth-Milestone verwendet Stashive einen einmaligen Setup-Token für den ersten Benutzer. Danach gibt es keine öffentliche Registrierung; weitere Benutzer werden nur durch Instance Administratoren angelegt.
