# -* coding: utf-8 -*-
from __future__ import unicode_literals
import pytest
from pytest_bdd import scenario, given, when, then
import journal
from test_journal import login_helper


@scenario('views.feature', 'Viewing Permalinks')
def test_permalink():
    pass


@scenario('views.feature', 'Edit an Article')
def test_edit_article():
    pass


@scenario('views.feature', 'Checking Code Highlighting')
def test_code_highlight():
    pass


@scenario('views.feature', 'Check Markdown Styling')
def test_markdown():
    pass


@given("I am an anonymous user")
def anon_user():
    pass


@given("I am an author user")
def login(app):
    username, password = ('admin', 'secret')
    redirect = login_helper(username, password, app)
    response = redirect.follow()
    return response


@given('There is an entry')
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


@given('I go to the home page')
def home(app, one_entry):
    detail = app.get('/')
    assert detail.status_code == 200
    return detail


@given("I submit my edits")
def edit(app, one_entry):
    edit_data = {
        'title': 'Hello there: edited',
        'body_text': 'This is an edited post'
    }
    edit_existing = app.post('/edit/{entry_id}'.format(entry_id=one_entry.id),
        params=edit_data, status='3*')
    return edit_data


@then('The article should have a permalink')
def check_link(home, one_entry):
    assert 'href="/detail/{entry_id}"'.format(entry_id=one_entry.id) in home.body
    assert one_entry.title in home.body


@then('Requesting it should give me the article contents')
def go_to_home(one_entry, app):
    # import pdb; pdb.set_trace()
    detail = app.get('/detail/{entry_id}'.format(entry_id=one_entry.id))
    assert detail.status_code == 200
    assert "Here is a small title, should be h4" in detail.text


@then('I should see my changes')
def check_edit(edit, app, one_entry):
    detail = app.get('/detail/{entry_id}'.format(entry_id=one_entry.id))
    assert edit['body_text'] in detail.body
    assert edit['title'] in detail.body


@then('The code text should have highlighting style')
def check_highlighting(one_entry, app):
    detail = app.get('/detail/{entry_id}'.format(entry_id=one_entry.id))
    print detail.body
    assert '<div class="codehilite">' in detail.body
    assert '<span class="kn">' in detail.body
    assert '<span class="p">' in detail.body
    assert '<span class="nf">' in detail.body


@then('The entry text should have markdown styling')
def check_markdown(one_entry, app):
    detail = app.get('/detail/{entry_id}'.format(entry_id=one_entry.id))
    print detail.body
    assert '<div class="markdown">' in detail.body
    assert "<h1>Here is a large title, should be h1</h1>" in detail.body
    assert "<h3>Here is a small title, should be h3</h3>" in detail.body
    assert "<ul>" in detail.body
    assert "<ol>" in detail.body
    assert "<li>One</li>" in detail.body