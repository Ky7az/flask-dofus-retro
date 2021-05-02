# -*- encoding: utf-8 -*-
""" CONFIG.PY """

import os


class Config(object):
    """ Config """

    SECRET_KEY = 'FIXME'
    APP_DIR = os.path.abspath(os.path.dirname(__file__)) # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    ASSETS_DEBUG = False # Don't bundle/minify static assets
    DEBUG_TB_ENABLED = False # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = 'simple' # Can be "memcached", "redis", etc.
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://ky7az:ky7az@localhost/dr'
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    #CELERY_BROKER_URL = 'redis://localhost:6379/10'
    #CELERY_RESULT_BACKEND = 'redis://localhost:6379/11'

    # DATABASE_HOST = 'localhost'
    # DATABASE_USER = 'ky7az'
    # DATABASE_PWD = 'ky7az'
    # DATABASE_NAME = 'dr'

    # Security
    #SECURITY_REGISTERABLE = True
    #SECURITY_RECOVERABLE = True
    #SECURITY_CONFIRMABLE = False
    #SECURITY_TRACKABLE = True

    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = 'FIXME'

    #SECURITY_POST_LOGIN_VIEW = '/account'
    #SECURITY_POST_CONFIRM_VIEW = '/account'

    # Mail
    #MAIL_SERVER = 'smtp.domain.com'
    #MAIL_PORT = 465
    #MAIL_USE_SSL = True
    #MAIL_USERNAME = 'user'
    #MAIL_PASSWORD = 'pass'
    #SECURITY_EMAIL_SENDER = 'info@domain.com'


class ProdConfig(Config):
    """ Prod Config """

    ENV = 'prod'
    DEBUG = False
    DEBUG_TB_ENABLED = False # Disable Debug toolbar


class DevConfig(Config):
    """ Dev Config """

    ENV = 'dev'
    DEBUG = True
    DEBUG_TB_ENABLED = True # Enable Debug toolbar
    ASSETS_DEBUG = True # Don't bundle/minify static assets
    CACHE_TYPE = 'simple' # Can be "memcached", "redis", etc.
