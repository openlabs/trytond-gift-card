# -*- coding: utf-8 -*-
"""
    configuration.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from decimal import Decimal

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval


__all__ = ['Invoice', 'InvoiceLine']
__metaclass__ = PoolMeta


class Invoice:
    'Invoice'
    __name__ = 'account.invoice'

    @classmethod
    def get_amount(cls, invoices, names):
        rv = super(Invoice, cls).get_amount(invoices, names)
        for invoice in invoices:
            for line in filter(lambda l: l.type == 'gift_card', invoice.lines):
                if 'untaxed_amount' in rv:
                    rv['untaxed_amount'][invoice.id] += line.amount

                if 'total_amount' in rv:
                    rv['total_amount'][invoice.id] += line.amount
        return rv


class InvoiceLine:
    'Invoice Line'
    __name__ = 'account.invoice.line'

    message = fields.Text(
        "Message", states={'invisible': Eval('type') != 'gift_card'}
    )

    @classmethod
    def __setup__(cls):
        super(InvoiceLine, cls).__setup__()

        if ('gift_card', 'Gift Card') not in cls.type.selection:

            cls.type.selection.append(('gift_card', 'Gift Card'))

        cls.amount.states['invisible'] = \
            cls.amount.states['invisible'] & ~(Eval('type') == 'gift_card')

        cls.unit_price.states['invisible'] = \
            cls.unit_price.states['invisible'] & ~(Eval('type') == 'gift_card')

        cls.unit_price.states['required'] = \
            cls.unit_price.states['required'] | (Eval('type') == 'gift_card')

    def get_amount(self, name):
        """
        Calulate amount for invoice line of gift card type
        """
        if self.type != 'gift_card':
            return super(InvoiceLine, self).get_amount(name)
        return self.unit_price

    @fields.depends('type', 'quantity', 'unit_price',
        '_parent_invoice.currency', 'currency')
    def on_change_with_amount(self):
        if self.type != 'gift_card':
            return super(InvoiceLine, self).on_change_with_amount()

        # For gift card the price is the gift card value
        return self.unit_price or Decimal('0.0')
