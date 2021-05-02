# -*- encoding: utf-8 -*-
""" UTILS.PY """

from wtforms import validators


## Constants

## Functions

## Checks

## Validators

class Unique(object):

    def __init__(self, model, field, message):
        self.model = model
        self.field = field
        self.message = message

    def __call__(self, form, field):
        if not field.data:
            return
        if field.object_data == field.data:
            return
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            raise validators.ValidationError(self.message)
