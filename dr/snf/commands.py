# -*- encoding: utf-8 -*-
""" COMMANDS.PY """

import click
from kamene.all import * # scapy
from datetime import datetime, timedelta
from pprint import pprint
import random
import requests
import time

from pynput import keyboard
from pywinauto import mouse
from pywinauto.application import Application

from PIL import ImageChops
from pyscreenshot import grab

import win32gui

from flask.cli import AppGroup
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func

from dr.extensions import db
from dr.snf.constants import is_CMSG, is_SMSG, win_title_fmt, CMSG, SMSG, NETWORK_INTERFACE, RESOLUTION, SCAN_ON_LOADING_MAP, ACTIONS, RESOURCE_IDS, PLAYER_MAPS, ENTITY_PLAYER, MAP_PATH
from dr.snf.models import DrMap, DrCell, DrQueue
from dr.main.models import DrPlayer, DrStorage, DrItem, DrMarketEntry, DrMarketHistory
from dr.snf.packets import CLIENT_MSG, SERVER_MSG

snf_manager = AppGroup('snf_manager')


## GETTERS

def get_player_by_id(player_id):
    try:
        dr_player = DrPlayer.query.filter(DrPlayer.id == player_id).one()
    except NoResultFound:
        return False
    return dr_player

def get_player_by_map(map_id):
    dr_player = DrPlayer.query.filter(DrPlayer.map_id == map_id).one()
    return dr_player

def get_maps():
    dr_players = DrPlayer.query.all()
    map_ids = [s.map_id for s in dr_players]
    return map_ids

def get_gdf_cells(data, map_id=None):
    cells = []
    dr_cell_query = DrCell.query.filter(DrCell.layer_object2_interactive == True) \
                                .filter(DrCell.layer_object2_num.in_(RESOURCE_IDS))

    if not map_id:
        map_ids = get_maps()
        dr_cell_query = dr_cell_query.filter(DrCell.map_id.in_(map_ids))
    else:
        dr_cell_query = dr_cell_query.filter(DrCell.map_id == map_id)

    for x in data.split('|'):
        y = x.split(';')
        if len(y) == 3:
            cell_id, frame, interactive = y
            try:
                dr_cell = dr_cell_query.filter(DrCell.cell_id == cell_id).one()
            except NoResultFound:
                continue
            except MultipleResultsFound:
                continue

            cells.append((dr_cell, int(frame), bool(interactive)))

    return cells

def get_cells(map_id, cell_type):
    coord_dic = {}
    dr_cell_query = DrCell.query.filter(DrCell.map_id == map_id)

    if cell_type == 'i':
        dr_cell_query = dr_cell_query.filter(DrCell.layer_object2_interactive == True) \
                                     .filter(DrCell.layer_object2_num.in_(RESOURCE_IDS))
    elif cell_type == 'c':
        dr_cell_query = dr_cell_query.filter(DrCell.layer_object1_num == 1030)

    dr_cells = dr_cell_query.order_by(DrCell.layer_object2_num.desc()) \
                            .order_by(DrCell.x) \
                            .order_by(DrCell.y) \
                            .all()

    for dr_cell in dr_cells:
        coord_dic[dr_cell] = get_coord(map_id, dr_cell.cell_id)
    
    return coord_dic

def get_coord(map_id, cell_id):
    min_x = db.session.query(func.min(DrCell.x)).filter(DrCell.map_id == map_id).scalar()
    max_x = db.session.query(func.max(DrCell.x)).filter(DrCell.map_id == map_id).scalar()

    min_y = db.session.query(func.min(DrCell.y)).filter(DrCell.map_id == map_id).scalar()
    max_y = db.session.query(func.max(DrCell.y)).filter(DrCell.map_id == map_id).scalar()

    div_x = (RESOLUTION['max_x'] - RESOLUTION['min_x']) / max_x
    div_y = (RESOLUTION['max_y'] - RESOLUTION['min_y']) / max_y

    try:
        dr_cell = DrCell.query.filter(DrCell.map_id == map_id).filter(DrCell.cell_id == cell_id).one()
    except NoResultFound:
        return (0, 0)

    x = int(dr_cell.x * div_x + RESOLUTION['min_x'])
    y = int(dr_cell.y * div_y + RESOLUTION['min_y'])

    return x, y

def count_queue(player):
    dr_queue_count = DrQueue.query.filter(DrQueue.player_id == player.id) \
                                  .filter(DrQueue.map_id == player.map_id) \
                                  .count()
    return dr_queue_count

## SETTERS

def scan_map_and_create_queue(map_id, player):

    if map_id not in PLAYER_MAPS[player.id]:
        return

    cells = get_cells(map_id, 'i')
    for dr_cell, (cell_x, cell_y) in cells.items():
        if cell_x and cell_y:
            move_pos(player, 0, 0)

            bbox_size = 30
            bbox = (cell_x - bbox_size, cell_y - bbox_size, cell_x + bbox_size, cell_y + bbox_size)
            im = grab(bbox=bbox)

            move_pos(player, cell_x,cell_y)

            diff = ImageChops.difference(grab(bbox=bbox), im)
            diff_bbox = diff.getbbox()
            if diff_bbox:
                print('New Job for Player {} : Cell {} at {}/{} = {}/{} on Map {} for Object2 {}'.format(player.name, dr_cell.cell_id, dr_cell.x, dr_cell.y, cell_x, cell_y, map_id, dr_cell.layer_object2_num))
                dr_queue = DrQueue(map_id=map_id, cell_id=dr_cell.cell_id, player_id=player.id, x=cell_x, y=cell_y)
                db.session.add(dr_queue)

    db.session.commit()
    db.session.flush() 

def search_and_delete_queue(cell_id, player_id=None, map_id=None):

    dr_queue_query = DrQueue.query.filter(DrQueue.cell_id == cell_id)

    if not map_id:
        map_ids = get_maps()
        dr_queue_query = dr_queue_query.filter(DrQueue.map_id.in_(map_ids))
    else:
        dr_queue_query = dr_queue_query.filter(DrQueue.map_id == map_id)

    if player_id:
        dr_queue_query = dr_queue_query.filter(DrQueue.player_id == player_id)

    try:
        dr_queue = dr_queue_query.one()
    except NoResultFound:
        return
    except MultipleResultsFound:
        return

    db.session.delete(dr_queue)
    db.session.commit()
    db.session.flush() 

def init_session():

    for player_id, player_name in ENTITY_PLAYER.items():
        try:
            dr_player = DrPlayer.query.filter(DrPlayer.id == player_id).one()
        except NoResultFound:
            dr_player = DrPlayer(id=player_id, name=player_name)
            db.session.add(dr_player)

        win_title = win_title_fmt.format(player_name)
        wnd_handle = win32gui.FindWindow(None, win_title)
        dr_player.window_handle = wnd_handle

        db.session.commit()
        db.session.flush() 


## ACTIONS

def click_pos(player, x, y):
    h_wnd = player.window_handle
    win32gui.SetForegroundWindow(h_wnd)
    win32gui.ShowWindow(h_wnd, 3)
    mouse.click(button='left', coords=(x, y))

def move_pos(player, x, y):
    h_wnd = player.window_handle
    win32gui.SetForegroundWindow(h_wnd)
    win32gui.ShowWindow(h_wnd, 3)
    mouse.move(coords=(x, y))

def random_action(player):
    action = random.choice(ACTIONS)

    if action == 'nothing':
        print('Doing nothing')

    elif action == 'wait':
        delay = random.randrange(1, 10)
        print('Waiting {}s'.format(delay))
        time.sleep(delay)

    elif action == 'move_random':
        x = random.randrange(300, 1600)
        y = random.randrange(100, 1000)
        print('Moving to {}/{}'.format(x, y))
        click_pos(player, x, y)
        time.sleep(5)

    elif action == 'move_center':
        x = random.randrange(900, 1000)
        y = random.randrange(500, 600)
        print('Moving to {}/{}'.format(x, y))
        click_pos(player, x, y)
        time.sleep(5)

def call_action(pid, msg):

    if pid == 'GDF':
        GDF_data = msg.data.decode()

        # GDF -> OQ : Finish Gathering
        if msg.SMSG_Items_onQuantity:
            SMSG_Items_onWeight = msg.SMSG_Items_onQuantity.SMSG_Items_onWeight

            if SMSG_Items_onWeight.SMSG_Infos_onQuantity:
                entity_id = int(SMSG_Items_onWeight.SMSG_Infos_onQuantity.entity_id) 
                dr_player = get_player_by_id(entity_id)
                if not dr_player:
                    # Gathered by an other player
                    return

            elif SMSG_Items_onWeight.SMSG_Job_onXP:
                SMSG_Job_onXP = SMSG_Items_onWeight.SMSG_Job_onXP
                if SMSG_Job_onXP.SMSG_GameActions_onActions:
                    SMSG_GameActions_onActions = SMSG_Job_onXP.SMSG_GameActions_onActions
                    GA_data = SMSG_GameActions_onActions.data.decode()
                    entity_id = int(GA_data.split(';')[2])
                    dr_player = get_player_by_id(entity_id)
                    if SMSG_GameActions_onActions.SMSG_Game_onJoin:
                        dr_player.state = 'fighting'
                        db.session.commit()
                        db.session.flush() 
                        print('Player {} is fighting on Map {}'.format(dr_player.name, dr_player.map_id))
                        return

            cells = get_gdf_cells(GDF_data, map_id=dr_player.map_id)
            if not cells:
                return

            for dr_cell, frame, interactive in cells:
                if frame == 3:
                    search_and_delete_queue(dr_cell.cell_id, player_id=dr_player.id, map_id=dr_cell.map_id)
                    dr_player.state = 'ready'
                    db.session.commit()
                    db.session.flush() 
                    print('Player {} is ready on Map {}'.format(dr_player.name, dr_cell.map_id))

        # GDF -> Im : Inventory Full
        elif msg.SMSG_Infos_onMessage:
            cells = get_gdf_cells(GDF_data)
            if cells:
                dr_cell, frame, interactive = cells.pop()
                dr_player = get_player_by_map(dr_cell.map_id)

                Im_data = msg.SMSG_Infos_onMessage.data.decode()
                if Im_data == '0144':
                    dr_player.state = 'inventory_full'
                    db.session.commit()
                    db.session.flush() 
                    print('Inventory is full for Player {} on Map {}'.format(dr_player.name, dr_player.map_id))

    elif pid == 'GA':

        # GA -> GDM : Loading Map
        if msg.SMSG_Game_onMapData:
            GA_data = msg.data.decode()
            entity_id = int(GA_data.split(';')[1])
            map_id = int(msg.SMSG_Game_onMapData.map_id)
            try:
                dr_map = DrMap.query.filter(DrMap.id == map_id).one()
            except NoResultFound:
                print('Map {} not found'.format(map_id))
                return

            dr_player = get_player_by_id(entity_id)
            if dr_player:
                dr_player.map_id = dr_map.id
                if dr_player.state in ['gathering', 'fighting']:
                    dr_player.state = 'ready'
                if dr_player.state == 'ready':
                    if SCAN_ON_LOADING_MAP:
                        scan_map_and_create_queue(map_id, dr_player)
                db.session.commit()
                db.session.flush() 

            print('Loading Map {} for Player {} "{}"'.format(map_id, entity_id, dr_player and dr_player.name or 'Unknown'))

        # GA -> GDF : Start Gathering
        elif msg.SMSG_Game_onFrameObject2:
            GA_data = msg.data.decode()
            entity_id = int(GA_data.split(';')[2])
            dr_player = get_player_by_id(entity_id)

            GDF_data = msg.SMSG_Game_onFrameObject2.data.decode()
            cells = get_gdf_cells(GDF_data, map_id=dr_player and dr_player.map_id or None)
            if not cells:
                return

            for dr_cell, frame, interactive in cells:
                if frame == 2:
                    print('Player {} "{}" is gathering Resource {} on Cell {} on Map {}'.format(entity_id, dr_player and dr_player.name or 'Unknown', dr_cell.layer_object2_num, dr_cell.cell_id, dr_cell.map_id))
                    if dr_player:
                        dr_player.state = 'gathering'
                        db.session.commit()
                        db.session.flush() 
                    else:
                        # Being Gathered by an other player
                        search_and_delete_queue(dr_cell.cell_id)

        # GA : Moving
        else:
            GA_data = msg.data.decode()
            GA_data_s = GA_data.split(';')
            if len(GA_data_s) == 4:
                entity_id = int(GA_data_s[2])
                dr_player = get_player_by_id(entity_id)

    # GC -> As : Connecting Player
    elif pid == 'GC':

        GC_data = msg.data.decode()
        player_name = GC_data.split('|')[2]
        try:
            dr_player = DrPlayer.query.filter(DrPlayer.name == player_name).one()
        except NoResultFound:
            return

        if hasattr(msg, 'SMSG_Account_onStats'):
            As_data = msg.SMSG_Account_onStats.data.decode()
            As_data_s = As_data.split('|')
            dr_player.initiative = As_data_s[7]
            dr_player.prospection = As_data_s[8]
            db.session.commit()
            db.session.flush() 

    elif pid == 'GD':

        # GD -> GDF : Ressource Respawn
        if msg.SMSG_Game_onFrameObject2:
            GDF_data = msg.SMSG_Game_onFrameObject2.data.decode()
            cells = get_gdf_cells(GDF_data)
            if not cells:
                return
 
            for dr_cell, frame, interactive in cells:
                if frame == 5:
                    map_id = dr_cell.map_id

                    player_id = False
                    for p_id, map_ids in PLAYER_MAPS.items():
                        if map_id in map_ids:
                            player_id = p_id
                            break
                    if not player_id:
                        return

                    dr_player = get_player_by_id(player_id)
                    cell_id = dr_cell.cell_id
                    cell_x, cell_y = get_coord(map_id, cell_id)

                    if dr_player and cell_x and cell_y:
                        print('New Job for Player {} : Cell {} at {}/{} = {}/{} on Map {} for Object2 {}'.format(dr_player.name, cell_id, dr_cell.x, dr_cell.y, cell_x, cell_y, map_id, dr_cell.layer_object2_num))
                        dr_queue = DrQueue(map_id=map_id, cell_id=cell_id, player_id=dr_player.id, x=cell_x, y=cell_y)
                        db.session.add(dr_queue)
                        db.session.commit()
                        db.session.flush()

    elif pid == 'EHP':
        item_id = int(msg.item_id)
        avg_price = int(msg.avg_price)

        try:
            dr_item = DrItem.query.filter(DrItem.id == item_id).one()
        except NoResultFound:
            dr_item = DrItem(id=item_id)
            db.session.add(dr_item)

        dr_item.avg_price = avg_price
        db.session.commit()
        db.session.flush()

    elif pid == 'EHl':
        item_id = int(msg.item_id)

        # Item
        try:
            dr_item = DrItem.query.filter(DrItem.id == item_id).one()
        except NoResultFound:
            dr_item = DrItem(id=item_id)
            db.session.add(dr_item)

        print('Item {} "{}"'.format(item_id, dr_item.name))
        EHl_data = msg.data.decode()
        EHl_data_s = EHl_data.split('|')
        for market_entry in EHl_data_s:
            market_entry_id, effects, price_1, price_10, price_100 = market_entry.split(';')
            market_entry_id = int(market_entry_id)
            price_1, price_10, price_100 = price_1 and int(price_1) or 0, price_10 and int(price_10) or 0, price_100 and int(price_100) or 0
            unit_price_1, unit_price_10, unit_price_100 = price_1/1, price_10/10, price_100/100

            # Market History
            dr_market_history = DrMarketHistory.query.filter(DrMarketHistory.market_entry_id == market_entry_id) \
                                                     .order_by(DrMarketHistory.id.desc()) \
                                                     .first()
            if dr_market_history:
                if dr_market_history.price_1 != price_1 or dr_market_history.price_10 != price_10 or dr_market_history.price_100 != price_100:
                    dr_market_history = DrMarketHistory(
                        item_id=item_id,
                        price_1=price_1,
                        price_10=price_10,
                        price_100=price_100,
                        unit_price_1=unit_price_1,
                        unit_price_10=unit_price_10,
                        unit_price_100=unit_price_100
                    )
                    db.session.add(dr_market_history)
                    db.session.flush()
            else:
                dr_market_history = DrMarketHistory(
                    item_id=item_id,
                    price_1=price_1,
                    price_10=price_10,
                    price_100=price_100,
                    unit_price_1=unit_price_1,
                    unit_price_10=unit_price_10,
                    unit_price_100=unit_price_100
                )
                db.session.add(dr_market_history)
                db.session.flush()

            # Market Entry
            try:
                dr_market_entry = DrMarketEntry.query.filter(DrMarketEntry.id == market_entry_id).one()
                if dr_market_entry.market_history_id != dr_market_history.id:
                    dr_market_entry.market_history_id = dr_market_history.id
                    dr_market_entry.write_dt = datetime.utcnow()
            except NoResultFound:
                dr_market_entry = DrMarketEntry(
                    id=market_entry_id,
                    item_id=item_id,
                    market_history_id=dr_market_history.id,
                    effects=effects
                )
                db.session.add(dr_market_entry)
                db.session.flush()

            dr_market_history.market_entry_id = dr_market_entry.id

        db.session.commit()
        db.session.flush()  

    # Im -> As -> EC -> EL : Opening Bank
    elif pid == 'Im':

        if hasattr(msg, 'SMSG_Account_onStats') and msg.SMSG_Account_onStats:
            SMSG_Account_onStats = msg.SMSG_Account_onStats
            As_data = SMSG_Account_onStats.data.decode()
            As_data_s = As_data.split('|')
            try:
                dr_player = DrPlayer.query.filter(DrPlayer.initiative == As_data_s[7]) \
                                        .filter(DrPlayer.prospection == As_data_s[8]) \
                                        .one()
            except NoResultFound:
                return

            if hasattr(SMSG_Account_onStats, 'SMSG_Exchange_onCreate'):
                SMSG_Exchange_onCreate = SMSG_Account_onStats.SMSG_Exchange_onCreate
                if hasattr(SMSG_Exchange_onCreate, 'SMSG_Exchange_onList'):
                    EL_data = SMSG_Exchange_onCreate.SMSG_Exchange_onList.data.decode()
                    EL_data_s = EL_data.split(';')
                    item_ids = []
                    for huhu in EL_data_s:
                        huhu_s = huhu.split('~')
                        if len(huhu_s) >= 3:
                            stg_type = huhu_s[0][0]
                            item_id = int(huhu_s[1], 16)
                            quantity = int(huhu_s[2], 16)

                            dr_storage_query = DrStorage.query.filter(DrStorage.stg_type == stg_type) \
                                                            .filter(DrStorage.player_id == dr_player.id)
                            if stg_type == 'O':
                                dr_storage_query = dr_storage_query.filter(DrStorage.item_id == item_id)
                                try:
                                    dr_item = DrItem.query.filter(DrItem.id == item_id).one()
                                except NoResultFound:
                                    dr_item = DrItem(id=item_id)
                                    db.session.add(dr_item)

                                item_ids.append(dr_item.id)

                            try:
                                dr_storage = dr_storage_query.one()
                                dr_storage.quantity = quantity
                            except NoResultFound:
                                dr_storage = DrStorage(stg_type=stg_type, player_id=dr_player.id, item_id=item_id, quantity=quantity)
                                db.session.add(dr_storage)

                    print('Storage updated for player {}'.format(dr_player.name))

                    # Remove items that are no longer there
                    dr_items = DrStorage.query.filter(DrStorage.item_id.notin_(item_ids)) \
                                              .filter(DrStorage.player_id == dr_player.id) \
                                              .delete(synchronize_session='fetch')

                    db.session.commit()
                    db.session.flush() 

## SCAPY

RAW_LOAD = b''

def read_raw(p, c=False, s=False):
    global RAW_LOAD
    raw = p.getlayer(Raw)
    if raw:
        load = raw.load
        if load and load[-1] != 0: # Long packet sent in several times
            RAW_LOAD += load
            return None

        if not RAW_LOAD:
            RAW_LOAD = load
        elif RAW_LOAD.startswith(b'Im'):
            RAW_LOAD += load # Last packet ended by \x00

        if c:
            msg = CLIENT_MSG(RAW_LOAD)
        elif s:
            msg = SERVER_MSG(RAW_LOAD)

        RAW_LOAD = b''
        return msg
    return False

def MSG_print(packet):

    if is_CMSG(packet):
        msg = read_raw(packet, c=True)

    elif is_SMSG(packet):
        msg = read_raw(packet, s=True)
        if msg:
            pid = '{}{}{}'.format(chr(msg.type), chr(msg.action), chr(msg.error)) if chr(msg.error) in ['F', 'P', 'l'] else '{}{}'.format(chr(msg.type), chr(msg.action))
            # print(pid)
            # msg.show()
            if pid in SMSG.keys():
                what = SMSG[pid]
                x = msg.fields[what]
                call_action(pid, x)
  
@snf_manager.command()
def start():
    """ Sniffing packets """

    init_session()
    sniff(
        iface=NETWORK_INTERFACE,
        filter='tcp port 443',
        lfilter=lambda p: IP in p and (is_CMSG(p) or is_SMSG(p)),
        prn=MSG_print,
        store=0)

@snf_manager.command()
def process():
    """ Process job queue """

    player_ids = [player_id for player_id, player_name in ENTITY_PLAYER.items()]

    while True:
        print('Running ...')

        # Delete queues older that 10 min
        dr_queues_to_del = DrQueue.query.filter(DrQueue.create_date < datetime.utcnow() - timedelta(minutes=10)) \
                                        .order_by(DrQueue.create_date) \
                                        .all()
        if dr_queues_to_del:
            print('Deleting {} Jobs'.format(len(dr_queues_to_del)))
            for dr_queue_to_del in dr_queues_to_del:
                db.session.delete(dr_queue_to_del) 

        map_ids = get_maps()
        try:
            dr_queue = DrQueue.query.filter(DrQueue.player_id.in_(player_ids)) \
                                    .filter(DrQueue.map_id.in_(map_ids)) \
                                    .order_by(DrQueue.create_date) \
                                    .limit(1) \
                                    .one()
        except NoResultFound:
            print('No Queue ..')
            dr_queue = False

        if dr_queue:
            dr_player = get_player_by_id(dr_queue.player_id)
            if dr_player.state == 'ready':
                print('Clicking Cell {} at {}/{} on Map {}'.format(dr_queue.cell_id, dr_queue.x, dr_queue.y, dr_queue.map_id))
                move_pos(dr_player, dr_queue.x, dr_queue.y)
                # delay = random.uniform(0.5, 0.99)
                # time.sleep(delay)
                # click_pos(dr_player, dr_queue.x, dr_queue.y)
                # click_pos(dr_player, dr_queue.x + 40, dr_queue.y + 40)
                # random_action(dr_player)
                db.session.delete(dr_queue)
            else:
                print('Player {} with state {}'.format(dr_player.name, dr_player.state))

        db.session.commit()
        db.session.flush()
        time.sleep(5)

@snf_manager.command()
@click.argument("map_id", type=int)
@click.argument("cell_type", type=click.Choice(['i', 'c']))
def check_coord(map_id, cell_type):
    """ Check interactive or outgoing cells of map by moving mouse on each """

    map_id = int(map_id)
    try:
        dr_player = get_player_by_map(map_id)
    except NoResultFound:
        print('Player not on Map {}'.format(map_id))
        return

    cells = get_cells(map_id, cell_type)
    for dr_cell, (cell_x, cell_y) in cells.items():
        if cell_x and cell_y:
            move_pos(dr_player, cell_x, cell_y)
            time.sleep(1)

    pprint(cells)

@snf_manager.command()
@click.argument("player_id", type=int)
def follow_path(player_id):

    def find_nearest(points, coord):
        x, y = coord
        dist = lambda key: (x - points[key][0]) ** 2 + (y - points[key][1]) ** 2
        return min(points, key=dist)

    def card(m_id):
        coord_dic = get_cells(m_id, 'c')
        x_mid = (RESOLUTION['max_x'] - RESOLUTION['min_x']) / 2
        y_mid = (RESOLUTION['max_y'] - RESOLUTION['min_y']) / 2

        left = find_nearest(coord_dic, (RESOLUTION['min_x'], y_mid))
        left_x, left_y = coord_dic[left]

        right = find_nearest(coord_dic, (RESOLUTION['max_x'], y_mid))
        right_x, right_y = coord_dic[right]

        top = find_nearest(coord_dic, (x_mid, RESOLUTION['min_y']))
        top_x, top_y = coord_dic[top]

        bot = find_nearest(coord_dic, (x_mid, RESOLUTION['max_y']))
        bot_x, bot_y = coord_dic[bot]

        return {
            'left': {
                'x': left_x,
                'y': left_y
            },
            'right': {
                'x': right_x,
                'y': right_y
            },
            'top': {
                'x': top_x,
                'y': top_y
            },
            'bot': {
                'x': bot_x,
                'y': bot_y
            }
        }

    def wait(delay=None):
        if delay is None:
            delay = random.randrange(1, 5)
        time.sleep(delay)
        db.session.commit()
        db.session.flush()

    def goto(m_dict, card_dict, player):
        where = random.choice(list(m_dict.keys()))
        while player.state != 'ready':
            print('Player {} with state {}'.format(player.name, player.state))
            wait(2)

        print('Player {} going to {}'.format(player.name, where))
        click_pos(player, card_dict[where]['x'], card_dict[where]['y'])
        return m_dict[where]

    def work(m_id, m_dict):
        dr_player = get_player_by_id(player_id)

        if m_id not in PLAYER_MAPS[dr_player.id]:
            print('Map {} not in PLAYER_MAPS'.format(m_id))
            return

        if m_id == dr_player.map_id:
            scan_map_and_create_queue(m_id, dr_player)
            cnt = count_queue(dr_player)
            while cnt > 0:
                cnt = count_queue(dr_player)
                print('Waiting for {} queue(s)'.format(cnt))
                wait(2)
        else:
            print("Map {} != Player's Map {}".format(m_id, dr_player.map_id))
            return

        card_dict = card(m_id)
        m_id = goto(m_dict, card_dict, dr_player)
        return m_id

    player_id = int(player_id)
    dr_player = get_player_by_id(player_id)
    m_id = dr_player.map_id
    m_dict = MAP_PATH.get(m_id, False)

    while m_dict:
        wait(5)
        m_id = work(m_id, m_dict)
        m_dict = MAP_PATH.get(m_id, False)
