Feature: Views
    Different ways to view the learning journal


Scenario: Viewing Permalinks
    Given I am an anonymous user
    And There is an entry
    And I go to the home page
    Then The article should have a permalink
    And Requesting it should give me the article contents


Scenario: Edit an Article
    Given I am an author user
    And There is an entry
    And I submit my edits
    Then I should see my changes


Scenario: Checking Code Highlighting
    Given I am an anonymous user
    And There is an entry
    Then The code text should have highlighting style


Scenario: Check Markdown Styling
    Given I am an anonymous user
    And There is an entry
    Then The entry text should have markdown styling