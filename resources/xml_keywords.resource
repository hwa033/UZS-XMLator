*** Settings ***
Documentation    XML Keywords - Clean & Minimal
Library          OperatingSystem
Library          XML    use_lxml=True  
Library          String

*** Variables ***
${XML_CONTENT}    ${None}

*** Keywords ***
Laad XML Template
    [Documentation]    Laadt XML template
    [Arguments]    ${file_path}
    
    File Should Exist    ${file_path}
    ${content}=    Get File    ${file_path}
    Set Test Variable    ${XML_CONTENT}    ${content}
    RETURN    ${content}

Vervang Placeholder  
    [Documentation]    Vervangt =PLACEHOLDER= met waarde
    [Arguments]    ${placeholder}    ${waarde}
    
    ${nieuwe_content}=    Replace String    ${XML_CONTENT}    =${placeholder}=    ${waarde}
    Set Test Variable    ${XML_CONTENT}    ${nieuwe_content}
    RETURN    ${nieuwe_content}

Sla XML Op
    [Documentation]    Slaat XML op naar bestand
    [Arguments]    ${output_file}
    
    Create File    ${output_file}    ${XML_CONTENT}
    RETURN    ${output_file}