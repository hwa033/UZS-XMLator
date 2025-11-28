*** Settings ***
Documentation    XML Automation Tests - Clean & Minimal
Library          OperatingSystem
Library          XML    use_lxml=True
Resource         resources/xml_keywords.resource

Suite Setup      Create Directory    temp
Suite Teardown   Remove Directory    temp    recursive=True

*** Test Cases ***
TC001: Laad En Bewerk XML Template
    [Documentation]    Test XML template laden en bewerken
    [Tags]    smoke
    
    # Laad template
    Laad XML Template    templates/loonheffing.xml
    
    # Vervang placeholders
    Vervang Placeholder    BSN         123456789
    Vervang Placeholder    DatB        1985-03-15  
    Vervang Placeholder    BedrLoonSv  TestBedrijf BV
    
    # Sla op en valideer
    Sla XML Op    temp/test1.xml
    File Should Exist    temp/test1.xml
    
    ${content}=    Get File    temp/test1.xml
    Should Contain    ${content}    123456789
    Should Not Contain    ${content}    =BSN=

TC002: XML Structuur Validatie
    [Documentation]    Test XML parsing en validatie
    [Tags]    validation
    
    # Maak test XML
    ${xml}=    Set Variable    <?xml version="1.0"?><root><test>waarde</test></root>
    Create File    temp/test2.xml    ${xml}
    
    # Valideer structuur
    ${parsed}=    Parse XML    temp/test2.xml
    ${waarde}=    Get Element Text    ${parsed}    test
    Should Be Equal    ${waarde}    waarde

TC003: Bulk XML Generatie
    [Documentation]    Test meerdere XML bestanden genereren
    [Tags]    bulk
    
    @{personen}=    Create List
    ...    ${{ {'bsn': '111111111', 'naam': 'Jan'} }}
    ...    ${{ {'bsn': '222222222', 'naam': 'Piet'} }}
    
    FOR    ${index}    ${persoon}    IN ENUMERATE    @{personen}
        ${xml}=    Set Variable    <?xml version="1.0"?><persoon><bsn>${persoon['bsn']}</bsn><naam>${persoon['naam']}</naam></persoon>
        Create File    temp/bulk_${index + 1}.xml    ${xml}
    END
    
    File Should Exist    temp/bulk_1.xml
    File Should Exist    temp/bulk_2.xml

TC004: Template Beschikbaarheid
    [Documentation]    Test of templates beschikbaar zijn
    [Tags]    templates
    
    Directory Should Exist    templates
    File Should Exist    templates/loonheffing.xml
    
    ${content}=    Get File    templates/loonheffing.xml
    Should Start With    ${content}    <?xml

TC005: Error Handling
    [Documentation]    Test error scenarios
    [Tags]    errors
    
    # Test niet-bestaand bestand
    Run Keyword And Expect Error    *    Get File    nietbestaand.xml
    
    # Test ongeldige XML  
    ${invalid}=    Set Variable    <root><niet-gesloten>
    Create File    temp/invalid.xml    ${invalid}
    Run Keyword And Expect Error    *    Parse XML    temp/invalid.xml