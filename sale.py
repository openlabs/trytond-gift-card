# -*- coding: utf-8 -*-
"""
    sale.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import fields, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction

__all__ = ['SaleLine', 'Sale']
__metaclass__ = PoolMeta


class SaleLine:
    "SaleLine"
    __name__ = 'sale.line'

    gift_card_delivery_mode = fields.Function(
        fields.Selection([
            ('virtual', 'Virtual'),
            ('physical', 'Physical'),
            ('combined', 'Combined'),
        ], 'Gift Card Delivery Mode', states={
            'invisible': ~Bool(Eval('is_gift_card')),
        }, depends=['is_gift_card']), 'on_change_with_gift_card_delivery_mode'
    )

    is_gift_card = fields.Function(
        fields.Boolean('Gift Card'),
        'on_change_with_is_gift_card'
    )
    gift_cards = fields.One2Many(
        'gift_card.gift_card', "sale_line", "Gift Cards", readonly=True
    )
    message = fields.Text(
        "Message", states={'invisible': ~Bool(Eval('is_gift_card'))}
    )

    recipient_email = fields.Char(
        "Recipient Email", states={
            'invisible': ~(
                Bool(Eval('is_gift_card')) &
                (Eval('gift_card_delivery_mode').in_(['virtual', 'combined']))
            ),
            'required': (
                Bool(Eval('is_gift_card')) &
                (Eval('gift_card_delivery_mode').in_(['virtual', 'combined']))
            ),
        }, depends=['gift_card_delivery_mode', 'is_gift_card']
    )

    recipient_name = fields.Char(
        "Recipient Name", states={
            'invisible': ~(
                Bool(Eval('is_gift_card')) &
                (Eval('gift_card_delivery_mode').in_(['virtual', 'combined']))
            ),
            'required': (
                Bool(Eval('is_gift_card')) &
                (Eval('gift_card_delivery_mode').in_(['virtual', 'combined']))
            ),
        }, depends=['gift_card_delivery_mode', 'is_gift_card']
    )

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()

        cls._error_messages.update({
            'amounts_out_of_range':
                'Gift card amount must be within %s %s and %s %s'
        })

    @fields.depends('product', 'is_gift_card')
    def on_change_with_gift_card_delivery_mode(self, name=None):
        """
        Returns delivery mode of the gift card product
        """
        if not (self.product and self.is_gift_card):
            return None

        return self.product.template.gift_card_delivery_mode

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default['gift_cards'] = None
        return super(SaleLine, cls).copy(lines, default=default)

    @fields.depends('product')
    def on_change_with_is_gift_card(self, name=None):
        """
        Returns boolean value to tell if product is gift card or not
        """
        return self.product and self.product.template.is_gift_card

    def get_invoice_line(self, invoice_type):
        """
        Pick up liability account from gift card configuration for invoices
        """
        GiftCardConfiguration = Pool().get('gift_card.configuration')
        InvoiceLine = Pool().get('account.invoice.line')

        if (not self.is_gift_card) or (invoice_type != 'out_invoice'):
            # 1. If not gift card, return value by super function
            # 2. We bill gift cards only when they are sold.
            #    Returning gift cards are bad for business ;-)
            return super(SaleLine, self).get_invoice_line(invoice_type)

        if self.invoice_lines:      # pragma: no cover
            # already invoiced
            return []

        with Transaction().set_user(0, set_context=True):
            invoice_line = InvoiceLine()

        invoice_line.type = self.type
        invoice_line.description = self.description
        invoice_line.note = self.note
        invoice_line.origin = self
        invoice_line.account = GiftCardConfiguration(1).liability_account
        invoice_line.unit_price = self.unit_price
        invoice_line.quantity = self.quantity

        if not invoice_line.account:
            self.raise_user_error(
                "Liability Account is missing from Gift Card "
                "Configuration"
            )

        return [invoice_line]

    @fields.depends('is_gift_card')
    def on_change_is_gift_card(self):
        ModelData = Pool().get('ir.model.data')

        if self.is_gift_card:
            return {
                'product': None,
                'description': 'Gift Card',
                'unit': ModelData.get_id('product', 'uom_unit'),
            }
        return {
            'description': None,
            'unit': None,
        }

    def create_gift_cards(self):
        '''
        Create the actual gift card for this line
        '''
        GiftCard = Pool().get('gift_card.gift_card')

        if not self.is_gift_card:
            # Not a gift card line
            return None

        if self.gift_cards:     # pragma: no cover
            # Cards already created
            return None

        template = self.product.template

        if not template.allow_open_amount and not (
            template.gc_min < self.amount < template.gc_max
        ):
            self.raise_user_error(
                "amounts_out_of_range", (
                    self.sale.currency.code, template.gc_min,
                    self.sale.currency.code, template.gc_max
                )
            )

        gift_cards = GiftCard.create([{
            'amount': self.amount,
            'sale_line': self.id,
            'message': self.message,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
        } for each in range(0, int(self.quantity))])

        # TODO: have option of creating card after invoice is paid ?
        GiftCard.activate(gift_cards)

        return gift_cards


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    def create_gift_cards(self):
        '''
        Create the gift cards if not already created
        '''
        for line in filter(lambda l: l.is_gift_card, self.lines):
            line.create_gift_cards()

    @classmethod
    @ModelView.button
    def process(cls, sales):
        """
        Create gift card on processing sale
        """

        super(Sale, cls).process(sales)

        for sale in sales:
            if sale.state not in ('confirmed', 'processing', 'done'):
                continue        # pragma: no cover
            sale.create_gift_cards()
