# -*- coding: utf-8 -*-
"""
    configuration.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from decimal import Decimal

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

    @classmethod
    def __setup__(cls):
        super(InvoiceLine, cls).__setup__()

        if ('gift_card', 'Gift Card') not in cls.type.selection:

            cls.type.selection.append(('gift_card', 'Gift Card'))

            cls.unit_price.states.update({
                'invisible': ~Eval('type').in_(['line', 'gift_card'])
            })
            cls.quantity.states.update({
                'invisible': ~Eval('type').in_(['line', 'gift_card'])
            })
            cls.amount.states.update({
                'invisible': ~Eval('type').in_(['line', 'gift_card'])
            })

    def get_amount(self, name):
        """
        Calulate amount for invoice line of gift card type
        """
        rv = super(InvoiceLine, self).get_amount(name)
        if self.type == 'gift_card':
            return self.currency.round(
                Decimal(str(self.quantity)) * self.unit_price)
        return rv
