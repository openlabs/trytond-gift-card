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
            GiftCard.active([gift_card])

            self.assertEqual(gift_card.state, 'active')

            # Gift card can be calcelled from active state
            GiftCard.cancel([gift_card])

            self.assertEqual(gift_card.state, 'cancel')

            # Gift card can be set back to draft state once cancelled
            GiftCard.draft([gift_card])

            self.assertEqual(gift_card.state, 'draft')

            # Gift card can be cancelled from draft state also
            GiftCard.cancel([gift_card])

            self.assertEqual(gift_card.state, 'cancel')


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
