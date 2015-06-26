# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

TEST_DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://jason@localhost:5432/test-learning-journal'
)

#TODO ^^^create a database corresponding to uri

os.environ['DATABASE_URL'] = TEST_DATABASE_URL
os.environ['TESTING'] = "True"

import journal

@pytest.fixture(scope='session')
def connection(request):
    engine = create_engine(TEST_DATABASE_URL)
    journal.Base.metadata.create_all(engine)
    connection = engine.connect()
    journal.DBSession.registry.clear()
    journal.DBSession.configure(bind=connection)
    journal.Base.metadata.bind = engine
    request.addfinalizer(journal.Base.metadata.drop_all)
    return connection


@pytest.fixture()
def db_session(request, connection):
    from transaction import abort
    trans = connection.begin()
    request.addfinalizer(trans.rollback)
    request.addfinalizer(abort)
    from journal import DBSession
    return DBSession


@pytest.fixture
def app():
    from journal import main
    from webtest import TestApp
    app = main()
    # main is just a factory that builds/returns configured wsgi apps
    return TestApp(app)


@pytest.fixture()
def entry(db_session):
    entry = journal.Entry.write(
        title='Test Title',
        body_text='Test Entry Text',
        session=db_session
    )
    db_session.flush()
    return entry


def test_write_entry(db_session):
    kwargs = {'title': "Test Title", "body_text": "Entry text test"}
    kwargs['session'] = db_session
    #  Asserting that there are no entries in database
    assert db_session.query(journal.Entry).count() == 0
    #  Creating an entry using the 'write' class method
    entry = journal.Entry.write(**kwargs)
    assert isinstance(entry, journal.Entry)
    #id and created made only on writing to database
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
    for field in ['title', 'body_text']:
        expected = getattr(entry, field, 'absent')
        assert expected in actual

def test_post_to_add_view(app):
    entry_data = {
        'title': 'Hello there',
        'body_text': 'This is a post'
    }
    response = app.post('/add', params=entry_data, status='3*')
    redirected = response.follow()
    actual = redirected.body
    for expected in entry_data.values():
        assert expected in actual

def test_add_no_params(app):
    response = app.post('/add', status=500)
    assert 'IntegrityError' in response.body
    