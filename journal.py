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
import datetime
# from pyramid.httpexceptions import HTTPNotFound

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))


DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://jason@localhost:5432/learning-journal')


Base = declarative_base()


class Entry(Base):
    __tablename__ = "entries"
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.Unicode(127), nullable=False)
    body_text = sa.Column(sa.UnicodeText, nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    @classmethod
    def write(cls, title=None, body_text=None, session=None):
        if session is None:
            session = DBSession
        instance = cls(title=title, body_text=body_text)
        session.add(instance)
        return instance

    @classmethod
    def all(cls, session=None):
        if session is None:
            session = DBSession
        return session.query(cls).order_by(cls.created.desc()).all()


@view_config(route_name='home', renderer='templates/test.jinja2')
def home(request):
    # import pdb; pdb.set_trace()
    return {'one':'two', 'stuff': ['a','b','c']}

@view_config(route_name='other', renderer='string')
def other(request):
    import pdb; pdb.set_trace()
    return request.matchdict


def init_db():
    engine = sa.create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)


def main():
    """Create a configured wsgi app"""
    settings = {}
    debug = os.environ.get('DEBUG', True)
    settings['reload_all'] = debug
    settings['debug_all'] = debug
    if not os.environ.get('Testing', False):
        #Connect to database only if not in testing
        engine = sa.create_engine(DATABASE_URL)
        DBSession.configure(bind=engine)

    # configuration setup
    config = Configurator(
        settings=settings
    )
    # Allow packages to declare their configurations
    config.include('pyramid_jinja2')
    config.include('pyramid_tm')
    config.add_route('home', '/')
    # config.add_route('other', '/other/{special_val}')
    config.scan()
    app = config.make_wsgi_app()
    return app


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
