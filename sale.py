# -*- coding: utf-8 -*-
"""
    sale.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from decimal import Decimal

from trytond.model import fields, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval

__all__ = ['SaleLine', 'Sale']
__metaclass__ = PoolMeta


class SaleLine:
    "SaleLine"
    __name__ = 'sale.line'

    gift_card = fields.One2One(
        'gift_card.gift_card-sale.line', "sale_line", "gift_card", "Gift Card"
    )

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()

        if ('gift_card', 'Gift Card') not in cls.type.selection:
            cls.type.selection.append(('gift_card', 'Gift Card'))

        cls.amount.states['invisible'] = \
            cls.amount.states['invisible'] & ~(Eval('type') == 'gift_card')

        cls.unit_price.states['invisible'] = \
            cls.unit_price.states['invisible'] & ~(Eval('type') == 'gift_card')

        cls.quantity.states['invisible'] = \
            cls.quantity.states['invisible'] & ~(Eval('type') == 'gift_card')

    def get_amount(self, name):
        """
        Calculate amount for gift card line
        """
        rv = super(SaleLine, self).get_amount(name)
        if self.type == 'gift_card':
            return self.sale.currency.round(
                Decimal(str(self.quantity)) * self.unit_price)
        return rv

    def get_invoice_line(self, invoice_type):
        """
        Pick up liability account from gift card configuration for invoices
        """
        GiftCardConfiguration = Pool().get('gift_card.configuration')

        rv = super(SaleLine, self).get_invoice_line(invoice_type)
        invoice_lines = []
        for invoice_line in rv:
            if invoice_line.type == 'gift_card':
                liability_account = GiftCardConfiguration(1).liability_account
                if not liability_account:
                    self.raise_user_error(
                        "Liability Account is missing from Gift Card "
                        "Configuration"
                    )
                invoice_line.account = liability_account
                invoice_line.unit_price = self.unit_price
                invoice_line.quantity = self.quantity
            invoice_lines.append(invoice_line)
        return invoice_lines

    @fields.depends(
        'type', 'quantity', 'unit_price', 'unit',
        '_parent_sale.currency'
    )
    def on_change_with_amount(self):
        if self.type == 'gift_card':
            currency = self.sale.currency if self.sale else None
            amount = Decimal(str(self.quantity or '0.0')) * \
                (self.unit_price or Decimal('0.0'))
            if currency:
                return currency.round(amount)
            return amount
        return Decimal('0.0')


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    @classmethod
    @ModelView.button
    def process(cls, sales):
        """
        Create gift card on processing sale
        """
        GiftCard = Pool().get('gift_card.gift_card')

        rv = super(Sale, cls).process(sales)

        for sale in sales:
            for line in sale.lines:
                if line.type == 'gift_card':

                    # Create gift card for sale line
                    gift_card, = GiftCard.create([{
                        'amount': line.amount,
                        'sale_line': line.id,
                    }])

                    GiftCard.activate([gift_card])

        return rv

    @classmethod
    def get_amount(cls, sales, names):
        """
        Add amount of gift card line to total amount of sale
        """
        rv = super(Sale, cls).get_amount(sales, names)
        for sale in sales:
            for line in filter(lambda l: l.type == 'gift_card', sale.lines):
                if 'total_amount' in rv:
                    rv['total_amount'][sale.id] += line.amount
                if 'untaxed_amount' in rv:
                    rv['untaxed_amount'][sale.id] += line.amount

        return rv
