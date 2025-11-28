*** Settings ***
Documentation    API integratie tests voor XML validatie endpoints
Resource         ../bronnen/xml_functies.resource
Resource         ../bronnen/api_functies.resource
Library          OperatingSystem
Library          String

*** Variables ***
${API_BASIS_URL}        http://localhost:5000
${XML_ENDPOINT}         /api/xml/valideer
${UPLOAD_ENDPOINT}      /api/xml/upload
${SESSIE_ALIAS}         xml_api

*** Test Cases ***
Test API Bereikbaarheid
    [Documentation]    Controleer of XML validatie API bereikbaar is
    [Tags]    api    basis
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    ${response}=    Verstuur GET Verzoek    ${sessie}    /api/health    200
    Controleer Response Status    ${response}    200
    Controleer Response Bevat Tekst    ${response}    "status":"ok"
    [Teardown]    Sluit API Sessie    ${sessie}

Test XML Validatie Endpoint Met Geldig XML
    [Documentation]    Verstuur geldig XML naar validatie endpoint
    [Tags]    api    validatie
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    ${xml_data}=    Get File    ${CURDIR}/../sjablonen/loonheffing.xml
    ${response}=    Verstuur POST Verzoek Met XML    ${sessie}    ${XML_ENDPOINT}    ${xml_data}    200
    Controleer Response Status    ${response}    200
    Controleer Response Header    ${response}    Content-Type    application/json
    Controleer JSON Waarde    ${response}    geldig    ${True}
    Controleer Response Tijd    ${response}    3.0
    [Teardown]    Sluit API Sessie    ${sessie}

Test XML Validatie Endpoint Met Ongeldig XML
    [Documentation]    Verstuur ongeldig XML en verwacht foutmelding
    [Tags]    api    validatie    fout
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    ${ongeldig_xml}=    Set Variable    <root><niet-gesloten>
    ${response}=    Verstuur POST Verzoek Met XML    ${sessie}    ${XML_ENDPOINT}    ${ongeldig_xml}    400
    Controleer Response Status    ${response}    400
    Controleer JSON Waarde    ${response}    geldig    ${False}
    Controleer Response Bevat Tekst    ${response}    fout
    [Teardown]    Sluit API Sessie    ${sessie}

Test XML Upload Endpoint
    [Documentation]    Upload XML bestand via multipart/form-data
    [Tags]    api    upload
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    ${xml_inhoud}=    Get File    ${CURDIR}/../sjablonen/loonheffing.xml
    ${files}=    Create Dictionary    bestand=${xml_inhoud}
    ${response}=    POST On Session    ${sessie}    ${UPLOAD_ENDPOINT}    
    ...    files=${files}    expected_status=201
    Controleer Response Status    ${response}    201
    Controleer Response Bevat Tekst    ${response}    bestand_id
    ${bestand_id}=    Haal JSON Waarde Op    ${response}    bestand_id
    Log    Bestand geupload met ID: ${bestand_id}
    [Teardown]    Sluit API Sessie    ${sessie}

Test API Response Headers
    [Documentation]    Valideer verplichte security en CORS headers
    [Tags]    api    security
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    ${response}=    Verstuur GET Verzoek    ${sessie}    /api/health    200
    Controleer Response Header    ${response}    Content-Type    application/json
    Controleer Response Header    ${response}    X-Content-Type-Options    nosniff
    Controleer Response Header    ${response}    X-Frame-Options    DENY
    [Teardown]    Sluit API Sessie    ${sessie}

Test API Rate Limiting
    [Documentation]    Test of rate limiting correct werkt
    [Tags]    api    security    rate-limit
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    
    # Verstuur 100 verzoeken snel achter elkaar
    FOR    ${i}    IN RANGE    100
        ${response}=    GET On Session    ${sessie}    /api/health    expected_status=any
        Exit For Loop If    ${response.status_code} == 429
    END
    
    # Laatste response zou 429 (Too Many Requests) moeten zijn
    Should Be Equal As Integers    ${response.status_code}    429
    Controleer Response Bevat Tekst    ${response}    rate limit
    [Teardown]    Sluit API Sessie    ${sessie}

Test API Authenticatie Vereist
    [Documentation]    Test dat endpoints authenticatie vereisen
    [Tags]    api    security    auth
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    ${response}=    GET On Session    ${sessie}    /api/admin/gebruikers    expected_status=401
    Controleer Response Status    ${response}    401
    Controleer Response Bevat Tekst    ${response}    unauthorized
    [Teardown]    Sluit API Sessie    ${sessie}

Test API Authenticatie Met Token
    [Documentation]    Test authenticatie met Bearer token
    [Tags]    api    auth
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    ${test_token}=    Set Variable    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test
    Authenticeer Met Bearer Token    ${sessie}    ${test_token}
    ${response}=    GET On Session    ${sessie}    /api/admin/gebruikers    expected_status=any
    # Met geldige token verwachten we 200 of 403 (forbidden), niet 401
    Should Not Be Equal As Integers    ${response.status_code}    401
    [Teardown]    Sluit API Sessie    ${sessie}

Test Bulk XML Validatie
    [Documentation]    Valideer meerdere XML bestanden in één request
    [Tags]    api    bulk
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    
    # Maak test XML data
    ${xml1}=    Set Variable    <root><element>Test 1</element></root>
    ${xml2}=    Set Variable    <root><element>Test 2</element></root>
    ${xml3}=    Set Variable    <root><element>Test 3</element></root>
    
    ${bulk_data}=    Catenate    SEPARATOR=\n---\n    ${xml1}    ${xml2}    ${xml3}
    ${response}=    Verstuur POST Verzoek Met XML    ${sessie}    /api/xml/bulk-valideer    ${bulk_data}    200
    
    Controleer Response Status    ${response}    200
    Controleer JSON Waarde    ${response}    totaal    3
    [Teardown]    Sluit API Sessie    ${sessie}

Test API Error Handling
    [Documentation]    Test diverse error scenario's
    [Tags]    api    errors
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    
    # Test 404 - Niet bestaand endpoint
    ${response1}=    GET On Session    ${sessie}    /api/niet-bestaand    expected_status=404
    Controleer Response Status    ${response1}    404
    
    # Test 405 - Method Not Allowed
    ${response2}=    DELETE On Session    ${sessie}    /api/health    expected_status=405
    Controleer Response Status    ${response2}    405
    
    # Test 400 - Bad Request (lege body)
    ${response3}=    POST On Session    ${sessie}    ${XML_ENDPOINT}    data=    expected_status=400
    Controleer Response Status    ${response3}    400
    
    [Teardown]    Sluit API Sessie    ${sessie}

Test Response Compressie
    [Documentation]    Test of API gzip compressie ondersteunt
    [Tags]    api    performance
    ${sessie}=    Maak API Sessie    ${API_BASIS_URL}    ${SESSIE_ALIAS}
    ${headers}=    Create Dictionary    Accept-Encoding=gzip, deflate
    ${response}=    GET On Session    ${sessie}    /api/health    headers=${headers}
    
    # Controleer of response gecomprimeerd is
    Dictionary Should Contain Key    ${response.headers}    Content-Encoding
    ...    msg=Response ondersteunt geen compressie
    [Teardown]    Sluit API Sessie    ${sessie}

*** Keywords ***
Start Test API Server
    [Documentation]    Start mock API server voor testen (indien nodig)
    Log    Mock API server zou hier gestart worden
    # In productie zou dit een echte server starten
    # Start Process    python    mock_api_server.py    alias=api_server

Stop Test API Server
    [Documentation]    Stop mock API server
    Log    Mock API server zou hier gestopt worden
    # Terminate Process    api_server
