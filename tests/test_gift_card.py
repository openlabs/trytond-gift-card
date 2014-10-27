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
        SaleLine = POOL.get('sale.line')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):

            self.setup_defaults()

            gift_card_product = self.create_product(is_gift_card=True)

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
                            'product': self.product.id,
                        }, {
                            'quantity': 1,
                            'unit': self.uom,
                            'unit_price': 500,
                            'description': 'Gift Card',
                            'product': gift_card_product,
                        }, {
                            'type': 'comment',
                            'description': 'Test line',
                        }])
                    ]

                }])

                sale_line1, = SaleLine.search([
                    ('sale', '=', sale.id),
                    ('product', '=', gift_card_product.id),
                ])

                sale_line2, = SaleLine.search([
                    ('sale', '=', sale.id),
                    ('product', '=', self.product.id),
                ])

                sale_line3, = SaleLine.search([
                    ('sale', '=', sale.id),
                    ('product', '=', None),
                ])

                self.assertTrue(sale_line1.is_gift_card)
                self.assertFalse(sale_line2.is_gift_card)
                self.assertFalse(sale_line3.is_gift_card)

                # Gift card line amount is included in untaxed amount
                self.assertEqual(sale.untaxed_amount, 900)

                # Gift card line amount is included in total amount
                self.assertEqual(sale.total_amount, 900)

                Sale.quote([sale])

                self.assertEqual(sale.untaxed_amount, 900)
                self.assertEqual(sale.total_amount, 900)

                Sale.confirm([sale])

                self.assertEqual(sale.untaxed_amount, 900)
                self.assertEqual(sale.total_amount, 900)

                self.assertFalse(
                    GiftCard.search([('sale_line', '=', sale_line1.id)])
                )

                self.assertFalse(Invoice.search([]))

                Sale.process([sale])

                self.assertEqual(sale.untaxed_amount, 900)
                self.assertEqual(sale.total_amount, 900)

                self.assertTrue(
                    GiftCard.search([('sale_line', '=', sale_line1.id)])
                )

                self.assertEqual(
                    GiftCard.search(
                        [('sale_line', '=', sale_line1.id)], count=True
                    ), 1
                )

                self.assertEqual(Invoice.search([], count=True), 1)

                gift_card, = GiftCard.search([
                    ('sale_line', '=', sale_line1.id)
                ])

                invoice, = Invoice.search([])

                self.assertEqual(gift_card.amount, 500)
                self.assertEqual(gift_card.state, 'active')
                self.assertEqual(gift_card.sale, sale)

                self.assertEqual(invoice.untaxed_amount, 900)
                self.assertEqual(invoice.total_amount, 900)

    def test0025_create_gift_card_for_line(self):
        """
        Check if gift card is not create if sale line is of type line
        """
        Sale = POOL.get('sale.sale')
        SaleLine = POOL.get('sale.line')
        GiftCard = POOL.get('gift_card.gift_card')
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
                }])
                sale_line, = SaleLine.create([{
                    'sale': sale.id,
                    'type': 'line',
                    'quantity': 2,
                    'unit': self.uom,
                    'unit_price': 200,
                    'description': 'Test description1',
                    'product': self.product.id,
                }])

                self.assertFalse(
                    GiftCard.search([('sale_line', '=', sale_line.id)])
                )

                sale_line.create_gift_cards()

                # No gift card is created
                self.assertFalse(
                    GiftCard.search([('sale_line', '=', sale_line.id)])
                )

                sale_line3, = SaleLine.copy([sale_line])
                self.assertFalse(sale_line3.gift_cards)

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

            gift_card_product = self.create_product(is_gift_card=True)

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
                            'product': self.product.id,
                        }, {
                            'quantity': 1,
                            'unit': self.uom,
                            'unit_price': 500,
                            'description': 'Test description2',
                            'product': gift_card_product
                        }])
                    ]

                }])

                # Gift card line amount is included in untaxed amount
                self.assertEqual(sale.untaxed_amount, 900)

                # Gift card line amount is included in total amount
                self.assertEqual(sale.total_amount, 900)

                Sale.quote([sale])
                Sale.confirm([sale])

                self.assertFalse(
                    GiftCard.search([('sale_line.sale', '=', sale.id)])
                )

                self.assertFalse(Invoice.search([]))

                with self.assertRaises(UserError):
                    Sale.process([sale])

    def test0030_check_on_change_amount(self):
        """
        Check if amount is changed with quantity and unit price
        """
        SaleLine = POOL.get('sale.line')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):

                # Sale line as gift card
                sale_line = SaleLine(
                    unit_price=Decimal('22.56789'),
                    type='line', sale=None
                )

                on_change_vals = sale_line.on_change_is_gift_card()
                self.assertTrue('description' in on_change_vals)
                self.assertTrue('product' not in on_change_vals)

                sale_line.is_gift_card = True
                on_change_vals = sale_line.on_change_is_gift_card()

                self.assertEqual(on_change_vals['product'], None)
                self.assertTrue('description' in on_change_vals)
                self.assertTrue('unit' in on_change_vals)

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

            self.assertTrue(gift_card.number)

            number = gift_card.number
            GiftCard.activate([gift_card])
            self.assertEqual(gift_card.number, number)

            gift_card2, = GiftCard.copy([gift_card])
            self.assertNotEqual(gift_card2.number, number)

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

                # Case 1:
                # Gift card available amount (150) > amount to be paid (50)
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

                PaymentTransaction.authorize([payment_transaction])

                self.assertEqual(payment_transaction.state, 'authorized')

                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('50')
                )

                self.assertEqual(
                    active_gift_card.amount_available, Decimal('100')
                )

                # Case 2: Gift card amount (100) < amount to be paid (300)
                payment_transaction = PaymentTransaction(
                    description="Pay invoice using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('300'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                with self.assertRaises(UserError):
                    PaymentTransaction.authorize([payment_transaction])

    def test0055_capture_gift_card(self):
        """
        Test capturing of gift card
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

                self.assertEqual(
                    active_gift_card.amount_captured, Decimal('0')
                )

                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('0')
                )

                self.assertEqual(
                    active_gift_card.amount_available, Decimal('200')
                )

                # Capture
                # Case 1
                # Gift card available amount(200) > amount to be paid (180)
                payment_transaction = PaymentTransaction(
                    description="Pay using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('100'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                PaymentTransaction.capture([payment_transaction])

                self.assertEqual(payment_transaction.state, 'posted')

                self.assertEqual(
                    active_gift_card.amount_captured, Decimal('100')
                )
                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('0')
                )

                # 200 - 100 = 100
                self.assertEqual(
                    active_gift_card.amount_available, Decimal('100')
                )

                # Case 2
                # Gift card available amount (100) = amount to be paid (100)
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

                PaymentTransaction.capture([payment_transaction])

                self.assertEqual(payment_transaction.state, 'posted')
                self.assertEqual(
                    active_gift_card.amount_captured, Decimal('200')
                )
                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('0')
                )

                # 200 - 200 = 0
                self.assertEqual(
                    active_gift_card.amount_available, Decimal('0')
                )
                self.assertEqual(active_gift_card.state, 'used')

                active_gift_card, = GiftCard.create([{
                    'amount': Decimal('10'),
                    'number': '45671339',
                    'state': 'active',
                }])

                # Case 3: Gift card amount (10) < amount to be paid (100)
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

                with self.assertRaises(UserError):
                    PaymentTransaction.capture([payment_transaction])

    def test0057_settle_gift_card(self):
        """
        Test settlement of gift card
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

                # Authorization of gift card
                # Case 1: Gift card available amount > amount to be paid
                payment_transaction = PaymentTransaction(
                    description="Pay using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('100'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                PaymentTransaction.authorize([payment_transaction])

                self.assertEqual(
                    active_gift_card.amount_captured, Decimal('0')
                )

                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('100')
                )

                # 200 - 100 = 100
                self.assertEqual(
                    active_gift_card.amount_available, Decimal('100')
                )

                # Settlement
                # Case 1: Gift card amount (100) > amount to be settled (50)
                payment_transaction = PaymentTransaction(
                    description="Pay using gift card",
                    party=self.party1.id,
                    address=self.party1.addresses[0].id,
                    amount=Decimal('50'),
                    currency=self.company.currency.id,
                    gateway=gateway.id,
                    gift_card=active_gift_card,
                )
                payment_transaction.save()

                PaymentTransaction.authorize([payment_transaction])

                self.assertEqual(
                    active_gift_card.amount_captured, Decimal('0')
                )

                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('150')
                )

                # 100 - 50 = 50
                self.assertEqual(
                    active_gift_card.amount_available, Decimal('50')
                )

                PaymentTransaction.settle([payment_transaction])

                self.assertEqual(payment_transaction.state, 'posted')

                self.assertEqual(
                    active_gift_card.amount_captured, Decimal('50')
                )
                self.assertEqual(
                    active_gift_card.amount_authorized, Decimal('100')
                )

                # 200 - 100 - 50 = 50
                self.assertEqual(
                    active_gift_card.amount_available, Decimal('50')
                )

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

    def test0080_test_gift_card_report(self):
        """
        Test Gift Card report
        """
        GiftCard = POOL.get('gift_card.gift_card')
        GiftCardReport = POOL.get('gift_card.gift_card', type='report')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):

                gift_card, = GiftCard.create([{
                    'amount': Decimal('200'),
                    'number': '45671338',
                    'state': 'active',
                }])

                val = GiftCardReport.execute([gift_card.id], {})

                self.assert_(val)
                # Assert report name
                self.assertEqual(val[3], 'Gift Card')

    def test0090_test_gift_card_deletion(self):
        """
        Test that Gift Card should not be deleted in active state
        """
        GiftCard = POOL.get('gift_card.gift_card')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            with Transaction().set_context({'company': self.company.id}):

                gift_card, = GiftCard.create([{
                    'amount': Decimal('200'),
                    'number': '45671338',
                    'state': 'active',
                }])

                with self.assertRaises(Exception):
                    GiftCard.delete([gift_card])

                # Try to delete gift card in some other state and it will
                # be deleted
                gift_card, = GiftCard.create([{
                    'amount': Decimal('200'),
                    'number': '45671339',
                    'state': 'draft',
                }])

                GiftCard.delete([gift_card])


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
