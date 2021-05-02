# -*- encoding: utf-8 -*-
""" APP.PY """

import os

from flask import Flask, render_template

from dr.config import DevConfig, ProdConfig
from dr.extensions import db, cache, mail, debug_toolbar, migrate
from dr.database import db_manager
from dr.commands import cmd_manager
from dr.snf.commands import snf_manager
from dr.main.views import bp_main
#from dr.snf.views import bp_snf


CONFIG = ProdConfig if os.environ.get('FLASK_DEBUG') == '0' else DevConfig

def create_app(config_object=CONFIG):
    """ Create App """
    app = Flask(__name__)
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    register_shellcontext(app)
    register_commands(app)
    return app

def register_extensions(app):
    """ Register Extensions """
    db.init_app(app)
    cache.init_app(app)
    mail.init_app(app)
    debug_toolbar.init_app(app)
    migrate.init_app(app, db)
    return None

def register_blueprints(app):
    """ Register Blueprints """
    app.register_blueprint(bp_main)
    #app.register_blueprint(bp_snf)
    return None

def register_errorhandlers(app):
    """ Register Error Handlers """
    def render_error(error):
        error_code = getattr(error, 'code', 500)
        return render_template("{0}.html".format(error_code)), error_code
    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None

def register_shellcontext(app):
    """ Register Shell Context """
    def shell_context():
        return {
            'db': db
        }
    app.shell_context_processor(shell_context)

def register_commands(app):
    """ Register Commands """
    app.cli.add_command(db_manager)
    app.cli.add_command(cmd_manager)
    app.cli.add_command(snf_manager)
