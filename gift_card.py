# -*- coding: utf-8 -*-
"""
    gift_card.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import ModelSQL, ModelView, Workflow, fields
from trytond.pyson import Eval, If

__all__ = ['GiftCard']


class GiftCard(Workflow, ModelSQL, ModelView):
    "Gift Card"
    __name__ = 'gift_card.gift_card'
    _rec_name = 'number'

    number = fields.Char(
        'Number', select=True, readonly=True,
        help='Number of the gift card'
    )
    origin = fields.Reference(
        'Origin', selection='get_origin', select=True,
        states={
            'readonly': Eval('state') != 'draft',
        }, depends=['state']
    )
    currency = fields.Many2One(
        'currency.currency', 'Currency', required=True,
        states={
            'readonly': Eval('state') != 'draft'
        }, depends=['state']
    )
    currency_digits = fields.Function(
        fields.Integer('Currency Digits'),
        'on_change_with_currency_digits'
    )
    amount = fields.Numeric(
        'Amount',
        digits=(16, Eval('currency_digits', 2)),
        states={
            'readonly': Eval('state') != 'draft'
        }, depends=['state', 'currency_digits'], required=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('cancel', 'Canceled'),
    ], 'State', readonly=True, required=True)

    @staticmethod
    def default_state():
        return 'draft'

    @classmethod
    def __setup__(cls):
        super(GiftCard, cls).__setup__()
        cls._transitions |= set((
            ('draft', 'active'),
            ('active', 'cancel'),
            ('draft', 'cancel'),
        ))
        cls._buttons.update({
            'cancel': {
                'invisible': ~Eval('state').in_(['draft', 'active']),
            },
            'draft': {
                'invisible': ~Eval('state').in_(['cancel']),
                'icon': If(
                    Eval('state') == 'cancel', 'tryton-clear',
                    'tryton-go-previous'
                ),
            },
        })

    @classmethod
    def get_origin(cls):
        return [(None, '')]
