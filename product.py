# -*- coding: utf-8 -*-
"""
    product.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Bool, Eval

__all__ = ['Template']
__metaclass__ = PoolMeta


class Template:
    "Product Template"
    __name__ = 'product.template'

    is_gift_card = fields.Boolean("Is Gift Card ?")

    gift_card = fields.Many2One(
        "gift_card.gift_card", "Gift Card", states={
            'invisible': ~(Bool(Eval('is_gift_card'))),
            'required': Bool(Eval('is_gift_card')),
        }, domain=[('state', '=', 'active')], depends=['is_gift_card']
    )

    gift_card_delivery_mode = fields.Selection([
        ('virtual', 'Virtual'),
        ('physical', 'Physical'),
        ('combined', 'Combined'),
    ], 'Gift Card Delivery Mode', states={
        'invisible': ~Bool(Eval('is_gift_card')),
        'required': Bool(Eval('is_gift_card')),
    }, depends=['is_gift_card'])

    @staticmethod
    def default_gift_card_delivery_mode():
        return 'physical'

    @staticmethod
    def default_is_gift_card():
        return False

    @fields.depends('type', 'is_gift_card')
    def on_change_with_gift_card_delivery_mode(self):
        """
        Delivery mode must be changed to virtual for service product and
        physical for goods
        """
        if not self.is_gift_card:
            return None

        if self.type == 'service':
            return 'virtual'

        if self.type == 'goods':
            return 'physical'
