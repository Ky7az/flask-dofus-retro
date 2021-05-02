# -*- coding: utf-8 -*-
""" EXTENSIONS.PY """

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask_cache import Cache
cache = Cache()

from flask_mail import Mail
mail = Mail()

from flask_debugtoolbar import DebugToolbarExtension
debug_toolbar = DebugToolbarExtension()

from flask_migrate import Migrate
migrate = Migrate()
