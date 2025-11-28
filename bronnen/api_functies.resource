*** Settings ***
Documentation    REST API testing keywords voor XML automatisering
Library          RequestsLibrary
Library          Collections
Library          String
Library          OperatingSystem

*** Keywords ***
Maak API Sessie
    [Documentation]    Creëer een nieuwe API sessie voor requests
    [Arguments]    ${basis_url}    ${alias}=api_sessie
    Create Session    ${alias}    ${basis_url}    verify=${True}
    RETURN    ${alias}

Verstuur GET Verzoek
    [Documentation]    Verstuur GET request en valideer response
    [Arguments]    ${sessie}    ${endpoint}    ${verwachte_status}=200
    ${response}=    GET On Session    ${sessie}    ${endpoint}    expected_status=${verwachte_status}
    Log    Response Status: ${response.status_code}
    Log    Response Body: ${response.text}
    RETURN    ${response}

Verstuur POST Verzoek Met XML
    [Documentation]    Verstuur POST request met XML body
    [Arguments]    ${sessie}    ${endpoint}    ${xml_data}    ${verwachte_status}=200
    ${headers}=    Create Dictionary    Content-Type=application/xml
    ${response}=    POST On Session    ${sessie}    ${endpoint}    
    ...    data=${xml_data}    headers=${headers}    expected_status=${verwachte_status}
    Log    Response Status: ${response.status_code}
    Log    Response Body: ${response.text}
    RETURN    ${response}

Verstuur POST Verzoek Met JSON
    [Documentation]    Verstuur POST request met JSON body
    [Arguments]    ${sessie}    ${endpoint}    ${json_data}    ${verwachte_status}=200
    ${headers}=    Create Dictionary    Content-Type=application/json
    ${response}=    POST On Session    ${sessie}    ${endpoint}    
    ...    data=${json_data}    headers=${headers}    expected_status=${verwachte_status}
    Log    Response Status: ${response.status_code}
    Log    Response Body: ${response.text}
    RETURN    ${response}

Verstuur PUT Verzoek
    [Documentation]    Verstuur PUT request voor resource update
    [Arguments]    ${sessie}    ${endpoint}    ${data}    ${verwachte_status}=200
    ${headers}=    Create Dictionary    Content-Type=application/xml
    ${response}=    PUT On Session    ${sessie}    ${endpoint}    
    ...    data=${data}    headers=${headers}    expected_status=${verwachte_status}
    Log    Response Status: ${response.status_code}
    RETURN    ${response}

Verstuur DELETE Verzoek
    [Documentation]    Verstuur DELETE request
    [Arguments]    ${sessie}    ${endpoint}    ${verwachte_status}=200
    ${response}=    DELETE On Session    ${sessie}    ${endpoint}    expected_status=${verwachte_status}
    Log    Response Status: ${response.status_code}
    RETURN    ${response}

Controleer Response Status
    [Documentation]    Valideer HTTP status code
    [Arguments]    ${response}    ${verwachte_status}
    Should Be Equal As Integers    ${response.status_code}    ${verwachte_status}
    ...    msg=Verwachte status ${verwachte_status}, kreeg ${response.status_code}

Controleer Response Header
    [Documentation]    Valideer specifieke response header
    [Arguments]    ${response}    ${header_naam}    ${verwachte_waarde}
    Dictionary Should Contain Key    ${response.headers}    ${header_naam}
    ...    msg=Header '${header_naam}' niet gevonden in response
    ${waarde}=    Get From Dictionary    ${response.headers}    ${header_naam}
    Should Contain    ${waarde}    ${verwachte_waarde}
    ...    msg=Header '${header_naam}' bevat niet '${verwachte_waarde}'

Controleer Response Bevat Tekst
    [Documentation]    Controleer of response body tekst bevat
    [Arguments]    ${response}    ${tekst}
    Should Contain    ${response.text}    ${tekst}
    ...    msg=Response bevat niet de tekst: ${tekst}

Controleer Response Bevat Niet
    [Documentation]    Controleer dat response body tekst NIET bevat
    [Arguments]    ${response}    ${tekst}
    Should Not Contain    ${response.text}    ${tekst}
    ...    msg=Response bevat onverwacht de tekst: ${tekst}

Haal JSON Waarde Op
    [Documentation]    Haal waarde op uit JSON response via JSONPath
    [Arguments]    ${response}    ${json_pad}
    ${json}=    Set Variable    ${response.json()}
    ${waarde}=    Get From Dictionary    ${json}    ${json_pad}
    RETURN    ${waarde}

Controleer JSON Waarde
    [Documentation]    Valideer specifieke waarde in JSON response
    [Arguments]    ${response}    ${json_sleutel}    ${verwachte_waarde}
    ${json}=    Set Variable    ${response.json()}
    ${werkelijke_waarde}=    Get From Dictionary    ${json}    ${json_sleutel}
    Should Be Equal    ${werkelijke_waarde}    ${verwachte_waarde}
    ...    msg=JSON waarde voor '${json_sleutel}' is ${werkelijke_waarde}, verwachtte ${verwachte_waarde}

Controleer Response Tijd
    [Documentation]    Valideer dat response tijd onder limiet ligt
    [Arguments]    ${response}    ${max_seconden}=5.0
    ${response_tijd}=    Convert To Number    ${response.elapsed.total_seconds()}
    Should Be True    ${response_tijd} <= ${max_seconden}
    ...    msg=Response tijd ${response_tijd}s overschrijdt limiet van ${max_seconden}s
    Log    Response tijd: ${response_tijd} seconden

Verstuur Bulk Verzoeken
    [Documentation]    Verstuur meerdere verzoeken parallel en verzamel resultaten
    [Arguments]    ${sessie}    ${endpoint_lijst}    ${methode}=GET
    @{resultaten}=    Create List
    FOR    ${endpoint}    IN    @{endpoint_lijst}
        ${response}=    Run Keyword If    '${methode}' == 'GET'
        ...    GET On Session    ${sessie}    ${endpoint}    expected_status=any
        ...    ELSE    POST On Session    ${sessie}    ${endpoint}    expected_status=any
        Append To List    ${resultaten}    ${response}
    END
    RETURN    @{resultaten}

Controleer API Beschikbaarheid
    [Documentation]    Test of API endpoint bereikbaar is
    [Arguments]    ${sessie}    ${health_endpoint}=/health
    TRY
        ${response}=    GET On Session    ${sessie}    ${health_endpoint}    expected_status=200
        Log    API is beschikbaar: ${response.status_code}
    EXCEPT
        Fail    API is niet bereikbaar op ${health_endpoint}
    END

Authenticeer Met Bearer Token
    [Documentation]    Voeg Bearer token toe aan sessie headers
    [Arguments]    ${sessie}    ${token}
    ${headers}=    Create Dictionary    Authorization=Bearer ${token}
    Set To Dictionary    ${sessie.headers}    Authorization=Bearer ${token}
    Log    Bearer token toegevoegd aan sessie

Authenticeer Met Basic Auth
    [Documentation]    Configureer Basic Authentication
    [Arguments]    ${sessie}    ${gebruikersnaam}    ${wachtwoord}
    ${auth}=    Create List    ${gebruikersnaam}    ${wachtwoord}
    Set To Dictionary    ${sessie}    auth=${auth}
    Log    Basic authentication geconfigureerd

Bewaar Response Als Bestand
    [Documentation]    Sla response body op als bestand
    [Arguments]    ${response}    ${bestandspad}
    Create File    ${bestandspad}    ${response.text}    encoding=UTF-8
    Log    Response opgeslagen naar: ${bestandspad}

Sluit API Sessie
    [Documentation]    Sluit API sessie en ruim resources op
    [Arguments]    ${alias}=api_sessie
    Delete All Sessions
    Log    Alle API sessies gesloten
