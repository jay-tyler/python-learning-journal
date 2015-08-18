# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import pytest
from sqlalchemy.exc import IntegrityError
import journal


INPUT_BTN = '<input type="submit" name="Submit" value="new">'


def login_helper(username, password, app):
    """encapsulate app login for reuse in tests

    Accept all status codes so that we can make assertions in tests
    """
    login_data = {'username': username, 'password': password}
    return app.post('/login', params=login_data, status='*')


def test_write_entry(db_session):
    kwargs = {'title': "Test Title", "body_text": "Entry text test"}
    kwargs['session'] = db_session
    #  Asserting that there are no entries in database
    assert db_session.query(journal.Entry).count() == 0
    #  Creating an entry using the 'write' class method
    entry = journal.Entry.write(**kwargs)
    assert isinstance(entry, journal.Entry)
    #  id and created made only on writing to database
    auto_fields = ['id', 'created']
    for field in auto_fields:
        assert getattr(entry, field, None) is None
    #  Flush session to 'write' data to database
    db_session.flush()
    #  Flush is put out there, but not committed; there is an entry in
    #  the database, but it's not finalized
    assert db_session.query(journal.Entry).count() == 1
    for field in kwargs:
        if field != 'session':
            assert getattr(entry, field, '') == kwargs[field]
    #  id an created should have been created when added to db
    for auto in ['id', 'created']:
        assert getattr(entry, auto, None) is not None


def test_entry_no_title_fails(db_session):
    bad_data = {"body_text": "test text"}
    journal.Entry.write(session=db_session, **bad_data)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_entry_no_text_fails(db_session):
    bad_data = {'title': 'test title'}
    journal.Entry.write(session=db_session, **bad_data)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_read_entries_empty(db_session):
    entries = journal.Entry.all()
    assert len(entries) == 0


def test_read_entries_one(db_session):
    title_template = "Title {}"
    text_template = "Entry Text {}"
    # write three entries, with clear order
    for x in range(3):
        journal.Entry.write(
            title=title_template.format(x),
            body_text=text_template.format(x),
            session=db_session)
        db_session.flush()
    entries = journal.Entry.all()
    assert len(entries) == 3
    assert entries[0].title > entries[1].title > entries[2].title
    for entry in entries:
        assert isinstance(entry, journal.Entry)


def test_empty_listing(app):
    response = app.get('/')
    assert response.status_code == 200
    actual = response.body
    expected = 'No entries here so far'
    assert expected in actual


def test_listing(app, entry):
    response = app.get('/')
    assert response.status_code == 200
    actual = response.body
    for field in ['title']:
        expected = getattr(entry, field, 'absent')
        assert expected in actual


def test_post_to_add_view_not_authorized(app, auth_req):
    entry_data = {
        'title': 'Hello there',
        'body_text': 'This is a post'
    }
    response = app.post('/new', params=entry_data, status='4*')
    actual = response.body
    assert "403 Forbidden" in actual


def test_post_to_add_view_authorized(app, auth_req):
    auth_req.params = {'username': 'admin', 'password': 'secret'}
    redirect = app.post('/login', params=auth_req.params)
    response = redirect.follow()
    assert response.status_code == 200
    entry_data = {
        'title': 'Hello there',
        'body_text': 'This is a post'
    }
    response = app.post('/new', params=entry_data, status='3*')
    redirected = response.follow()
    actual = redirected.body
    assert entry_data['title'] in actual


def test_post_to_add_view_authorized_bad_title(app, auth_req):
    auth_req.params = {'username': 'admin', 'password': 'secret'}
    redirect = app.post('/login', params=auth_req.params)
    response = redirect.follow()
    assert response.status_code == 200
    entry_data = {
        'body_text': 'This is a post',
        'title': ''
    }
    response = app.post('/new', params=entry_data, status='2*')
    assert 'Try Again: need both an entry and a title' in response.body


def test_get_add_view_not_authorized(app, auth_req):
    response = app.get('/new', status='2*')
    actual = response.body
    assert "You need to be logged in to do this." in actual


def test_post_to_add_view_not_authorized(app, auth_req):
    entry_data = {
        'body_text': 'This is a post',
        'title': ''
    }
    response = app.post('/new', params=entry_data, status='4*')
    assert response.status_code == 403

def test_add_no_params(app, auth_req):
    auth_req.params = {'username': 'admin', 'password': 'secret'}
    redirect = app.post('/login', params=auth_req.params)
    response = redirect.follow()
    assert response.status_code == 200
    response = app.post('/new', status=500)
    assert 'IntegrityError' in response.body


def test_do_login_success(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'admin', 'password': 'secret'}
    assert do_login(auth_req)


def test_do_login_bad_pass(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'admin', 'password': 'wrong'}
    assert not do_login(auth_req)


def test_do_login_bad_user(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'bad', 'password': 'secret'}
    assert not do_login(auth_req)


def test_do_login_missing_params(auth_req):
    from journal import do_login
    for params in ({'username': 'admin'}, {'password': 'secret'}):
        auth_req.params = params
        with pytest.raises(ValueError):
            do_login(auth_req)


def test_start_as_anonymous(app):
    response = app.get('/', status=200)
    actual = response.body
    new_view = app.get('/new')
    actual = new_view.body
    assert INPUT_BTN not in actual


def test_login_success(app):
    username, password = ('admin', 'secret')
    redirect = login_helper(username, password, app)
    assert redirect.status_code == 302
    response = redirect.follow()
    assert response.status_code == 200
    new_view = app.get('/new')
    actual = new_view.body
    assert INPUT_BTN in actual


def test_login_fails(app):
    username, password = ('admin', 'wrong')
    response = login_helper(username, password, app)
    assert response.status_code == 200
    actual = response.body
    assert "Login Failed" in actual
    new_view = app.get('/new')
    actual = new_view.body
    assert INPUT_BTN not in actual


def test_logout(app):
    test_login_success(app)
    redirect = app.get('/logout', status="3*")
    response = redirect.follow()
    assert response.status_code == 200
    actual = response.body
    new_view = app.get('/new')
    actual = new_view.body
    assert INPUT_BTN not in actual


def test_permalink(entry, app):
    entry_id = entry.id
    detail = app.get('/detail/{entry_id}'.format(entry_id=entry_id))
    assert detail.status_code == 200
    assert entry.body_text in detail.body
    assert entry.title in detail.body


def test_edit(entry, app, auth_req):
    entry_id = entry.id
    edit_data = {
        'title': 'Hello there: edited',
        'body_text': 'This is an edited post'
    }
    # login
    auth_req.params = {'username': 'admin', 'password': 'secret'}
    redirect = app.post('/login', params=auth_req.params)
    response = redirect.follow()
    assert response.status_code == 200
    # edit post
    edit_existing = app.post('/edit/{entry_id}'.format(entry_id=entry_id),
                             params=edit_data, status='3*')
    detail = app.get('/detail/{entry_id}'.format(entry_id=entry_id))
    assert edit_data['body_text'] in detail.body
    assert edit_data['title'] in detail.body
    assert edit_existing.status_code == 302


def test_markdown(app, db_session):
    entry = journal.Entry.write(
        title='Test Title',
        body_text="\n".join(['#### Here is a small title, should be h4',
                             '### Here is a small title, should be h3',
                             '## Here is a medium title, should be h2',
                             '# Here is a large title, should be h1',
                             '### What follows is an unordered list',
                             '* One',
                             '* Two',
                             '* Three',
                             '* Four',
                             '',
                             'Here is an ordered list',
                             '1. Foo',
                             '2. Bar']),
        session=db_session
    )
    db_session.flush()
    entry_id = entry.id
    detail = app.get('/detail/{entry_id}'.format(entry_id=entry_id))
    print detail.body
    assert '<div class="markdown">' in detail.body
    assert "<h1>Here is a large title, should be h1</h1>" in detail.body
    assert "<h3>Here is a small title, should be h3</h3>" in detail.body
    assert "<ul>" in detail.body
    assert "<ol>" in detail.body
    assert "<li>One</li>" in detail.body


def test_code_color(app, db_session):
    entry = journal.Entry.write(
        title='Test Title',
        body_text="\n".join(["```python",
                             "from  __future__ import unicode_literals",
                             "",
                             "def foo(bar)",
                             "    return int(bar) * 2",
                             "",
                             "class bar(object):",
                             "    def __init__(self):",
                             "        self.size = 4",
                             "```"]),
        session=db_session
    )
    db_session.flush()
    entry_id = entry.id
    detail = app.get('/detail/{entry_id}'.format(entry_id=entry_id))
    print detail.body
    assert '<div class="codehilite">' in detail.body
    assert '<span class="kn">' in detail.body
    assert '<span class="p">' in detail.body
    assert '<span class="nf">' in detail.body
