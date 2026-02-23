# Filedrop Configuratie voor UZS XMLator

## Overzicht

De gegenereerde XML-bestanden worden automatisch naar de juiste UZS filedrop locatie geplaatst op basis van:
1. **Omgeving** (testomgeving): UZSTA_OMG, UZSA_ACC1, UZSC_ACC1, UZSD_ACC1, UZSP_ACC1
2. **Berichttype**: OTP3, ZBM, VM

## Configuratie (`web/instellingen.json`)

```json
{
  "omgeving": "UZSTA_OMG",
  "filedrop_locaties": {
    "UZSTA_OMG": {
      "OTP3": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\UZSTA_OMG\\UwvZwMelding_MQ_V0428",
      "ZBM": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\UZSTA_OMG\\v0428\\UwvZwMelding",
      "VM": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\UZSTA_OMG\\v0428\\UwvZwMelding"
    },
    "UZSA_ACC1": {
      "OTP3": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\UZSA_ACC1\\UwvZwMelding_MQ_V0428",
      "ZBM": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\UZSA_ACC1\\v0428\\UwvZwMelding",
      "VM": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\UZSA_ACC1\\v0428\\UwvZwMelding"
    },
    "UZSC_ACC1": {...},
    "UZSD_ACC1": {...},
    "UZSP_ACC1": {...}
  }
}
```

## Aanpassen van de Omgeving

### 1. Via `instellingen.json`
Wijzig het `"omgeving"` veld naar een van de geconfigureerde omgevingen:

```json
{
  "omgeving": "UZSA_ACC1",
  ...
}
```

### 2. Via Omgevingsvariabele (optioneel in toekomst)
De applicatie zou kunnen uitgebreid worden om omgeving uit een omgevingsvariabele te lezen:

```powershell
$env:UZS_ENVIRONMENT = "UZSA_ACC1"
```

## Filedrop Paden per Omgeving

| Omgeving | OTP3 (Digipoort) | ZBM/VM |
|----------|------------------|--------|
| UZSTA_OMG | `.../UZSTA_OMG/UwvZwMelding_MQ_V0428` | `.../UZSTA_OMG/v0428/UwvZwMelding` |
| UZSA_ACC1 | `.../UZSA_ACC1/UwvZwMelding_MQ_V0428` | `.../UZSA_ACC1/v0428/UwvZwMelding` |
| UZSC_ACC1 | `.../UZSC_ACC1/UwvZwMelding_MQ_V0428` | `.../UZSC_ACC1/v0428/UwvZwMelding` |
| UZSD_ACC1 | `.../UZSD_ACC1/UwvZwMelding_MQ_V0428` | `.../UZSD_ACC1/v0428/UwvZwMelding` |
| UZSP_ACC1 | `.../UZSP_ACC1/UwvZwMelding_MQ_V0428` | `.../UZSP_ACC1/v0428/UwvZwMelding` |

## Werking in de Applicatie

### `app.py` - `get_output_directory()`

```python
def get_output_directory(aanvraag_type=None, omgeving=None):
    """
    Bepaal uitvoermap op basis van berichttype en omgeving.
    """
    if omgeving is None:
        omgeving = CONFIG.get('omgeving', 'UZSTA_OMG')
    
    filedrop_locaties = CONFIG.get('filedrop_locaties', {})
    
    if aanvraag_type and omgeving in filedrop_locaties:
        # Kijk voor exact match en return D:\GUP\UZS\filedrop\...

  ### Fallback gedrag (zonder filedrop paden)
  Wanneer `filedrop_locaties` leeg is of geen paden bevat voor de geselecteerde omgeving,
  valt de applicatie terug op een lokale downloadmap zodat testers alsnog bestanden
  kunnen ophalen:

  - `web/static/downloads` (wordt gebruikt voor directe downloadlinks in de UI)

  Dit is alleen bedoeld voor dev/test en vervangt de productie filedrop niet.
```

### Upload Flow

1. Gebruiker uploadt Excel-bestand met formulier
2. Selecteert berichttype (OTP3, ZBM, VM)
3. App bepaalt:
   - Huidige omgeving uit `instellingen.json`
   - Filedrop pad uit `filedrop_locaties[omgeving][berichttype]`
4. XML-bestanden worden gegenereerd en direct in juiste filedrop geplaatst

## Deployment op E: Drive (Testserver)

Na het bouwen en overzetten van de EXE naar `E:\App-data\`:

1. Bewerk `web/instellingen.json`:
```json
{
  "omgeving": "UZSTA_OMG"  // of de juiste testomgeving
}
```

2. Start het programma:
```powershell
E:\App-data\xmlator.exe
```

3. XML-bestanden verschijnen automatisch in:
```
D:\GUP\UZS\filedrop\UZI-GAP3\{OMGEVING}\{BERICHTTYPE_PAD}
```

## Toevoegen van Nieuwe Omgeving

1. Voeg entry toe in `web/instellingen.json`:
```json
{
  "NIEUWE_OMG": {
    "OTP3": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\NIEUWE_OMG\\UwvZwMelding_MQ_V0428",
    "ZBM": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\NIEUWE_OMG\\v0428\\UwvZwMelding",
    "VM": "D:\\GUP\\UZS\\filedrop\\UZI-GAP3\\NIEUWE_OMG\\v0428\\UwvZwMelding"
  }
}
```

2. Commit en push:
```powershell
git add web/instellingen.json
git commit --no-verify -m "Nieuwe omgeving NIEUWE_OMG toegevoegd"
git push
```

3. Rebuild EXE:
```powershell
.\build.ps1
```
