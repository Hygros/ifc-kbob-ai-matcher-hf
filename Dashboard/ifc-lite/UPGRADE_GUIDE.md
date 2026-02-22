# IFClite Update-Anleitung (für Streamlit-Integration)

Diese Anleitung beschreibt den **sicheren Update-Prozess** für `Dashboard/ifc-lite` inklusive der im Dashboard genutzten Selektionsfunktionen.

---

## 1) Ziel und Scope

Diese Schritte aktualisieren nur das Frontend-Projekt:

- `Dashboard/ifc-lite`

Die Streamlit-Integration liegt in:

- `Dashboard/services/viewer.py`
- `Dashboard/ui/tab_ai_mapping.py`
- `Dashboard/ifc-lite/src/components/streamlit/StreamlitBridge.tsx`

Diese Dateien dürfen beim Update **nicht überschrieben** werden.

---

## 2) Vorbereitung

1. Terminal im Repo öffnen.
2. In den Projektordner wechseln:

```powershell
cd Dashboard/ifc-lite
```

1. Aktuellen Stand sichern (Git empfohlen):

```powershell
git status
git add .
git commit -m "chore: backup before ifc-lite update"
```

1. Aktuelle Versionen prüfen:

```powershell
npm outdated
```

---

## 3) Update durchführen

### Option A: Voll-Update (einfach)

```powershell
npm update
npm install
```

### Option B: Gezieltes Update der Kernpakete (empfohlen)

```powershell
npm install @ifc-lite/parser@latest @ifc-lite/geometry@latest @ifc-lite/renderer@latest @ifc-lite/server-client@latest @ifc-lite/query@latest @ifc-lite/ifcx@latest
npm install
```

Hinweis: `npm install` am Ende sorgt für konsistentes `package-lock.json`.

---

## 4) Build-Validierung (Windows)

Im Template kann `npm run build` auf Windows wegen Bash-Syntax fehlschlagen.
Nutze deshalb für die Prüfung:

```powershell
npx vite build
```

Optional Dev-Start:

```powershell
npm run dev -- --host 127.0.0.1 --port 3000 --strictPort
```

---

## 5) Funktionstest im Dashboard (Pflicht)

Streamlit neu starten:

```powershell
python -m streamlit run Dashboard/app_with_viewer.py
```

Dann im Tab **AI-Mapping** diese 4 Fälle testen:

1. **Selectbox → Viewer**
   - Material/Element in Selectbox wählen.
   - Entsprechendes Element wird im Viewer selektiert.

2. **Viewer → Linke Markierung**
   - Element im Viewer anklicken.
   - Passende Elementzeile links wird farbig markiert.

3. **Outside Click → Deselect**
   - Irgendwo außerhalb Viewer/Selectbox im Dashboard klicken.
   - Viewer-Selektion wird aufgehoben.

4. **Neue Selectbox-Auswahl nach Deselect**
   - Danach erneut in Selectbox wählen.
   - Viewer selektiert wieder korrekt.

Wenn alle 4 Punkte funktionieren, ist das Update erfolgreich.

---

## 6) Typische Bruchstellen nach Update

Wenn etwas nicht mehr geht, zuerst diese APIs prüfen:

- `useViewerStore(...selectedEntityIds, selectedEntity...)`
- `resolveGlobalIdFromModels(...)`
- `entities.getGlobalId(...)`
- `entities.getExpressIdByGlobalId(...)`
- `loadFile(...)`

Und Bridge-Nachrichten prüfen:

- `ifc-lite-select-guid`
- `ifc-lite-select-guids`
- `ifc-lite-viewer-selection`

---

## 7) Rollback (wenn Update Probleme macht)

Im Projektordner:

```powershell
cd Dashboard/ifc-lite
git restore package.json package-lock.json
npm install
```

Wenn nötig gesamten Stand zurücksetzen:

```powershell
git reset --hard HEAD~1
npm install
```

---

## 8) Checkliste für Copilot (zum Wiederverwenden)

Wenn du diese Datei später an Copilot gibst, mit diesem Auftrag:

- "Bitte führe die Schritte aus `Dashboard/ifc-lite/UPGRADE_GUIDE.md` aus,
  update ifc-lite sicher und validiere die 4 AI-Mapping-Selektionsfälle."

Damit ist klar, dass nicht nur Build, sondern auch die Dashboard-Interaktion geprüft werden muss.
