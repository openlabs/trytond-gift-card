# -*- coding: utf-8 -*-
"""
    gateway.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta
from trytond.model import fields, ModelView, Workflow
from trytond.pyson import Eval

__all__ = [
    'PaymentGateway', 'PaymentTransaction'
]

__metaclass__ = PoolMeta


class PaymentGateway:
    "Gift Card Gateway Implementation"
    __name__ = 'payment_gateway.gateway'

    def get_methods(self):
        rv = super(PaymentGateway, self).get_methods()
        gift_card = ('gift_card', 'Gift Card')
        if self.provider == 'self' and gift_card not in rv:
            rv.append(gift_card)
        return rv


class PaymentTransaction:
    """
    Implement the authorize and capture methods
    """
    __name__ = 'payment_gateway.transaction'

    gift_card = fields.Many2One(
        'gift_card.gift_card', 'Gift Card', domain=[('state', '=', 'active')],
        states={
            'required': Eval('method') == 'gift_card',
            'readonly': Eval('state') != 'draft'
        }, select=True
    )

    @classmethod
    def __setup__(cls):
        super(PaymentTransaction, cls).__setup__()

        cls._error_messages.update({
            'insufficient_amount':
                'Card %s is found to have insufficient amount'
        })

        cls._buttons['authorize']['invisible'] = \
            cls._buttons['authorize']['invisible'] & ~(
                (Eval('state') == 'draft') &
                (Eval('method') == 'gift_card')
        )
        cls._buttons['capture']['invisible'] = \
            cls._buttons['capture']['invisible'] & ~(
                (Eval('state') == 'draft') &
                (Eval('method') == 'gift_card')
        )

        cls._buttons['settle']['invisible'] = \
            cls._buttons['settle']['invisible'] & ~(
                (Eval('state') == 'authorized') &
                (Eval('method') == 'gift_card')
        )

    def validate_gift_card_amount(self, available_amount):
        """
        Validates that gift card has sufficient amount to pay
        """
        if available_amount < self.amount:
            self.raise_user_error("insufficient_amount", self.gift_card.number)

    def authorize_self(self):
        """
        Authorize using gift card for the specific transaction.
        """
        if self.method == 'gift_card':
            self.validate_gift_card_amount(self.gift_card.amount_available)

        return super(PaymentTransaction, self).authorize_self()

    def capture_self(self):
        """
        Capture using gift card for the specific transaction.
        """
        if self.method == 'gift_card':
            self.validate_gift_card_amount(self.gift_card.amount_available)

        return super(PaymentTransaction, self).capture_self()

    def settle_self(self):
        """
        Settle using gift card for the specific transaction.
        """
        if self.method == 'gift_card':
            # Ignore authorized amount as settlement will be done for
            # previously authorized amount
            available_amount = \
                self.gift_card.amount - self.gift_card.amount_captured
            self.validate_gift_card_amount(available_amount)

        return super(PaymentTransaction, self).settle_self()

    @classmethod
    @ModelView.button
    @Workflow.transition('posted')
    def post(cls, transactions):
        """
        Complete the transactions by creating account moves and post them.

        This method is likely to end in failure if the initial configuration
        of the journal and fiscal periods have not been done. You could
        alternatively use the safe_post instance method to try to post the
        record, but ignore the error silently.
        """
        rv = super(PaymentTransaction, cls).post(transactions)

        for transaction in transactions:
            if transaction.gift_card and \
                    transaction.gift_card.amount_available == 0:
                transaction.gift_card.state = 'used'
                transaction.gift_card.save()
        return rv
