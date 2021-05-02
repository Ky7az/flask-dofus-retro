# -*- encoding: utf-8 -*-
""" MODELS.PY """

from datetime import datetime
import enum
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound

from dr.extensions import db


class DrPlayer(db.Model):
    """ Player """

    __tablename__ = 'dr_player'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    map_id = db.Column(db.Integer, db.ForeignKey('dr_map.id'))
    window_handle = db.Column(db.Integer)
    state = db.Column(db.Enum('ready', 'moving', 'gathering', 'fighting', 'inventory_full'), default='ready')
    initiative = db.Column(db.Integer, default=100)
    prospection = db.Column(db.Integer, default=100)

    def __repr__(self):
        return '<Player {} "{}">'.format(self.id, self.name)

    def to_json(self):
        return dict(
            id=self.id,
            name=self.name
        )

class DrItemIngredient(db.Model):
    """ Link Item <-> ingredients """

    __tablename__ = 'dr_item_ingredient'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('dr_item.id'))
    quantity = db.Column(db.Integer, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('dr_item.id'))

class ItemCateg(enum.Enum):
    arme = "Arme"
    consommable = "Consommable"
    equipement = "Equipement"
    ressource = "Ressource"

class ItemSubCateg(enum.Enum):
    arc = "Arc"
    baguette = "Baguette"
    baton = "Bâton"
    dague = "Dague"
    epee = "Epée"
    hache = "Hache"
    marteau = "Marteau"
    pelle = "Pelle"

    nourriture = "Nourriture"
    potion = "Potion"
    document = "Document"

    amulette = "Amulette"
    anneau = "Anneau"
    botte = "Botte"
    bouclier = "Bouclier"
    cape = "Cape"
    ceinture = "Ceinture"
    chapeau = "Chapeau"
    dofus = "Dofus"
    familier = "Familier"
    dragodinde = "Dragodinde"
    sac = "Sac"

class DrItem(db.Model):
    """ Item """

    __tablename__ = 'dr_item'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    categ = db.Column(db.Enum(ItemCateg), nullable=True)
    sub_categ = db.Column(db.Enum(ItemSubCateg), nullable=True)
    avg_price = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, nullable=True)
    effects = db.Column(db.Text)
    stats = db.Column(db.Text)
    conditions = db.Column(db.Text)

    def __repr__(self):
        if self.name:
            return "{} [{}]".format(self.name, self.id)
        return "{}".format(self.id)

    def to_json(self):
        dr_item_ingredients = DrItemIngredient.query.filter(DrItemIngredient.item_id == self.id) \
                                                    .order_by(DrItemIngredient.quantity) \
                                                    .all()

        act = ''
        if self.categ and self.categ.name in ['arme', 'equipement']:
            act = '<a class="btn btn-secondary btn-create-craft fas fa-cut" data-toggle="modal" data-target="#modalCreateCraftForm" title="Create Craft"</a>'

        return dict(
            id=self.id,
            n=self.name,
            cat=self.categ and self.categ.value or '',
            scat=self.sub_categ and self.sub_categ.value or '',
            lvl=self.level,
            avg=self.avg_price,
            eff=self.effects and self.effects.replace('\n', '<br/>') or '',
            sta=self.stats and self.stats.replace('\n', '<br/>') or '',
            cnd=self.conditions and self.conditions.replace('\n', '<br/>') or '',
            rec='<br/>'.join(['{}x {}'.format(x.quantity, DrItem.query.get(x.ingredient_id).name) for x in dr_item_ingredients]),
            crafts_quantity='{}/{}'.format(DrStorage.get_quantity(self.id), DrCraft.get_quantity(self.id)),
            act=act
        )

class DrCraft(db.Model):
    """ Craft """

    def _default_priority():
        max_priority = db.session.query(func.max(DrCraft.priority)).scalar()
        if max_priority is not None:
            return max_priority + 1
        return 0

    def get_quantity(item_id):
        crafts = DrCraft.query.all()
        qantity = 0
        for craft in crafts:
            item_ingredients = DrItemIngredient.query.filter(DrItemIngredient.item_id == craft.item_id, DrItemIngredient.ingredient_id == item_id) \
                                                     .order_by(DrItemIngredient.quantity) \
                                                     .all()
            for x in item_ingredients:
                qantity += x.quantity
        return qantity

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('dr_player.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('dr_item.id'), nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=_default_priority)

    def to_json(self):
        dr_player = DrPlayer.query.get(self.player_id)
        dr_item = DrItem.query.get(self.item_id)
        recipe_with_quantity = self.get_recipe_with_quantity()
        is_ready = int(all(qty[0] == qty[1] for ingredient_id, qty in recipe_with_quantity.items()))
        btn_class = 'btn-outline-success' if is_ready else 'btn-outline-danger'
        act = '<a class="btn {} btn-delete-craft fas fa-times" data-toggle="modal" href="/crafts/{}" data-target="#modalDeleteCraftForm" data-craft-ready={} data-craft-id={} title="Delete Craft"</a>'.format(btn_class, self.id, is_ready, self.id)
        return dict(
            pri=self.priority,
            p=dr_player.name,
            it='{} ({})'.format(dr_item.name, dr_item.level),
            rec='<br/>'.join('{}/{} {}'.format(qty[0], qty[1], DrItem.query.get(ingredient_id).name) for ingredient_id, qty in recipe_with_quantity.items()),
            act=act
        )

    def get_recipe_with_quantity(self):
        craft_dict = {}
        ingredients_used = {}

        crafts = DrCraft.query.order_by(DrCraft.priority).all()
        for craft in crafts:
            craft_dict[craft.id] = {}
            item_ingredients = DrItemIngredient.query.filter(DrItemIngredient.item_id == craft.item_id) \
                                                     .order_by(DrItemIngredient.quantity) \
                                                     .all()
            for x in item_ingredients:
                recipe_quantity = x.quantity
                storage_quantity = DrStorage.get_quantity(x.ingredient_id)

                if x.ingredient_id in ingredients_used:
                    storage_quantity -= ingredients_used[x.ingredient_id]

                quantity_used = recipe_quantity if storage_quantity >= recipe_quantity else storage_quantity

                if x.ingredient_id in ingredients_used:
                    ingredients_used[x.ingredient_id] += quantity_used
                else:
                    ingredients_used[x.ingredient_id] = quantity_used

                craft_dict[craft.id][x.ingredient_id] = (quantity_used, recipe_quantity)

        return craft_dict[self.id]

class StorageType(enum.Enum):
    O = "Item"
    G = "Kamas"

class DrStorage(db.Model):
    """ Storage """

    __tablename__ = 'dr_storage'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = db.Column(db.Integer, primary_key=True)
    create_dt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    stg_type = db.Column(db.Enum(StorageType), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('dr_player.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('dr_item.id'))
    quantity = db.Column(db.Integer, nullable=False)

    def get_quantity(item_id):
        dr_storages = DrStorage.query.filter(DrStorage.item_id == item_id).all()
        quantity = sum([stg.quantity for stg in dr_storages])
        return quantity

    def to_json(self):
        dr_item = DrItem.query.get(self.item_id)
        dr_player = DrPlayer.query.get(self.player_id)
        return dict(
            p=dr_player.name,
            ty=self.stg_type.value,
            it=repr(dr_item),
            qty=self.quantity,
            avg=self.stg_type.name == 'O' and dr_item and dr_item.avg_price * self.quantity or 0
        )

class DrMarketEntry(db.Model):
    """ Market Entry """

    __tablename__ = 'dr_market_entry'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = db.Column(db.BigInteger, primary_key=True)
    create_dt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    write_dt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('dr_item.id'), nullable=False)
    market_history_id = db.Column(db.BigInteger, db.ForeignKey('dr_market_history.id'), nullable=False)
    effects = db.Column(db.Text)

    def __repr__(self):
        return '<Market Entry {}>'.format(self.id)
  
    def to_json(self):
        dr_market_history = DrMarketHistory.query.get(self.market_history_id)
        return dict(
            id=self.id,
            dt=self.write_dt,
            mh=dr_market_history.id,
            it=repr(DrItem.query.get(self.item_id)),
            p1=dr_market_history.price_1,
            p10=dr_market_history.price_10,
            p100=dr_market_history.price_100,
            up1=dr_market_history.unit_price_1,
            up10=dr_market_history.unit_price_10,
            up100=dr_market_history.unit_price_100,
            eff=self.effects
        )

class DrMarketHistory(db.Model):
    """ Market History """

    __tablename__ = 'dr_market_history'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    create_dt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('dr_item.id'), nullable=False)
    market_entry_id = db.Column(db.Integer, db.ForeignKey('dr_market_entry.id'), nullable=True)

    price_1 = db.Column(db.Integer, nullable=False)
    price_10 = db.Column(db.Integer, nullable=False)
    price_100 = db.Column(db.Integer, nullable=False)

    unit_price_1 = db.Column(db.Float(precision=2), nullable=False)
    unit_price_10 = db.Column(db.Float(precision=2), nullable=False)
    unit_price_100 = db.Column(db.Float(precision=2), nullable=False)

    def __repr__(self):
        return '<Market History {}>'.format(self.id)

    def to_json(self):
        return dict(
            id=self.id,
            dt=self.create_dt,
            it=repr(DrItem.query.get(self.item_id)),
            me=self.market_entry_id,
            p1=self.price_1,
            p10=self.price_10,
            p100=self.price_100,
            up1=self.unit_price_1,
            up10=self.unit_price_10,
            up100=self.unit_price_100
        )
