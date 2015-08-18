Feature: Views
    Different ways to view the learning journal

Scenario: Viewing Permalinks
    Given I am an anonymous user
    And There are is an entry
    When I go to the home page
    Then The aricle should have a permalink
    And Requesting it should give me the article contents


