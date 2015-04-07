# -*- coding: utf-8 -*-
"""
    configuration.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import ModelView, ModelSQL, ModelSingleton, fields
from trytond.pool import PoolMeta

__all__ = ['Configuration', 'SaleConfiguration']
__metaclass__ = PoolMeta


class Configuration(ModelSingleton, ModelSQL, ModelView):
    "Configuration"
    __name__ = 'gift_card.configuration'

    liability_account = fields.Property(
        fields.Many2One(
            'account.account', 'Liability Account', required=True,
            domain=[('kind', '=', 'revenue')]
        )
    )

    # This field defines sequnce for the gift card number
    number_sequence = fields.Property(
        fields.Many2One(
            'ir.sequence', 'Number Sequence', required=True,
            domain=[('code', '=', 'gift_card.gift_card')],
        )
    )


class SaleConfiguration:
    __name__ = 'sale.configuration'

    # Gift card creation method
    gift_card_method = fields.Property(
        fields.Selection([
            ('order', 'On Order Processed'),
            ('invoice', 'On Invoice Paid'),
        ], 'Gift Card Creation Method', required=True)
    )
