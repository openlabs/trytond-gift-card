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

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction
from decimal import Decimal


class TestGiftCard(unittest.TestCase):
    '''
    Test Gift Card
    '''

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('gift_card')

    def test0040_create_gift_card(self):
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
