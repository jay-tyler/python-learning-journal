# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from pyramid.config import Configurator
from pyramid.view import view_config
from waitress import serve
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
import transaction
import datetime
from pyramid.httpexceptions import (HTTPFound, HTTPForbidden,
                                    HTTPMethodNotAllowed, HTTPNotFound)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import NoResultFound
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import remember, forget
from cryptacular.bcrypt import BCRYPTPasswordManager
from markdown2 import Markdown

markdowner = Markdown(extras=["code-friendly", "fenced-code-blocks",
                              "cuddled-lists"])

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))


DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://jason@localhost:5432/learning-journal')

HERE = os.path.dirname(os.path.abspath(__file__))

Base = declarative_base()


@view_config(route_name='home', renderer='templates/index.jinja2')
def list_view(request):
    entries = Entry.all()
    return {'entries': entries}


@view_config(route_name='detail', renderer='templates/detail.jinja2')
def detail_view(request):
    try:
        article_id = request.matchdict['id']
        article = Entry.get_article(article_id)
        return {'article': article}
    except NoResultFound:
        return HTTPFound(request.route_url('home'))


@view_config(route_name='new', renderer='templates/new.jinja2')
def new_entry(request):
    if request.method == 'GET':
        return {}
    if request.method == 'POST':
        if request.authenticated_userid:
            title = request.params.get('title')
            body_text = request.params.get('body_text')
            try:
                newart = Entry.write(title=title, body_text=body_text)
                DBSession.flush()
            except ValueError:
                #  Right now we stupidly go back to new view;
                #  need to implement some kind of user feedback
                return {'err_msg': 'Try Again: need both an entry and a title',
                        'title': title,
                        'body_text': body_text}
            # TODO: edit points towards the detail page; new view probably
            # should as well. Need to find a way to return the article id.
            return HTTPFound(request.route_url('detail', id=newart.id))
        else:
            return HTTPForbidden()
    else:
        return HTTPMethodNotAllowed()


@view_config(route_name='edit', renderer='templates/edit.jinja2')
def edit_entry(request):
    if request.method == 'GET':
        article_id = request.matchdict['id']
        try:
            article = Entry.get_article(article_id)
        except KeyError:
            return HTTPNotFound()
        return {'article': article}
    if request.method == 'POST':
        if request.authenticated_userid:
            new_title = request.params.get('title')
            new_body_text = request.params.get('body_text')
            article_id = request.matchdict['id']
            try:
                Entry.edit_entry(title=new_title, body_text=new_body_text,
                                 id=article_id)
            except ValueError:
                #  Right now we stupidly go back to edit view;
                #  need to implement some kind of user feedback
                return HTTPFound(request.route_url('edit', id=article_id))            
            return HTTPFound(request.route_url('detail', id=article_id))
        else:
            return HTTPForbidden()
    else:
        return HTTPMethodNotAllowed()


@view_config(context=DBAPIError)
def db_exception(context, request):
    from pyramid.response import Response
    response = Response(context.message)
    response.status_int = 500
    return response


@view_config(route_name='login', renderer='templates/login.jinja2')
def login(request):
    """authenticate a user by username/password"""
    username = request.params.get('username', '')
    error = ''
    if request.method == 'POST':
        error = "Login Failed"
        authenticated = False
        try:
            authenticated = do_login(request)
        except ValueError as e:
            error = str(e)

        if authenticated:
            headers = remember(request, username)
            return HTTPFound(request.route_url('home'), headers=headers)

    return {'error': error, 'username': username}


@view_config(route_name='logout', renderer='templates/index.jinja2')
def logout(request):
    headers = forget(request)
    return HTTPFound(request.route_url('home'), headers=headers)


class Entry(Base):
    __tablename__ = "entries"
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.Unicode(127), nullable=False)
    body_text = sa.Column(sa.UnicodeText, nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def render_text(self):
        return markdowner.convert(self.body_text)

    @classmethod
    def write(cls, title=None, body_text=None, session=None, id=None):
        if session is None:
            session = DBSession
        if title != "" and body_text != "":
            # Form will pass empty string when empty
            instance = cls(title=title, body_text=body_text)
            session.add(instance)
            return instance
        else:
            # Case of empty string
            raise ValueError

    @classmethod
    def edit_entry(cls, title=None, body_text=None, session=None, id=None):
        if session is None:
            session = DBSession
        edit_article = cls.get_article(article_id=id)
        if title != "" and body_text != "":
            # Form will pass empty string when empty
            edit_article.title = title
            edit_article.body_text = body_text
            session.add(edit_article)
            return edit_article
        else:
            # Case of empty string
            raise ValueError

    @classmethod
    def all(cls, session=None):
        if session is None:
            session = DBSession
        return session.query(cls).order_by(cls.created.desc()).all()

    @classmethod
    def get_article(cls, article_id, session=None):
        if session is None:
            session = DBSession
        return session.query(cls).filter(cls.id == article_id).one()


def init_db():
    engine = sa.create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)


def do_login(request):
    username = request.params.get('username', None)
    password = request.params.get('password', None)
    if not (username and password):
        raise ValueError('both username and password are required')

    settings = request.registry.settings
    manager = BCRYPTPasswordManager()
    if username == settings.get('auth.username', ''):
        hashed = settings.get('auth.password', '')
        return manager.check(hashed, password)
    return False


def main():
    """Create a configured wsgi app"""
    settings = {}
    debug = os.environ.get('DEBUG', True)
    settings['reload_all'] = debug
    settings['debug_all'] = debug
    settings['auth.username'] = os.environ.get('AUTH_USERNAME', 'admin')
    manager = BCRYPTPasswordManager()
    settings['auth.password'] = os.environ.get(
        'AUTH_PASSWORD', manager.encode('secret')
        )
    if not os.environ.get('TESTING', False):
        #  Connect to database only if not in testing
        engine = sa.create_engine(DATABASE_URL)
        DBSession.configure(bind=engine)
    # add a "secret" value for auth tkt signing
    auth_secret = os.environ.get('JOURNAL_AUTH_SECRET', 'itsaseekrit')

    # configuration setup
    config = Configurator(
        settings=settings,
        authentication_policy=AuthTktAuthenticationPolicy(
            secret=auth_secret,
            hashalg='sha512'
            ),
        authorization_policy=ACLAuthorizationPolicy(),
    )
    # Allow packages to declare their configurations
    config.include('pyramid_tm')
    config.include('pyramid_jinja2')
    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('detail', '/detail/{id}')
    config.add_route('new', '/new')
    config.add_route('edit', '/edit/{id}')
    config.add_static_view('static', os.path.join(HERE, 'static'))
    config.scan()
    app = config.make_wsgi_app()
    return app


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
