# -*- encoding: utf-8 -*-
""" COMMANDS.PY """

import click
from distutils.util import strtobool
import json
from math import pi, cos, sin, ceil
import os
from pathlib import Path
import pickle
import re

from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from flask.cli import AppGroup

from dr.extensions import db
from dr.main.models import DrItem, DrItemIngredient
from dr.snf.models import DrMap, DrCell

cmd_manager = AppGroup('cmd_manager')


HASH = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
PId4 = pi / 4
COS_PId4 = cos(PId4)
SIN_PId4 = sin(PId4)
COS_mPId4 = COS_PId4
SIN_mPId4 = -SIN_PId4


def get_x(cell_id, width):
    return cell_id % (width - 0.5) * 2

def get_y(cell_id, width):
    return cell_id / (width - 0.5)

def get_x_rotated(cell_id, width, height):
    x = get_x(cell_id, width) - width
    y = get_y(cell_id, width) - height
    return ceil((x * COS_PId4 - y * SIN_PId4 - 0.25) * 0.7) + width

def get_y_rotated(cell_id, width, height):
    x = get_x(cell_id, width) - width
    y = get_y(cell_id, width) - height
    return ceil((x * SIN_PId4 + y * COS_PId4 - 1.75) * 0.7) + height

def uncompress_cells(dr_map):
    data = []
    for i in dr_map.decrypted:
        data.append(HASH.index(chr(i)))

    active = data[0] & 32 >> 5 == 1
    dr_cells = []
    cell_count = int(len(dr_map.decrypted) / 10)
    for i in range(cell_count):
        dr_cells.append(uncompress_cell(dr_map, i, data, active))
    return dr_cells

def uncompress_cell(dr_map, cell_id, data, active):
    idx = cell_id * 10
    line_of_sight = data[idx] & 1 == 1
    layer_ground_rot = data[idx + 1] & 48 >> 4
    ground_level = data[idx + 1] & 15
    movement = data[idx + 2] & 56 >> 3
    layer_ground_num = (data[idx] & 24 << 6) + (data[idx + 2] & 7 << 6) + data[idx + 3]
    ground_slope = data[idx + 4] & 60 >> 2
    layer_ground_flip = data[idx + 4] & 2 >> 1 == 1
    layer_object1_num = (data[idx] & 4 << 11) + (data[idx + 4] & 1 << 12) + (data[idx + 5] << 6) + data[idx + 6]
    layer_object1_rot = data[idx + 7] & 48 >> 4
    layer_object1_flip = data[idx + 7] & 8 >> 3 == 1
    layer_object2_flip = data[idx + 7] & 4 >> 2 == 1
    layer_object2_interactive = data[idx + 7] & 2 >> 1 == 1
    layer_object2_num = (data[idx] & 2 << 12) + (data[idx + 7] & 1 << 12) + (data[idx + 8] << 6) + data[idx + 9]

    return DrCell(
        map_id=dr_map.id,
        cell_id=cell_id,
        active=active,
        line_of_sight=line_of_sight,
        layer_ground_rot=layer_ground_rot,
        ground_level=ground_level,
        movement=movement,
        layer_ground_num=layer_ground_num,
        ground_slope=ground_slope,
        layer_ground_flip=layer_ground_flip,
        layer_object1_num=layer_object1_num,
        layer_object1_rot=layer_object1_rot,
        layer_object1_flip=layer_object1_flip,
        layer_object2_flip=layer_object2_flip,
        layer_object2_interactive=layer_object2_interactive,
        layer_object2_num=layer_object2_num,
        x=get_x(cell_id, dr_map.width),
        y=get_y(cell_id, dr_map.width),
        x_rot=get_x_rotated(cell_id, dr_map.width, dr_map.height),
        y_rot=get_y_rotated(cell_id, dr_map.width, dr_map.height)
    )

@cmd_manager.command()
def load_maps():
    """ Load maps """

    map_dir = 'dr/data/maps_1.29'
    for map_file in os.listdir(map_dir):

        with open('{}/{}'.format(map_dir, map_file), encoding='utf-8') as json_file:
            map_dic = json.load(json_file)

            try:
                dr_map = DrMap.query.filter(DrMap.id == int(map_dic['id'])).one()
            except NoResultFound:
                dr_map = DrMap(
                    id=int(map_dic['id']),
                    height=int(map_dic['height']),
                    width=int(map_dic['width']),
                    capabilities=int(map_dic['capabilities']),
                    is_outdoor=strtobool(map_dic['bOutdoor']),
                    private_key=map_dic['key'].encode(),
                    # encrypted=map_dic['mapData'].encode(),
                    decrypted=map_dic['decryptedMapData'].encode()
                )
                db.session.add(dr_map)

            if any(chr(c) not in HASH for c in dr_map.decrypted):
                print('Map {} skipped'.format(dr_map.id))
                continue

            dr_cells = uncompress_cells(dr_map)
            for dr_cell in dr_cells:
                try:
                    dr_cell = DrCell.query.filter(DrCell.map_id == dr_map.id).filter(DrCell.cell_id == dr_cell.cell_id).one()
                    print('Map {} Cell {} already exists'.format(dr_map.id, dr_cell.cell_id))
                except NoResultFound:   
                    db.session.add(dr_cell)

            db.session.commit()
            db.session.flush()
            print(dr_map, len(dr_cells))

@cmd_manager.command()
def load_items():
    """ Load items """

    with open('dr/data/items_1.29.txt', encoding='utf-8') as txt_file:
        for item_line in txt_file.readlines():
            item_line_s = item_line.split(':')
            item_id = int(item_line_s[0])
            item_name = ':'.join(item_line_s[1:]).strip('\n')

            try:
                dr_item = DrItem.query.filter(DrItem.id == item_id).one()
                print('Item {} "{}" already exists'.format(item_id, item_name))
            except NoResultFound:
                dr_item = DrItem(
                    id=item_id,
                    name=item_name
                )
                db.session.add(dr_item)
    
        db.session.commit()
        db.session.flush()

@cmd_manager.command()
def load_barbok_data():
    """ Load Barbok data """

    with open('dr/data/items.json', encoding='utf-8') as json_file:
        datastore = json.load(json_file)
        for item_name, item_id in datastore['ingredients'].items():
            try:
                dr_item = DrItem.query.filter(DrItem.id == item_id).one()
                if dr_item.name != item_name:
                    print('Item {} "{}" already exists with another name ({}). Will be updated.'.format(item_id, item_name, dr_item.name))
                    dr_item.name = item_name
                else:
                    print('Item {} "{}" already exists'.format(item_id, item_name))
            except NoResultFound:
                dr_item = DrItem(
                    id=item_id,
                    name=item_name
                )
                db.session.add(dr_item)
        for type_item in ['armes','equipements']:
            for type_equipement in datastore[type_item]:
                for item_name, item_data in datastore[type_item][type_equipement].items():
                    item_id = item_data['id']
                    item_lvl = item_data['niveau']
                    # print(item_name)
                    to_create = False
                    try:
                        dr_item = DrItem.query.filter(DrItem.id == item_id).one()
                    except NoResultFound:
                        to_create = True
                        dr_item = DrItem(
                            id=item_id,
                            name=item_name
                        )
                    dr_item.level = item_lvl
                    dr_item.categ = type_item.rstrip('s')
                    dr_item.sub_categ = type_equipement.rstrip('s').rstrip('x')
                    effects = '\n'.join([effect['valeur'] for effect in item_data['effets']])
                    dr_item.effects = effects
                    if item_data['caracteristiques']:
                        stats = '\n'.join(item_data['caracteristiques'])
                        dr_item.stats = stats
                    if item_data['conditions']:
                        conditions = '\n'.join(item_data['conditions'])
                        dr_item.conditions = conditions
                    if to_create:
                        db.session.add(dr_item)
                    if item_data['recette']:
                        for ing_data in item_data['recette']:
                            qte = ing_data['quantite']
                            ing_id = ing_data['id']
                            ing_name = ing_data['ingredient']
                            try:
                                dr_item_ing = DrItemIngredient.query.filter(DrItemIngredient.item_id == item_id, DrItemIngredient.ingredient_id == ing_id).one()
                                print('Item {} "{}" already exists in {} recipe.'.format(item_id, ing_name, item_name))
                            except NoResultFound:
                                dr_item_ing = DrItemIngredient(
                                    item_id=item_id,
                                    ingredient_id=ing_id,
                                    quantity=qte
                                )
                                db.session.add(dr_item_ing)
        db.session.commit()
        db.session.flush()

@cmd_manager.command()
def clean():
    """ Remove *.pyc and *.pyo files recursively starting at current directory """

    for dirpath, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                full_pathname = os.path.join(dirpath, filename)
                print('Removing {}'.format(full_pathname))
                os.remove(full_pathname)
