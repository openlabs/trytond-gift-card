# -*- coding: utf-8 -*-
"""
    gift_card.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from num2words import num2words

from trytond.model import ModelSQL, ModelView, Workflow, fields
from trytond.pyson import Eval, If
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.report import Report

__all__ = ['GiftCard', 'GiftCardSaleLine', 'GiftCardReport']


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

    amount_authorized = fields.Function(
        fields.Numeric(
            "Amount Authorized", digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']
        ), 'get_amount'
    )
    amount_captured = fields.Function(
        fields.Numeric(
            "Amount Captured", digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']
        ), 'get_amount'
    )

    amount_available = fields.Function(
        fields.Numeric(
            "Amount Available", digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']
        ), 'get_amount'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('used', 'Used'),
    ], 'State', readonly=True, required=True)

    sale_line = fields.One2One(
        'gift_card.gift_card-sale.line', 'gift_card', 'sale_line', "Sale Line",
        readonly=True
    )
    payment_transactions = fields.One2Many(
        "payment_gateway.transaction", "gift_card", "Payment Transactions",
        readonly=True
    )

    @staticmethod
    def default_currency():
        """
        Set currency of current company as default currency
        """
        Company = Pool().get('company.company')

        return Transaction().context.get('company') and \
            Company(Transaction().context.get('company')).currency.id or None

    def get_amount(self, name):
        """
        Returns authorzied, captured and available amount for the gift card
        """
        PaymentTransaction = Pool().get('payment_gateway.transaction')

        if name == 'amount_authorized':
            return sum([t.amount for t in PaymentTransaction.search([
                ('state', '=', 'authorized'),
                ('gift_card', '=', self.id)
            ])])

        if name == 'amount_captured':
            return sum([t.amount for t in PaymentTransaction.search([
                ('state', '=', 'posted'),
                ('gift_card', '=', self.id)
            ])])

        if name == 'amount_available':
            return self.amount - self.amount_authorized - self.amount_captured

    @staticmethod
    def default_state():
        return 'draft'

    @fields.depends('currency')
    def on_change_with_currency_digits(self, name=None):
        if self.currency:
            return self.currency.digits
        return 2

    @classmethod
    def __setup__(cls):
        super(GiftCard, cls).__setup__()
        cls._transitions |= set((
            ('draft', 'active'),
            ('active', 'canceled'),
            ('draft', 'canceled'),
            ('canceled', 'draft'),
        ))
        cls._buttons.update({
            'cancel': {
                'invisible': ~Eval('state').in_(['draft', 'active']),
            },
            'draft': {
                'invisible': ~Eval('state').in_(['canceled']),
                'icon': If(
                    Eval('state') == 'cancel', 'tryton-clear',
                    'tryton-go-previous'
                ),
            },
            'activate': {
                'invisible': Eval('state') != 'draft',
            }
        })

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    def activate(cls, gift_cards):
        """
        Set gift cards to active state
        """
        for card in gift_cards:
            card.generate_sequence()

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, gift_cards):
        """
        Set gift cards back to draft state
        """
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('canceled')
    def cancel(cls, gift_cards):
        """
        Cancel gift cards
        """
        pass

    @classmethod
    def get_origin(cls):
        return [(None, '')]

    def generate_sequence(self):
        """
        Fills the code field with number sequence

        """
        Sequence = Pool().get('ir.sequence')
        Configuration = Pool().get('gift_card.configuration')

        if not self.number:
            self.number = Sequence.get_id(Configuration(1).number_sequence.id)
            self.save()


class GiftCardSaleLine(ModelSQL):
    "Gift Card Sale Line"

    __name__ = 'gift_card.gift_card-sale.line'

    gift_card = fields.Many2One(
        "gift_card.gift_card", "Gift Card", required=True, select=True
    )

    sale_line = fields.Many2One(
        'sale.line', 'Sale Line', required=True, select=True
    )


class GiftCardReport(Report):
    __name__ = 'gift_card.gift_card'

    @classmethod
    def parse(cls, report, records, data, localcontext):
        """
        Update localcontext to add num2words
        """
        localcontext.update({
            'num2words': lambda *args, **kargs: num2words(
                *args, **kargs)
        })
        return super(GiftCardReport, cls).parse(
            report, records, data, localcontext
        )
