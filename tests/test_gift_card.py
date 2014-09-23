# -*- coding: utf-8 -*-
"""
    tests/test_gift_card.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))
import unittest
from datetime import date

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction
from decimal import Decimal
from test_base import TestBase
from trytond.exceptions import UserError


class TestGiftCard(TestBase):
    '''
    Test Gift Card
    '''

    def test0010_create_gift_card(self):
        """
        Create gift card
        """
        GiftCard = POOL.get('gift_card.gift_card')
        Currency = POOL.get('currency.currency')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):

            self.usd = Currency(
                name='US Dollar', symbol=u'$', code='USD',
            )
            self.usd.save()

            gift_card, = GiftCard.create([{
                'currency': self.usd.id,
                'amount': Decimal('20'),
            }])

            self.assertEqual(gift_card.state, 'draft')

    def test0015_on_change_currency(self):
        """
        Check if currency digits are changed because of currency of gift
        card
        """
        GiftCard = POOL.get('gift_card.gift_card')
        Currency = POOL.get('currency.currency')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):

            self.usd = Currency(
                name='US Dollar', symbol=u'$', code='USD', digits=3
            )
            self.usd.save()

            gift_card = GiftCard(currency=self.usd.id)

            self.assertEqual(gift_card.on_change_with_currency_digits(), 3)

            gift_card = GiftCard(currency=None)

            self.assertEqual(gift_card.on_change_with_currency_digits(), 2)

    def test0020_gift_card_on_processing_sale(self):
        """
        Check if gift card is being created on processing sale
        """
        Sale = POOL.get('sale.sale')
        GiftCard = POOL.get('gift_card.gift_card')
        Invoice = POOL.get('account.invoice')
        Configuration = POOL.get('gift_card.configuration')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):

            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):

                Configuration.create([{
                    'liability_account': self._get_account_by_kind('revenue').id
                }])
                sale, = Sale.create([{
                    'reference': 'Sale1',
                    'sale_date': date.today(),
                    'invoice_address': self.party1.addresses[0].id,
                    'shipment_address': self.party1.addresses[0].id,
                    'party': self.party1.id,
                    'lines': [
                        ('create', [{
                            'type': 'line',
                            'quantity': 2,
                            'unit': self.uom,
                            'unit_price': 200,
                            'description': 'Test description1',
                            'product': self.product1.id,
                        }, {
                            'type': 'gift_card',
                            'quantity': 1,
                            'unit': self.uom,
                            'unit_price': 500,
                            'description': 'Test description2',
                        }])
                    ]

                }])

                # Gift card line amount is included in untaxed amount
                self.assertEqual(sale.untaxed_amount, 900)

                # Gift card line amount is included in total amount
                self.assertEqual(sale.total_amount, 900)

                Sale.quote([sale])
                Sale.confirm([sale])

                self.assertFalse(GiftCard.search([]))

                self.assertFalse(Invoice.search([]))

                Sale.process([sale])

                self.assertTrue(GiftCard.search([]))

                self.assertEqual(GiftCard.search([], count=True), 1)

                self.assertEqual(Invoice.search([], count=True), 1)

                gift_card, = GiftCard.search([])

                invoice, = Invoice.search([])

                self.assertEqual(gift_card.amount, 500)
                self.assertEqual(gift_card.state, 'active')

                self.assertEqual(invoice.untaxed_amount, 900)
                self.assertEqual(invoice.total_amount, 900)

    def test0025_gift_card_on_processing_sale_without_liability_account(self):
        """
        Check if gift card is being created on processing sale when liability
        account is missing from gift card configuration
        """
        Sale = POOL.get('sale.sale')
        GiftCard = POOL.get('gift_card.gift_card')
        Invoice = POOL.get('account.invoice')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):

            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):
                sale, = Sale.create([{
                    'reference': 'Sale1',
                    'sale_date': date.today(),
                    'invoice_address': self.party1.addresses[0].id,
                    'shipment_address': self.party1.addresses[0].id,
                    'party': self.party1.id,
                    'lines': [
                        ('create', [{
                            'type': 'line',
                            'quantity': 2,
                            'unit': self.uom,
                            'unit_price': 200,
                            'description': 'Test description1',
                            'product': self.product1.id,
                        }, {
                            'type': 'gift_card',
                            'quantity': 1,
                            'unit': self.uom,
                            'unit_price': 500,
                            'description': 'Test description2',
                        }])
                    ]

                }])

                # Gift card line amount is included in untaxed amount
                self.assertEqual(sale.untaxed_amount, 900)

                # Gift card line amount is included in total amount
                self.assertEqual(sale.total_amount, 900)

                Sale.quote([sale])
                Sale.confirm([sale])

                self.assertFalse(GiftCard.search([]))

                self.assertFalse(Invoice.search([]))

                with self.assertRaises(UserError):
                    Sale.process([sale])

    def test0030_check_on_change_amount(self):
        """
        Check if amount is changed with quantity and unit price
        """
        SaleLine = POOL.get('sale.line')
        Sale = POOL.get('sale.sale')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):

                # 1. Sale with currency and sale line type as "gift_card"
                sale, = Sale.create([{
                    'reference': 'Sale1',
                    'sale_date': date.today(),
                    'invoice_address': self.party1.addresses[0].id,
                    'shipment_address': self.party1.addresses[0].id,
                    'party': self.party1.id
                }])

                sale_line = SaleLine(
                    quantity=3, unit_price=Decimal('22.56789'),
                    type='gift_card', sale=sale
                )

                self.assertEqual(
                    sale_line.on_change_with_amount(), Decimal('67.70')
                )

                # 2. Sale Line without sale and type as "gift_card"
                sale_line = SaleLine(
                    quantity=3, unit_price=Decimal('22.56789'),
                    type='gift_card', sale=None
                )

                self.assertEqual(
                    sale_line.on_change_with_amount(), Decimal('67.70367')
                )

                # 3. Sale Line with type other than "gift_card"
                sale_line = SaleLine(
                    quantity=3, unit_price=Decimal('22.56789'),
                    type='subtotal', sale=None
                )

                self.assertEqual(
                    sale_line.on_change_with_amount(), Decimal('0')
                )

    def test0040_gift_card_transition(self):
        """
        Check gift card transitions
        """
        GiftCard = POOL.get('gift_card.gift_card')
        Currency = POOL.get('currency.currency')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):

            self.usd = Currency(
                name='US Dollar', symbol=u'$', code='USD',
            )
            self.usd.save()

            gift_card, = GiftCard.create([{
                'currency': self.usd.id,
                'amount': Decimal('20'),
            }])

            self.assertEqual(gift_card.state, 'draft')

            # Gift card can become active in draft state
            GiftCard.activate([gift_card])

            self.assertEqual(gift_card.state, 'active')

            # Gift card can be calcelled from active state
            GiftCard.cancel([gift_card])

            self.assertEqual(gift_card.state, 'canceled')

            # Gift card can be set back to draft state once canceled
            GiftCard.draft([gift_card])

            self.assertEqual(gift_card.state, 'draft')

            # Gift card can be canceled from draft state also
            GiftCard.cancel([gift_card])

            self.assertEqual(gift_card.state, 'canceled')

    def test0050_gift_card_sequence(self):
        """
        Check sequence is created on activating gift card
        """
        GiftCard = POOL.get('gift_card.gift_card')
        Currency = POOL.get('currency.currency')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):

            self.usd = Currency(
                name='US Dollar', symbol=u'$', code='USD',
            )
            self.usd.save()

            gift_card, = GiftCard.create([{
                'currency': self.usd.id,
                'amount': Decimal('20'),
            }])

            self.assertFalse(gift_card.number)

            GiftCard.activate([gift_card])

            self.assertTrue(gift_card.number)

    def test0050_authorize_gift_card_payment_gateway_valid_card(self):
        """
        Test gift card authorization
        """
        GiftCard = POOL.get('gift_card.gift_card')
        PaymentTransaction = POOL.get('payment_gateway.transaction')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):

                active_gift_card, = GiftCard.create([{
                    'amount': Decimal('150'),
                    'number': '45671338',
                    'state': 'active',
                }])

                gateway = self.create_payment_gateway()

                # Case 1: Gift card available amount > amount to be paid
                payment_transaction = PaymentTransaction(
                    description="Pay invoice using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('50'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                payment_transaction.authorize_gift_card()

                self.assertEqual(payment_transaction.state, 'authorized')

                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('50')
                )

                self.assertEqual(
                    active_gift_card.amount_available, Decimal('100')
                )

                # Case 2: Gift card available amount = amount to be paid
                payment_transaction = PaymentTransaction(
                    description="Pay invoice using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('100'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                payment_transaction.authorize_gift_card()

                self.assertEqual(payment_transaction.state, 'authorized')

                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('150')
                )

                self.assertEqual(
                    active_gift_card.amount_available, Decimal('0')
                )

                active_gift_card, = GiftCard.create([{
                    'amount': Decimal('0'),
                    'number': '45671338',
                    'state': 'active',
                }])

                # Case 2: Gift card amount < amount to be paid
                payment_transaction = PaymentTransaction(
                    description="Pay invoice using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('100'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                with self.assertRaises(Exception):
                    payment_transaction.authorize_gift_card()

    def test0055_capture_gift_card_payment_gateway_valid_card(self):
        """
        Test capturing of gift card
        """
        GiftCard = POOL.get('gift_card.gift_card')
        PaymentTransaction = POOL.get('payment_gateway.transaction')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):

                active_gift_card, = GiftCard.create([{
                    'amount': Decimal('150'),
                    'number': '45671338',
                    'state': 'active',
                }])

                gateway = self.create_payment_gateway()

                # Case 1: Gift card available amount > amount to be paid
                payment_transaction = PaymentTransaction(
                    description="Pay invoice using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('50'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                payment_transaction.capture_gift_card()

                self.assertEqual(payment_transaction.state, 'posted')

                self.assertEqual(
                    active_gift_card.amount_captured, Decimal('50')
                )

                self.assertEqual(
                    active_gift_card.amount_available, Decimal('100')
                )

                # Case 2: Gift card available amount = amount to be paid
                payment_transaction = PaymentTransaction(
                    description="Pay invoice using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('100'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                payment_transaction.capture_gift_card()

                self.assertEqual(payment_transaction.state, 'posted')
                self.assertEqual(
                    active_gift_card.amount_captured, Decimal('150')
                )

                self.assertEqual(
                    active_gift_card.amount_available, Decimal('0')
                )
                self.assertEqual(active_gift_card.state, 'used')

                active_gift_card, = GiftCard.create([{
                    'amount': Decimal('0'),
                    'number': '45671338',
                    'state': 'active',
                }])

                # Case 2: Gift card amount < amount to be paid
                payment_transaction = PaymentTransaction(
                    description="Pay invoice using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('100'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                with self.assertRaises(Exception):
                    payment_transaction.capture_gift_card()

    def test0060_payment_gateway_methods_and_providers(self):
        """
        Tests gateway methods
        """
        PaymentGateway = POOL.get('payment_gateway.gateway')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            gateway = PaymentGateway(
                provider='self',
            )
            self.assertTrue(gateway.get_methods())
            self.assertTrue(('gift_card', 'Gift Card') in gateway.get_methods())

            gateway = PaymentGateway(
                provider='authorize.net',
            )
            self.assertFalse(gateway.get_methods())

    def test0070_gift_card_amount(self):
        """
        Check authorized, captured and available amount fro gift card
        """
        GiftCard = POOL.get('gift_card.gift_card')
        PaymentTransaction = POOL.get('payment_gateway.transaction')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):

                active_gift_card, = GiftCard.create([{
                    'amount': Decimal('200'),
                    'number': '45671338',
                    'state': 'active',
                }])

                gateway = self.create_payment_gateway()

                # Payment transactions in authorized state
                payment_transaction1 = PaymentTransaction(
                    description="Payment Transaction 1",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('70'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction1.save()

                PaymentTransaction.authorize([payment_transaction1])

                payment_transaction2 = PaymentTransaction(
                    description="Payment Transaction 2",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('20'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction2.save()

                PaymentTransaction.authorize([payment_transaction2])

                # Payment transactions being captured
                payment_transaction3 = PaymentTransaction(
                    description="Payment Transaction 3",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('10'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction3.save()

                PaymentTransaction.capture([payment_transaction3])

                payment_transaction4 = PaymentTransaction(
                    description="Payment Transaction 4",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('20'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction4.save()

                PaymentTransaction.capture([payment_transaction4])

            self.assertEqual(active_gift_card.amount_authorized, 90)
            self.assertEqual(active_gift_card.amount_captured, 30)
            self.assertEqual(active_gift_card.amount_available, 80)


def suite():
    """
    Define suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestGiftCard)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
