# Digitale aanvragen — UZS (Overzicht)

Dit document beschrijft de gebruikte berichttypes, versies en de bijbehorende output-locaties die door deze applicatie worden gebruikt.

## Applicaties en mappings

- ZBM (CdBerichtType: ZBM) — versie V0428
  - Output: `uzs_filedrop\UZI-GAP3\UZSx_ACC1\v0428`

- VM (CdBerichtType: VM) — versie V0428
  - Output: `uzs_filedrop\UZI-GAP3\UZSx_ACC1\v0428`

- Digipoort (CdBerichtType: OTP3 / UwvZwMelding_MQ_V0428)
  - Output: `uzs_filedrop\UZI-GAP3\UZSx_ACC1\UwvZwMelding_MQ_V0428`

> De exacte mapping staat in `web/app.py` in de `OUTPUT_MAP`-variabele.

## Velden die standaard worden aangepast

Bij het genereren van een bericht worden enkele velden automatisch ingevuld of uniek gemaakt:

- GegevensUitwisselingsnr (uniek: datum/tijd + suffix)
- BerichtReferentienr (uniek)
- TransactieReferentienr (uniek)

Daarnaast kunt u testdata meegeven voor persoonlijke velden, zoals:

- BSN
- Geboortedatum
- Naam

## Velden voor specifieke berichttypes

Sommige berichten bevatten extra velden die relevant zijn voor de businesslogica (bijv. Melding Ziekte). Voorbeelden:

- `DatEersteAoDag`
- `IndDirecteUitkering`
- `CdRedenAangifteAo`
- `CdRedenZiekmelding`
- `IndWerkdagOpZaterdag` / `IndWerkdagOpZondag`

De precieze betekenis en wanneer deze velden gebruikt worden, hangt af van het berichttype en de interne validatieregels. Raadpleeg het relevante XSD of functioneel ontwerp voor details.

## Aanpassingen en uitbreidingen

Als u extra velden wilt aanpassen of andere opslaglocaties wilt gebruiken, pas dan `web/app.py` aan (variabele `OUTPUT_MAP`).
<!-- Externe XML-sjablonen worden in deze build niet gebruikt; de generatie gebruikt een interne minimale sjabloon. -->

## Opmerkingen

- Deze handleiding is bedoeld als praktische referentie; voor formele specificaties en businessregels raadpleeg de officiele documentatie en XSD-bestanden in `docs/`.
