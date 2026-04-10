# Open punten – security en AVG

Dit document bevat bewust **uitgestelde** verbeterpunten.

## Context

Op dit moment wordt de applicatie gebruikt met **testdata**. Extra beveiligings- en compliance-maatregelen zijn inhoudelijk wenselijk, maar maken het testen en dagelijks gebruik nu onnodig complexer.

Daarom zijn onderstaande punten **nog niet direct ingevoerd als verplichte werkwijze**. Deze pakken we op een later moment op.

## Open punten

### 1. TLS / HTTPS afdwingen
- Applicatie alleen publiceren achter HTTPS.
- Bij voorkeur via reverse proxy / IIS / nginx.

### 2. Authenticatie / autorisatie verder aanscherpen
- Echte gebruikersauthenticatie of reverse-proxy auth.
- Eventueel rollen/autorisaties voor upload, download en verwijderen.
- Huidige extra API-key mogelijkheid nu niet als verplichte werkwijze inzetten.

### 3. Secrets beheer formaliseren
- `U_XMLATOR_SECRET` via beheerproces instellen.
- `XMLATOR_API_KEY` via beheerproces instellen indien later verplicht gemaakt.
- Geen secrets handmatig of los in scripts/documentatie beheren.

### 4. Bewaartermijn formeel vastleggen
- Definitieve bewaartermijn voor XML-output, logs en afgeleide bestanden bepalen.
- Ook back-ups en exports meenemen.

### 5. Toegangsrechten op mappen en shares aanscherpen
- Outputmappen, logmappen en eventuele shares beperken tot bevoegde gebruikers.
- Service account / least privilege toepassen.

### 6. Encryptie at rest
- Controleren of opslag op schijf/share voldoende is afgeschermd.
- Indien nodig versleuteling op server-, share- of schijfniveau toepassen.

### 7. Audit logging / beheerlogging
- Vastleggen wie uploadt, downloadt en verwijdert.
- Alleen invoeren als dit operationeel nodig is en zonder onnodige extra persoonsgegevens in logs.

### 8. DPIA / privacy assessment
- Formele beoordeling uitvoeren als de tool buiten testcontext of met productie-achtige persoonsgegevens gebruikt blijft worden.

### 9. Incident- en datalekproces
- Vastleggen wat de procedure is bij ongewenste toegang, verlies of verspreiding van gegevens.

### 10. Back-up en lifecycle beheer
- Controleren of output en logs in back-ups terechtkomen.
- Zorgen dat verwijdertermijnen daar ook gevolgd worden.

## Huidige keuze

Voor nu is bewust gekozen om deze punten **niet verder af te dwingen**, omdat:
- de applicatie momenteel met **testdata** wordt gebruikt;
- extra beveiligingslagen het **testen en gebruik complexer** maken;
- functioneel testen op dit moment prioriteit heeft.

## Later oppakken

Bij een volgende fase kunnen we dit document gebruiken als checklist voor:
- security hardening;
- AVG-aanscherping;
- productie- of acceptatie-geschiktheid.
