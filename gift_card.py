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
from jinja2 import Environment, PackageLoader
from nereid import render_email
from trytond.config import CONFIG


__all__ = ['GiftCard', 'GiftCardReport']


class GiftCard(Workflow, ModelSQL, ModelView):
    "Gift Card"
    __name__ = 'gift_card.gift_card'
    _rec_name = 'number'

    number = fields.Char(
        'Number', select=True, readonly=True, required=True,
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

    sale_line = fields.Many2One('sale.line', "Sale Line", readonly=True)

    sale = fields.Function(
        fields.Many2One('sale.sale', "Sale"), 'get_sale'
    )
    payment_transactions = fields.One2Many(
        "payment_gateway.transaction", "gift_card", "Payment Transactions",
        readonly=True
    )
    message = fields.Text("Message")
    recipient_email = fields.Char(
        "Recipient Email", states={
            'readonly': Eval('state') != 'draft'
        }
    )

    recipient_name = fields.Char(
        "Recipient Name", states={
            'readonly': Eval('state') != 'draft'
        }
    )

    is_email_sent = fields.Boolean("Is Email Sent ?", readonly=True)
    comment = fields.Text('Comment')

    def get_sale(self, name):
        """
        Return sale for gift card using sale line associated with it
        """
        return self.sale_line and self.sale_line.sale.id or None

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
                ('state', 'in', ['posted', 'done']),
                ('gift_card', '=', self.id)
            ])])

        if name == 'amount_available':
            return self.amount - sum([
                t.amount for t in PaymentTransaction.search([
                    ('state', 'in', ['authorized', 'posted', 'done']),
                    ('gift_card', '=', self.id)
                ])
            ])

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
        cls._sql_constraints = [
            ('number_uniq', 'UNIQUE(number)',
             'The number of the gift card must be unique.')
        ]
        cls._error_messages.update({
            'deletion_not_allowed':
                "Gift cards can not be deleted in active state"
        })
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
    def create(cls, vlist):
        Sequence = Pool().get('ir.sequence')
        Configuration = Pool().get('gift_card.configuration')

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if not values.get('number'):
                values['number'] = Sequence.get_id(
                    Configuration(1).number_sequence.id
                )
        return super(GiftCard, cls).create(vlist)

    @classmethod
    def copy(cls, gift_cards, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['number'] = None
        default['sale_line'] = None
        default['state'] = cls.default_state()
        default['payment_transactions'] = None
        return super(GiftCard, cls).copy(gift_cards, default=default)

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    def activate(cls, gift_cards):
        """
        Set gift cards to active state
        """
        for gift_card in gift_cards:
            if gift_card.recipient_email and not gift_card.is_email_sent:
                gift_card.send_gift_card_as_email()

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

    @classmethod
    def delete(cls, gift_cards):
        """
        It should not be possible to delete gift cards in active state
        """

        for gift_card in gift_cards:
            if gift_card.state == 'active':
                cls.raise_user_error("deletion_not_allowed")

        return super(GiftCard, cls).delete(gift_cards)

    def _get_subject_for_email(self):
        """
        Returns the text to use as subject of email
        """
        return "Gift Card - %s" % self.number

    def _get_email_templates(self):
        """
        Returns a tuple of the form:

        (html_template, text_template)
        """
        env = Environment(loader=PackageLoader(
            'trytond.modules.gift_card', 'emails'
        ))
        return (
            env.get_template('gift_card_html.html'),
            env.get_template('gift_card_text.html')
        )

    def send_gift_card_as_email(self):
        """
        Send gift card as an attachment in the email
        """
        EmailQueue = Pool().get('email.queue')
        GiftCardReport = Pool().get('gift_card.gift_card', type='report')

        if not self.recipient_email:  # pragma: no cover
            return

        # Try to generate report twice
        # This is needed as sometimes `unoconv` fails to convert report to pdf
        for try_count in range(2):
            try:
                val = GiftCardReport.execute([self.id], {})
                break
            except:  # pragma: no cover
                if try_count == 0:
                    continue
                else:
                    return

        subject = self._get_subject_for_email()
        html_template, text_template = self._get_email_templates()

        email_gift_card = render_email(
            CONFIG['smtp_from'], self.recipient_email,
            subject,
            html_template=html_template,
            text_template=text_template,
            attachments={"%s.%s" % (val[3], val[0]): val[1]},
            card=self,
        )

        EmailQueue.queue_mail(
            CONFIG['smtp_from'], self.recipient_email,
            email_gift_card.as_string()
        )
        self.is_email_sent = True
        self.save()


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
