# -*- encoding: utf-8 -*-
""" DATABASE.PY """

import click

from flask.cli import AppGroup

from dr.extensions import db


db_manager = AppGroup('db_manager')

@db_manager.command()
def drop():
    """Drop Database Tables"""
    if click.confirm('Drop All ?'):
        db.drop_all()

@db_manager.command()
def create():
    """Create Database Tables"""
    db.create_all()

@db_manager.command()
def populate():
    """Populate Database Tables"""
    import glob
    from flask_fixtures.loaders import YAMLLoader
    from flask_fixtures import load_fixtures

    for data_dir in ['./dr/data']:
        for data_file in glob.glob(data_dir + '/*.yaml'):
            data = YAMLLoader().load(data_file)
            load_fixtures(db, data)
