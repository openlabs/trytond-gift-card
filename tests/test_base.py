# -*- coding: utf-8 -*-
"""
    test_base

    :copyright: (C) 2014 by Openlabs Technologies & Consulting (P) Limited
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
from decimal import Decimal

from trytond.tests.test_tryton import POOL, USER
import trytond.tests.test_tryton
from trytond.transaction import Transaction


class TestBase(unittest.TestCase):
    """
    Base Test Case for gift card
    """

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('gift_card')

        self.Currency = POOL.get('currency.currency')
        self.Company = POOL.get('company.company')
        self.Party = POOL.get('party.party')
        self.User = POOL.get('res.user')
        self.Country = POOL.get('country.country')
        self.SubDivision = POOL.get('country.subdivision')

    def _create_coa_minimal(self, company):
        """Create a minimal chart of accounts
        """
        AccountTemplate = POOL.get('account.account.template')
        Account = POOL.get('account.account')

        account_create_chart = POOL.get(
            'account.create_chart', type="wizard"
        )

        account_template, = AccountTemplate.search(
            [('parent', '=', None)]
        )

        session_id, _, _ = account_create_chart.create()
        create_chart = account_create_chart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()

        receivable, = Account.search([
            ('kind', '=', 'receivable'),
            ('company', '=', company),
        ])
        payable, = Account.search([
            ('kind', '=', 'payable'),
            ('company', '=', company),
        ])
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()

    def _get_account_by_kind(self, kind, company=None, silent=True):
        """Returns an account with given spec

        :param kind: receivable/payable/expense/revenue
        :param silent: dont raise error if account is not found
        """
        Account = POOL.get('account.account')
        Company = POOL.get('company.company')

        if company is None:
            company, = Company.search([], limit=1)

        accounts = Account.search([
            ('kind', '=', kind),
            ('company', '=', company)
        ], limit=1)
        if not accounts and not silent:
            raise Exception("Account not found")
        return accounts[0] if accounts else False

    def _create_payment_term(self):
        """Create a simple payment term with all advance
        """
        PaymentTerm = POOL.get('account.invoice.payment_term')

        return PaymentTerm.create([{
            'name': 'Direct',
            'lines': [('create', [{'type': 'remainder'}])]
        }])[0]

    def setup_defaults(self):
        """
        Setup the defaults
        """
        User = POOL.get('res.user')
        Uom = POOL.get('product.uom')
        Template = POOL.get('product.template')
        Product = POOL.get('product.product')

        self.usd, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        with Transaction().set_context(company=None):
            self.party, = self.Party.create([{
                'name': 'Openlabs',
            }])
            self.company, = self.Company.create([{
                'party': self.party.id,
                'currency': self.usd
            }])

        User.write(
            [User(USER)], {
                'main_company': self.company.id,
                'company': self.company.id,
            }
        )

        self._create_coa_minimal(company=self.company.id)
        self.account_revenue = self._get_account_by_kind('revenue')
        self.account_expense = self._get_account_by_kind('expense')
        self._create_payment_term()

        self.party1, = self.Party.create([{
            'name': 'Test party',
            'addresses': [('create', [{
                'city': 'Melbourne',
            }])],
        }])

        self.uom, = Uom.search([('name', '=', 'Unit')])

        self.template1, = Template.create([{
            'name': 'product',
            'type': 'goods',
            'list_price': Decimal('20'),
            'cost_price': Decimal('5'),
            'default_uom': self.uom.id,
            'salable': True,
            'sale_uom': self.uom.id,
            'account_revenue': self.account_revenue.id,
        }])

        self.product1, = Product.create([{
            'template': self.template1.id,
        }])
