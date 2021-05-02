# -*- encoding: utf-8 -*-
""" MODELS.PY """

import logging
from datetime import datetime

from dr.extensions import db


class DrMap(db.Model):
    """ Map """

    __tablename__ = 'dr_map'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    height = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    capabilities = db.Column(db.Integer)
    is_outdoor = db.Column(db.Boolean)
    private_key = db.Column(db.LargeBinary, nullable=False)
    encrypted = db.Column(db.LargeBinary)
    decrypted = db.Column(db.LargeBinary)

    def __repr__(self):
        return '<Map {}>'.format(self.id)


class DrCell(db.Model):
    """ Map Cell """

    __tablename__ = 'dr_cell'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    map_id = db.Column(db.Integer, db.ForeignKey('dr_map.id'), primary_key=True, nullable=False)
    cell_id = db.Column(db.Integer, primary_key=True, nullable=False)
    active = db.Column(db.Boolean)
    line_of_sight = db.Column(db.Boolean)
    layer_ground_rot = db.Column(db.Integer)
    ground_level = db.Column(db.Integer)
    movement = db.Column(db.Integer)
    layer_ground_num = db.Column(db.Integer)
    ground_slope = db.Column(db.Integer)
    layer_ground_flip = db.Column(db.Boolean)
    layer_object1_num = db.Column(db.Integer)
    layer_object1_rot = db.Column(db.Integer)
    layer_object1_flip = db.Column(db.Boolean)
    layer_object2_flip = db.Column(db.Boolean)
    layer_object2_interactive = db.Column(db.Boolean)
    layer_object2_num = db.Column(db.Integer)
    x = db.Column(db.Integer)
    y = db.Column(db.Integer)
    x_rot = db.Column(db.Integer)
    y_rot = db.Column(db.Integer)

    def __repr__(self):
        return '<Cell {} {}/{}>'.format(self.cell_id, self.x_rot, self.y_rot)


class DrQueue(db.Model):
    """ Queue """

    __tablename__ = 'dr_queue'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    map_id = db.Column(db.Integer, db.ForeignKey('dr_map.id'), nullable=False)
    cell_id = db.Column(db.Integer, nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('dr_player.id'), nullable=False)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<Queue {}>'.format(self.id)
