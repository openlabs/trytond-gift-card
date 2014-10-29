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
from datetime import date, datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

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
        self.Sequence = POOL.get('ir.sequence')
        self.Account = POOL.get('account.account')
        self.GiftCard = POOL.get('gift_card.gift_card')

    def _create_fiscal_year(self, date_=None, company=None):
        """
        Creates a fiscal year and requried sequences
        """
        FiscalYear = POOL.get('account.fiscalyear')
        Sequence = POOL.get('ir.sequence')
        SequenceStrict = POOL.get('ir.sequence.strict')
        Company = POOL.get('company.company')

        if date_ is None:
            date_ = datetime.utcnow().date()

        if company is None:
            company, = Company.search([], limit=1)

        invoice_sequence, = SequenceStrict.create([{
            'name': '%s' % date.year,
            'code': 'account.invoice',
            'company': company,
        }])
        fiscal_year, = FiscalYear.create([{
            'name': '%s' % date_.year,
            'start_date': date_ + relativedelta(month=1, day=1),
            'end_date': date_ + relativedelta(month=12, day=31),
            'company': company,
            'post_move_sequence': Sequence.create([{
                'name': '%s' % date_.year,
                'code': 'account.move',
                'company': company,
            }])[0],
            'out_invoice_sequence': invoice_sequence,
            'in_invoice_sequence': invoice_sequence,
            'out_credit_note_sequence': invoice_sequence,
            'in_credit_note_sequence': invoice_sequence,
        }])
        FiscalYear.create_period([fiscal_year])
        return fiscal_year

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
        self._create_fiscal_year()

        self.party1, = self.Party.create([{
            'name': 'Test party',
            'addresses': [('create', [{
                'city': 'Melbourne',
            }])],
        }])

        self.uom, = Uom.search([('name', '=', 'Unit')])

        self.product = self.create_product()

    def create_product(self, type='goods', mode='physical', is_gift_card=False):
        """
        Create default product
        """
        Template = POOL.get('product.template')

        values = {
            'name': 'product',
            'type': type,
            'list_price': Decimal('20'),
            'cost_price': Decimal('5'),
            'default_uom': self.uom.id,
            'salable': True,
            'sale_uom': self.uom.id,
            'account_revenue': self.account_revenue.id,
            'products': [
                ('create', [{
                    'code': 'Test Product'
                }])
            ]
        }

        if is_gift_card:
            values.update({
                'is_gift_card': True,
                'gift_card_delivery_mode': mode,
            })

        return Template.create([values])[0].products[0]

    def create_payment_gateway(self, method='gift_card'):
        """
        Create payment gateway
        """
        PaymentGateway = POOL.get('payment_gateway.gateway')
        Journal = POOL.get('account.journal')

        today = date.today()

        sequence, = self.Sequence.create([{
            'name': 'PM-%s' % today.year,
            'code': 'account.journal',
            'company': self.company.id
        }])

        self.account_cash, = self.Account.search([
            ('kind', '=', 'other'),
            ('name', '=', 'Main Cash'),
            ('company', '=', self.company.id)
        ])

        self.cash_journal, = Journal.create([{
            'name': 'Cash Journal',
            'code': 'cash',
            'type': 'cash',
            'credit_account': self.account_cash.id,
            'debit_account': self.account_cash.id,
            'sequence': sequence.id,
        }])

        gateway = PaymentGateway(
            name='Gift Card',
            journal=self.cash_journal,
            provider='self',
            method=method,
        )
        gateway.save()
        return gateway
