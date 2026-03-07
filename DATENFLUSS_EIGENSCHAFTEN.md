# Datenfluss: IFC-Export → SBERT Mapping → Dashboard

## 1. IFC-EXPORT (ifc_extraction_core.py)

### Direkt aus IFC-Element extrahiert (Basis-Attribute):
```
IfcEntity              (z.B. IfcBeam, IfcColumn, IfcWall)
PredefinedType        (z.B. PIERCAP, CANTILEVER, LOAD_BEARING)
Name
Description
GUID
HasModeledRebar       (boolean flag für modellierte Bewehrung)
```

### Aus PropertySets extrahiert (DEFAULT_PROPERTY_FIELDS):
```
Description
Status
CastingMethod
StrengthClass
ExposureClass
Length
NetVolume
GrossVolume
ReinforcementVolumeRatio
Height                (zusätzlich extrahiert)
NetArea               (zusätzlich extrahiert)
Count                 (nur bei IfcReinforcingBar)
Weight                (nur bei IfcReinforcingBar)
```

### Berechnete Felder (COMPUTED_FIELDS):
```
Durchmesser           (berechnet aus Length + NetVolume für DIAMETER_CANDIDATE_ENTITIES)
Ansichtsfläche        (berechnet für IfcWall: Length × Height; für IfcCovering: NetArea)
```

### Material-Informationen:
```
Material              (Namen aus IfcMaterial Definitions)
MaterialLayerIndex    (Index für mehrschichtige Materialien: 1, 2, 3, ...)
MaterialLayerThickness
```

---

## 2. SBERT MAPPING INPUT (Sentence_Transformer_V00.py)

### Felder für Bi-Encoder (IFC_EXPORT_FIELDS):
Diese Felder werden zu einer Suchquery zusammengefügt:
```
IfcEntity
PredefinedType
Name
Material
Durchmesser
CastingMethod
StrengthClass
```

**Hinweis:** Diese Felder werden konkateniert zu einem Query-Text für die SBERT-Ähnlichkeitssuche gegen die KBOB-Datenbank

### Cross-Encoder Reranking:
```
Input:  Top-K Ergebnisse vom Bi-Encoder (TOP_K_RESULTS = 30)
Scores: RERANK_TOP_N = 30
Output: Re-ranked Material-Matches mit normalisierten Scores [0, 1]
```

---

## 3. DASHBOARD DARSTELLUNG (tab_ai_mapping.py)

### Aufbereitete Basis-Spalten für die UI (base_cols):
```
IfcEntity
PredefinedType
Name
GUID
MaterialLayerIndex
Description
Material
Durchmesser
top_k_matches          (SBERT Match-Ergebnisse mit Scores)
```

### Element-Label im Dashboard:
Zusammengestellt aus (wenn Wert gültig ist):
```
IfcEntity | PredefinedType | Name | Description | Material | CastingMethod | StrengthClass | Ø Durchmesser
```

### Zusätzliche im Merge angezeigte Felder:
```
Material KBOB          (Nutzer-Auswahl)
AI Score               (Score des ausgewählten Materials)
```

### Übersicht-Tabelle (subheader "Übersicht"):
```
IfcEntity
PredefinedType
Name
Description            (umbenannt zu "Beschrieb")
Durchmesser
Material KBOB          (Nutzer-Auswahl)
AI Score               (formatiert auf 3 Dezimalstellen)
```

---

## 4. FILTERN & AUSSCHLÜSSE

### Im Dashboard nicht angezeigt:
```
Status
StructuralClass
ExposureClass
CastingMethod
StrengthClass
GUID                   (nur intern für Viewer-Linking)
top_k_matches          (nur für Material-Dropdown-Vorschläge)
Height
NetArea
Count, Weight
ReinforcementVolumeRatio
MaterialLayerThickness
```

### Ausgeschlossene Zeilen:
```
MaterialLayerIndex == "R"  (synthetische Bewehrungs-Zeilen, nur für Charts)
```

---

## 5. REINFORCEMENT-SPEZIFISCHE FELDER

### Im SBERT-Prozess berechnet (add_reinforcement_info):
```
is_concrete            (boolean: Material-Check gegen CONCRETE_KEYWORDS)
has_modeled_rebar      (boolean: aus HasModeledRebar Flag)
reinforcement_ratio_source    ("ifc" | "default")
reinforcement_ratio_kg_m3     (float)
reinforcement_mass_kg  (berechnet: volume_m3 × ratio)
reinforcement_status   ("explicit" | "assumed" | "none" | "no_material")
```

### Im Dashboard vom Nutzer eingegeben:
```
reinforcement_accepted       (checkbox)
reinforcement_ratio_kg_m3    (number_input, optional)
reinforcement_source         (tracking: "user" | "ifc" | "default")
```

---

## 6. ZUSAMMENFASSUNG: FELDABDECKUNG

```
┌────────────────────────────────────────────────────────────────┐
│                        IFC-EXPORT                              │
├──────────────────────┬──────────────────────┬──────────────────┤
│ ~29 Felder           │ Basis + Properties   │ SBERT Input      │
│ (JSONL-Datei)        │ + Material + Berechnet                  │
└──────────────────────┴──────────────────────┴──────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│                     SBERT PROCESSING                           │
├──────────────────────┬──────────────────────┬──────────────────┤
│ 9 Felder             │ Konkateniert zu      │ Top-K Matches    │
│ (IFC_EXPORT_FIELDS)  │ Query-Text           │ mit Scores       │
└──────────────────────┴──────────────────────┴──────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│                   DASHBOARD ANZEIGE                            │
├──────────────────────┬──────────────────────┬──────────────────┤
│ 9 Felder angezeigt   │ Label: 8 Felder      │ Tabelle: 7 Felder│
│ (base_cols)          │ kombiniert           │                  │
└──────────────────────┴──────────────────────┴──────────────────┘
```

---

## 7. KEINE WERTE: NUR STRUKTUR

Alle Werte werden nach diesen Kriterien gefiltert (is_valid-Check):
```
- value NOT IN (None, "", [], {})
- string_value.strip() NOT empty
- normalized string NOT IN {"nan", "none", "null", "undefined", "notdefined", "n/a", "na", "-"}
```
