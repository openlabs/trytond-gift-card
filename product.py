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

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()

        cls._error_messages.update({
            'inappropriate_product':
                'Product %s is not appropriate under %s delivery mode'
        })

    @classmethod
    def validate(cls, templates):
        """
        Validates each product template
        """
        super(Template, cls).validate(templates)

        for template in templates:
            template.check_type_and_mode()

    def check_type_and_mode(self):
        """
        Type must be service only if delivery mode is virtual

        Type must be goods only if delivery mode is combined or physical
        """
        if not self.is_gift_card:
                return

        if (
            self.gift_card_delivery_mode == 'virtual' and
            self.type != 'service'
        ) or (
            self.gift_card_delivery_mode in ['physical', 'combined'] and
            self.type != 'goods'
        ):
            self.raise_user_error(
                "inappropriate_product", (
                    self.rec_name, self.gift_card_delivery_mode
                )
            )
