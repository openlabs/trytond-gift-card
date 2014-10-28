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

    gift_card_delivery_mode = fields.Selection([
        ('virtual', 'Virtual'),
        ('physical', 'Physical'),
        ('combined', 'Combined'),
    ], 'Gift Card Delivery Mode', states={
        'invisible': ~Bool(Eval('is_gift_card')),
        'required': Bool(Eval('is_gift_card')),
    }, depends=['is_gift_card'])

    allow_open_amount = fields.Boolean(
        "Allow Open Amount ?", states={
            'invisible': ~Bool(Eval('is_gift_card')),
        }, depends=['is_gift_card']
    )
    gc_min = fields.Numeric(
        "Gift Card Minimum Amount", states={
            'invisible': Bool(Eval('allow_open_amount')),
            'required': ~Bool(Eval('allow_open_amount')),
        }, depends=['allow_open_amount']
    )

    gc_max = fields.Numeric(
        "Gift Card Maximum Amount", states={
            'invisible': Bool(Eval('allow_open_amount')),
            'required': ~Bool(Eval('allow_open_amount')),
        }, depends=['allow_open_amount']
    )

    @staticmethod
    def default_gift_card_delivery_mode():
        return 'physical'

    @staticmethod
    def default_is_gift_card():
        return False

    @staticmethod
    def default_allow_open_amount():
        return True

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()

        cls._error_messages.update({
            'inappropriate_product':
                'Product %s is not appropriate under %s delivery mode',
            'invalid_amount':
                'Gift Card minimum amount must be smaller than gift card '
                'maximum amount',
            'negative_amount_not_allowed':
                'Gift card amounts can not be negative'
        })

    @classmethod
    def validate(cls, templates):
        """
        Validates each product template
        """
        super(Template, cls).validate(templates)

        for template in templates:
            template.check_type_and_mode()

            template.check_gc_min_max()

    def check_gc_min_max(self):
        """
        Check minimum amount to be smaller than maximum amount
        """
        if self.allow_open_amount:
            return

        if self.gc_min < 0 or self.gc_max < 0:
            self.raise_user_error("negative_amount_not_allowed")

        if self.gc_min > self.gc_max:
            self.raise_user_error("invalid_amount")

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
