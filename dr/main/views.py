# -*- encoding: utf-8 -*-
""" VIEWS.PY """

import logging
from datetime import datetime

from flask import Blueprint, request, session, redirect, abort, jsonify
from flask.templating import render_template
from sqlalchemy.orm.exc import NoResultFound

from dr.extensions import db
from dr.main.models import DrPlayer, DrItem, DrCraft, DrStorage, DrMarketEntry, DrMarketHistory, DrItemIngredient
from dr.main.models import ItemCateg


bp_main = Blueprint('main', __name__, template_folder='templates', static_folder='../static')

## ENTRY POINT

@bp_main.route('/')
def index():
    return render_template('index.html')

## PLAYER

@bp_main.route('/players', methods=['GET'])
def player_get():
    rows = []
    players = DrPlayer.query.all()
    for player in players:
        player_json = player.to_json()
        rows.append(player_json)
    ret = jsonify(rows)
    return ret, 200

## ITEM

@bp_main.route('/item')
def item():
    return render_template('item.html')

@bp_main.route('/items', methods=['GET'])
def item_get():
    categ_select = request.args.get('categ_select')
    param_sort = request.args.get('sort')
    param_order = request.args.get('order')
    param_search = request.args.get('search')
    param_offset = request.args.get('offset')
    param_limit = request.args.get('limit')

    dr_item_query = DrItem.query

    if param_order == 'desc':
        dr_item_query = dr_item_query.order_by(DrItem.name.desc())
    else:
        dr_item_query = dr_item_query.order_by(DrItem.name.asc())

    if categ_select:
        dr_item_query = dr_item_query.filter(DrItem.categ == categ_select)
    if param_search:
        dr_item_query = dr_item_query.filter(DrItem.name.ilike('%{}%'.format(param_search)))

    total = dr_item_query.count()

    if param_offset:
        dr_item_query = dr_item_query.offset(param_offset)
    if param_limit:
        dr_item_query = dr_item_query.limit(param_limit)

    rows = []
    items = dr_item_query.all()
    for item in items:
        item_json = item.to_json()
        rows.append(item_json)

    ret = {
        'total': total,
        'rows': rows
    }
    ret = jsonify(ret)
    return ret, 200

@bp_main.route('/items/categs', methods=['GET'])
def item_categ_get():
    rows = []
    for categ in ItemCateg:
        rows.append({
            'name': categ.name,
            'value': categ.value
        })
    ret = jsonify(rows)
    return ret, 200

@bp_main.route('/ingredients/add', methods=['POST'])
def item_ing_add():
    json = request.json
    item_id = int(json.get('item_id'))
    try:
        dr_storage = DrStorage.query.filter(DrStorage.item_id==item_id).limit(1).one()
        dr_storage.quantity += 1
    except NoResultFound:
        players = DrPlayer.query.all()
        player_id = players[0].id
        dr_storage = DrStorage(
                            player_id=player_id,
                            item_id=item_id,
                            quantity=1,
                            stg_type="O"
                        )
        db.session.add(dr_storage)
    if dr_storage.quantity == 0:
        db.session.delete(dr_storage)

    db.session.commit()
    db.session.flush()

    ingredient_json = DrItem.query.filter(DrItem.id == item_id).one().to_json()
    in_storage, needed = ingredient_json['crafts_quantity'].split('/')
    missing = max(0,int(needed) - int(in_storage))

    return {'crafts_quantity': ingredient_json['crafts_quantity'], 'missing': missing}, 200

def _item_ing_sub(item_id, qty):
    try:
        dr_storages = DrStorage.query.filter(DrStorage.item_id==item_id).all()
        for dr_storage in dr_storages:
            qty_to_remove = min(dr_storage.quantity, qty)
            dr_storage.quantity -= qty_to_remove
            qty -= qty_to_remove
            if dr_storage.quantity == 0:
                db.session.delete(dr_storage)
            if qty == 0:
                break
    except NoResultFound:
        pass
    db.session.commit()
    db.session.flush()



@bp_main.route('/ingredients/sub', methods=['POST'])
def item_ing_sub():
    json = request.json
    item_id = int(json.get('item_id'))
    qty = int(json.get('quantity'))
    _item_ing_sub(item_id, qty)
    ingredient_json = DrItem.query.filter(DrItem.id == item_id).one().to_json()
    in_storage, needed = ingredient_json['crafts_quantity'].split('/')
    missing = max(0,int(needed) - int(in_storage))

    return {'crafts_quantity': ingredient_json['crafts_quantity'], 'missing': missing}, 200


## CRAFT

@bp_main.route('/craft')
def craft():
    return render_template('craft.html')

@bp_main.route('/crafts', methods=['GET'])
def craft_get():
    rows = []
    crafts = DrCraft.query.filter().all()
    for craft in crafts:
        craft_json = craft.to_json()
        rows.append(craft_json)
    ret = jsonify(rows)
    return ret, 200

@bp_main.route('/crafts', methods=['POST'])
def craft_create():
    json = request.json
    player_id = int(json.get('player_id'))
    item_id = int(json.get('item_id'))

    dr_craft = DrCraft(player_id=player_id, item_id=item_id)

    db.session.add(dr_craft)
    db.session.commit()
    db.session.flush()

    craft_json = dr_craft.to_json()
    return craft_json, 201

@bp_main.route('/crafts/ingredients', methods=['GET'])
def item_ingredient_get():
    rows = []
    crafts = DrCraft.query.all()
    ingredient_ids = {}
    for craft in crafts:
        dr_item = DrItem.query.get(craft.item_id)
        item_ingredients = DrItemIngredient.query.filter(DrItemIngredient.item_id == craft.item_id) \
                                                     .order_by(DrItemIngredient.quantity) \
                                                     .all()
        for ingredient in item_ingredients:
            ingredient_json = DrItem.query.filter(DrItem.id == ingredient.ingredient_id).one().to_json()
            in_storage, needed = ingredient_json['crafts_quantity'].split('/')
            if needed != '0' and ingredient_json['id'] not in ingredient_ids:
                ingredient_ids[ingredient_json['id']] = {
                    'ingredient_id': ingredient_json['id'],
                    'name': ingredient_json['n'],
                    'crafts': ['{} for {} priority {}'.format(ingredient.quantity, dr_item.name, craft.priority)],
                    'maxPri': craft.priority,
                    'crafts_quantity': ingredient_json['crafts_quantity'],
                    'missing': max(0,int(needed) - int(in_storage)),
                    'acts': '<a class="btn btn-secondary btn-add-sub-ingredient fas fa-plus" data-ing-id={} data-toggle="modal" href="/ingredients/add" title="Add"</a><a class="btn btn-secondary btn-add-sub-ingredient fas fa-minus" data-ing-id={} data-toggle="modal" href="/ingredients/sub" title="Sub"</a>'.format(ingredient_json['id'], ingredient_json['id'])
                }
            elif ingredient_json['id'] in ingredient_ids:
                ingredient_ids[ingredient_json['id']]['crafts'].append('{} for {} priority {}'.format(ingredient.quantity, dr_item.name, craft.priority))
                ingredient_ids[ingredient_json['id']]['maxPri'] = min(ingredient_ids[ingredient_json['id']]['maxPri'], craft.priority)
    for k, v in ingredient_ids.items():
        v['crafts'] = '<br/>'.join(v['crafts'])
        rows.append(v)
    ret = jsonify(rows)
    return ret, 200


@bp_main.route('/crafts/<craft_id>', methods=['PUT'])
def craft_update(craft_id):
    json = request.json
    index = int(json.get('index') or 0)
    
    dr_craft = DrCraft.query.get(craft_id)

    dr_craft_swapped = DrCraft.query.filter(DrCraft.priority == index).one()
    dr_craft_swapped.priority = dr_craft.priority

    dr_craft.priority = index

    crafts = DrCraft.query.filter(DrCraft.priority >= index) \
                          .filter(DrCraft.id != dr_craft.id) \
                          .order_by(DrCraft.priority) \
                          .all()
    for craft in crafts:
        index += 1
        craft.priority = index

    db.session.commit()
    db.session.flush()

    return {}, 204

@bp_main.route('/crafts/<craft_id>', methods=['DELETE'])
def craft_delete(craft_id):
    json = request.json
    update_storage = json.get('update_storage')
    dr_craft = DrCraft.query.get(craft_id)
    if update_storage:
        dr_item = DrItem.query.get(dr_craft.item_id)
        ingredients = DrItemIngredient.query.filter(DrItemIngredient.item_id == dr_item.id)
        for ingredient in ingredients:
            # print('{} {} à enlever'.format(ingredient.quantity, ingredient.ingredient_id))
            _item_ing_sub(ingredient.ingredient_id, ingredient.quantity)

    db.session.delete(dr_craft)
    db.session.commit()
    db.session.flush()

    return {}, 204

## STORAGE

@bp_main.route('/storage')
def storage():
    return render_template('storage.html')

@bp_main.route('/storages', methods=['GET'])
def storage_get():
    rows = []
    storages = DrStorage.query.all()
    for storage in storages:
        storage_json = storage.to_json()
        rows.append(storage_json)
    ret = jsonify(rows)
    return ret, 200

## MARKET ENTRY

@bp_main.route('/market_entry')
def market_entry():
    return render_template('market_entry.html')

@bp_main.route('/market_entries', methods=['GET'])
def market_entry_get():
    rows = []
    market_entries = DrMarketEntry.query.all()
    for market_entry in market_entries:
        market_json = market_entry.to_json()
        rows.append(market_json)
    ret = jsonify(rows)
    return ret, 200

## MARKET HISTORY

@bp_main.route('/market_history')
def market_history():
    return render_template('market_history.html')

@bp_main.route('/market_histories', methods=['GET'])
def market_history_get():
    rows = []
    market_histories = DrMarketHistory.query.all()
    for market_history in market_histories:
        market_json = market_history.to_json()
        rows.append(market_json)
    ret = jsonify(rows)
    return ret, 200

## MARKET REPORT

@bp_main.route('/market_report')
def market_report():
    return render_template('market_report.html')

@bp_main.route('/market_reports', methods=['GET'])
def market_report_get():

    mode_select = request.args.get('mode_select')

    min_percent_unit_price = float(request.args.get('min_percent_unit_price', 0))
    min_unit_price = float(request.args.get('min_unit_price', 0))
    
    min_percent_avg_price = float(request.args.get('min_percent_avg_price', 0))
    min_avg_price = float(request.args.get('min_avg_price', 0))

    ratio_up1_up10 = float(request.args.get('ratio_up1_up10', 0))

    rows = []
    q = DrMarketEntry.query

    dt_midnight = datetime.combine(datetime.today(), datetime.strptime('00:00', '%H:%M').time())
    q = q.filter(DrMarketEntry.write_dt >= dt_midnight)

    market_entries = q.all()
    for market_entry in market_entries:
        item = DrItem.query.get(market_entry.item_id)
        item_avg_price = item and item.avg_price or 0
        market_history = DrMarketHistory.query.get(market_entry.market_history_id)
        market_histories = DrMarketHistory.query.filter(DrMarketHistory.market_entry_id == market_entry.id).order_by(DrMarketHistory.id.desc()).all()

        unit_prices_1 = ' | '.join([str(h.unit_price_1) for h in market_histories][:10][::-1])
        unit_prices_10 = ' | '.join([str(h.unit_price_10) for h in market_histories][:10][::-1])
        unit_prices_100 = ' | '.join([str(h.unit_price_100) for h in market_histories][:10][::-1])

        unit_price_1, last_unit_price_1, min_unit_price_1, max_unit_price_1, avg_unit_price_1, diff_unit_price_amount_1, diff_unit_price_percent_1, diff_avg_price_amount_1, diff_avg_price_percent_1 = analyze_prices(market_histories, item and item_avg_price or 0, 'unit_price_1')
        unit_price_10, last_unit_price_10, min_unit_price_10, max_unit_price_10, avg_unit_price_10, diff_unit_price_amount_10, diff_unit_price_percent_10, diff_avg_price_amount_10, diff_avg_price_percent_10 = analyze_prices(market_histories, item_avg_price, 'unit_price_10')
        unit_price_100, last_unit_price_100, min_unit_price_100, max_unit_price_100, avg_unit_price_100, diff_unit_price_amount_100, diff_unit_price_percent_100, diff_avg_price_amount_100, diff_avg_price_percent_100 = analyze_prices(market_histories, item_avg_price, 'unit_price_100')

        ratio_unit_price_1_10 = round(unit_price_1 / unit_price_10, 2) if unit_price_1 and unit_price_10 else 0

        if (mode_select == 'diffPercentUnitPrice' and ((diff_unit_price_percent_1 < min_percent_unit_price and unit_price_1 >= min_unit_price) or (diff_unit_price_percent_10 < min_percent_unit_price and unit_price_10 >= min_unit_price) or (diff_unit_price_percent_100 < min_percent_unit_price and unit_price_100 >= min_unit_price))) \
                or (mode_select == 'diffPercentAveragePrice' and item_avg_price >= min_avg_price and (diff_avg_price_percent_1 < min_percent_avg_price or diff_avg_price_percent_10 < min_percent_avg_price or diff_avg_price_percent_100 < min_percent_avg_price)) \
                or (mode_select == 'ratioUnitPrice' and ratio_unit_price_1_10 >= ratio_up1_up10):

            rows.append(
                dict(
                    me = market_entry.id,
                    it = repr(item),
                    avg = item_avg_price,

                    up1 = unit_price_1,
                    lup1 = last_unit_price_1,
                    upz1 = unit_prices_1,
                    min_up1 = min_unit_price_1,
                    max_up1 = max_unit_price_1,
                    avg_up1 = avg_unit_price_1,
                    # d_up_a1 = diff_unit_price_amount_1,
                    d_up_p1 = diff_unit_price_percent_1,
                    # d_avg_a1 = diff_avg_price_amount_1,
                    d_avg_p1 = diff_avg_price_percent_1,

                    up10 = unit_price_10,
                    lup10 = last_unit_price_10,
                    upz10 = unit_prices_10,
                    min_up10 = min_unit_price_10,
                    max_up10 = max_unit_price_10,
                    avg_up10 = avg_unit_price_10,
                    # d_up_a10 = diff_unit_price_amount_10,
                    d_up_p10 = diff_unit_price_percent_10,
                    # d_avg_a10 = diff_avg_price_amount_10,
                    d_avg_p10 = diff_avg_price_percent_10,

                    up100 = unit_price_100,
                    upz100 = unit_prices_100,
                    lup100 = last_unit_price_100,
                    min_up100 = min_unit_price_100,
                    max_up100 = max_unit_price_100,
                    avg_up100 = avg_unit_price_100,
                    # d_up_a100 = diff_unit_price_amount_100,
                    d_up_p100 = diff_unit_price_percent_100,
                    # d_avg_a100 = diff_avg_price_amount_100,
                    d_avg_p100 = diff_avg_price_percent_100,

                    rup110 = ratio_unit_price_1_10
                )
            )

    ret = jsonify(rows)
    return ret, 200

def analyze_prices(market_histories, avg_price, price_field):

    prices = [getattr(h, price_field) for h in market_histories]
    min_unit_price = min(prices)
    max_unit_price = max(prices)
    avg_unit_price = round(sum(prices) / len(prices), 2)

    unit_price = prices[0]
    last_unit_price = prices[1] if len(prices) > 1 else 0

    if last_unit_price > 0:
        diff_unit_price_amount = round(unit_price - last_unit_price, 2) if unit_price > 0 else 0
        diff_unit_price_percent = round(diff_unit_price_amount / last_unit_price * 100, 2)
    else:
        diff_unit_price_amount = 0
        diff_unit_price_percent = 0

    if avg_price > 0:
        diff_avg_price_amount = round(unit_price - avg_price, 2) if unit_price > 0 else 0
        diff_avg_price_percent = round(diff_avg_price_amount / avg_price * 100, 2)
    else:
        diff_avg_price_amount = 0
        diff_avg_price_percent = 0

    return unit_price, last_unit_price, min_unit_price, max_unit_price, avg_unit_price, \
           diff_unit_price_amount, diff_unit_price_percent, diff_avg_price_amount, diff_avg_price_percent