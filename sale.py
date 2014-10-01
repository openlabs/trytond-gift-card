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
from trytond.transaction import Transaction

__all__ = ['SaleLine', 'Sale']
__metaclass__ = PoolMeta


class SaleLine:
    "SaleLine"
    __name__ = 'sale.line'

    gift_card = fields.One2One(
        'gift_card.gift_card-sale.line', "sale_line", "gift_card", "Gift Card"
    )
    message = fields.Text(
        "Message", states={'invisible': Eval('type') != 'gift_card'}
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

        cls.unit_price.states['required'] = \
            cls.unit_price.states['required'] | (Eval('type') == 'gift_card')

    def get_amount(self, name):
        """
        Calculate amount for gift card line
        """
        if self.type != 'gift_card':
            return super(SaleLine, self).get_amount(name)
        return self.unit_price

    def get_invoice_line(self, invoice_type):
        """
        Pick up liability account from gift card configuration for invoices
        """
        GiftCardConfiguration = Pool().get('gift_card.configuration')
        InvoiceLine = Pool().get('account.invoice.line')

        rv = super(SaleLine, self).get_invoice_line(invoice_type)

        if self.type != 'gift_card':
            return rv

        if invoice_type != 'out_invoice':
            # We bill gift cards only when they are sold.
            # Returning gift cards are bad for business ;-)
            return []

        with Transaction().set_user(0, set_context=True):
            invoice_line = InvoiceLine()

        invoice_line.type = self.type
        invoice_line.description = self.description
        invoice_line.note = self.note
        invoice_line.origin = self
        invoice_line.account = GiftCardConfiguration(1).liability_account
        invoice_line.unit_price = self.unit_price
        invoice_line.quantity = 1   # FIXME

        if not invoice_line.account:
            self.raise_user_error(
                "Liability Account is missing from Gift Card "
                "Configuration"
            )

        return [invoice_line]

    @fields.depends(
        'type', 'quantity', 'unit_price', 'unit',
        '_parent_sale.currency'
    )
    def on_change_with_amount(self):
        if self.type != 'gift_card':
            return super(SaleLine, self).on_change_with_amount()

        # For gift card the price is the gift card value
        return self.unit_price or Decimal('0.0')

    def create_gift_card(self):
        '''
        Create the actual gift card for this line
        '''
        GiftCard = Pool().get('gift_card.gift_card')

        if self.type != 'gift_card':
            return None

        gift_card, = GiftCard.create([{
            'amount': self.amount,
            'sale_line': self.id,
            'message': self.message,
        }])

        GiftCard.activate([gift_card])

        return gift_card


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    @classmethod
    @ModelView.button
    def process(cls, sales):
        """
        Create gift card on processing sale
        """

        rv = super(Sale, cls).process(sales)

        for sale in sales:
            map(
                lambda line: line.create_gift_card(),
                filter(lambda l: l.type == 'gift_card', sale.lines)
            )
        return rv

    @classmethod
    def get_amount(cls, sales, names):
        """
        Add amount of gift card line to total amount of sale
        """
        rv = super(Sale, cls).get_amount(sales, names)
        for sale in sales:
            if sale.untaxed_amount_cache:
                continue
            for line in filter(lambda l: l.type == 'gift_card', sale.lines):
                if 'total_amount' in rv:
                    rv['total_amount'][sale.id] += line.amount
                if 'untaxed_amount' in rv:
                    rv['untaxed_amount'][sale.id] += line.amount

        return rv
