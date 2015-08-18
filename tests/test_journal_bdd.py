# -* coding: utf-8 -*-
from __future__ import unicode_literals
import pytest
from pytest_bdd import scenario, given, when, then
# from test_journal import app, login_helper, db_session, entry, connection
# from test_journal import TEST_DATABASE_URL
import journal


@scenario('views.feature', 'Viewing Permalinks')
def test_permalink():
    pass


@given("I am an anonymous user")
def anon_user():
    pass


@given('There are is an entry')
def one_entry(db_session):
    entry = journal.Entry.write(
        title='Test Title',
        body_text="\n".join([
            '#### Here is a small title, should be h4',
            '### Here is a small title, should be h3',
            '## Here is a medium title, should be h2',
            '# Here is a large title, should be h1',
            '### What follows is an unordered list',
            '',
            '* One',
            '* Two',
            '* Three',
            '* Four',
            '',
            'Here is an ordered list',
            '',
            '1. Foo',
            '2. Bar',
            '',
            'Here is Code:',
            '',
            "```python",
            "from  __future__ import unicode_literals",
            "",
            "def foo(bar)",
            "    return int(bar) * 2",
            "",
            "class bar(object):",
            "    def __init__(self):",
            "        self.size = 4",
            "```"
        ]), session=db_session
    )
    db_session.flush()
    return entry


@when('I go to the home page')
def home(app):
    detail = app.get('/')
    assert detail.status_code == 200
    return detail


@then('The aricle should have a permalink')
def check_link(home, one_entry):
    assert 'href=/detail/{entry_id}'.format(one_entry.id) in home.body
    assert one_entry.title in home.body


@given('Requesting it should give me the article contents')
def go_to_home(one_entry, app):
    detail = app.get('/detail/{entry_id}'.format(entry_id=one_entry.id))
    assert detail.status_code == 200
    assert one_entry.body_text in detail.body
    assert one_entry.title in detail.body