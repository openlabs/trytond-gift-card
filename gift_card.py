# -*- coding: utf-8 -*-
"""
    gift_card.py

    :copyright: (c) 2014-2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from num2words import num2words

from trytond.model import ModelSQL, ModelView, Workflow, fields
from trytond.pyson import Eval, If
from trytond.wizard import Wizard, Button, StateView, StateTransition
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.report import Report
from jinja2 import Environment, PackageLoader
from nereid import render_email
from trytond.config import config


__all__ = [
    'GiftCard', 'GiftCardReport', 'GiftCardRedeemStart', 'GiftCardRedeemDone',
    'GiftCardRedeemWizard',
]


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
        return [
            (None, ''),
            ('sale.sale', 'Sale'),
        ]

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
        ModelData = Pool().get('ir.model.data')
        Group = Pool().get('res.group')

        group_id = ModelData.get_id(
            "gift_card", "gift_card_email_receivers"
        )
        bcc_emails = map(
            lambda user: user.email,
            filter(lambda user: user.email, Group(group_id).users)
        )

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

        sender = config.get('email', 'from')

        email_gift_card = render_email(
            sender, self.recipient_email,
            subject,
            html_template=html_template,
            text_template=text_template,
            attachments={"%s.%s" % (val[3], val[0]): val[1]},
            card=self,
        )

        EmailQueue.queue_mail(
            sender, [self.recipient_email] + bcc_emails,
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


class GiftCardRedeemStart(ModelView):
    "Gift Card Redeem Start View"
    __name__ = 'gift_card.redeem.start'

    description = fields.Text('Description', required=True)
    gateway = fields.Many2One(
        'payment_gateway.gateway', 'Gateway', required=True,
        domain=[
            ('method', '=', 'gift_card'),
        ]
    )
    gift_card = fields.Many2One(
        'gift_card.gift_card', 'Gift Card', readonly=True
    )
    party = fields.Many2One('party.party', 'Party', required=True)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True)
    address = fields.Many2One(
        'party.address', 'Billing Address', required=True,
        domain=[('party', '=', Eval('party'))],
        depends=['party']
    )
    currency = fields.Many2One('currency.currency', 'Currency', required=True)
    currency_digits = fields.Function(
        fields.Integer('Currency Digits'),
        'on_change_with_currency_digits'
    )

    @staticmethod
    def default_currency():
        """
        Set currency of current company as default currency
        """
        Company = Pool().get('company.company')

        return Transaction().context.get('company') and \
            Company(Transaction().context.get('company')).currency.id or None

    @fields.depends('currency')
    def on_change_with_currency_digits(self, name=None):
        if self.currency:
            return self.currency.digits
        return 2

    @fields.depends('party')
    def on_change_with_address(self, name=None):  # pragma: no cover
        """
        This method returns one of the following, once the party is set -:

        * If the party has invoice addresses, the first among them is shown by
          default.
        * If the party has no invoice addresses but has addresses, the first
          among those addresses is shown.
        * If the party has no addresses, the user gets to select them.
        """
        Address = Pool().get('party.address')

        if self.party is None:  # If the party is removed altogether
            return None

        try:
            address, = Address.search([
                ('party', '=', self.party.id)],
                order=[('invoice', 'DESC')], limit=1
            )
        except ValueError:
            return None
        return address.id


class GiftCardRedeemDone(ModelView):
    "Gift Card Redeem Done View"
    __name__ = 'gift_card.redeem.end'

    done_msg = fields.Text('Redemption Complete', readonly=True)


class GiftCardRedeemWizard(Wizard):
    "Gift Card Redeem Wizard"
    __name__ = 'gift_card.redeem.wizard'

    start = StateView(
        'gift_card.redeem.start',
        'gift_card.redeem_start_view_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button(
                'Redeem', 'redeem',
                'tryton-ok', default=True
            )
        ]
    )
    redeem = StateTransition()
    done = StateView(
        'gift_card.redeem.end',
        'gift_card.redeem_done_view_form',
        [
            Button('OK', 'end', 'tryton-ok')
        ]
    )

    @classmethod
    def __setup__(cls):
        super(GiftCardRedeemWizard, cls).__setup__()
        cls._error_messages.update({
            'gift_card_inactive': (
                'The gift card to be redeemed must be in active state.'
            ),
            'gift_card_redeemed': (
                'This gift card has already been redeemed.'
            ),
            'multiple_giftcards': (
                'You can only redeem a single gift card at a'
                ' time.'
            ),
        })

    def default_start(self, data):
        """
        Initial state of redeem wizard.
        """
        Gateway = Pool().get('payment_gateway.gateway')
        GiftCard = Pool().get('gift_card.gift_card')

        try:
            gift_card_id, = Transaction().context.get('active_ids')
        except ValueError:
            self.raise_user_error('multiple_giftcards')

        gift_card = GiftCard(gift_card_id)

        self.check_giftcard_state(gift_card)

        res = {
            'gift_card': gift_card.id,
        }
        try:
            gateway, = Gateway.search([
                ('method', '=', 'gift_card'),
                ('active', '=', True),
            ])
        except ValueError:
            return res

        res.update({'gateway': gateway.id})
        return res

    def transition_redeem(self):
        """
        Transition where PaymentTransaction is created and associated
        with current gift card.
        """
        PaymentTransaction = Pool().get('payment_gateway.transaction')
        Date = Pool().get('ir.date')

        transaction, = PaymentTransaction.create([{
            'description': self.start.description,
            'date': Date.today(),
            'party': self.start.party.id,
            'address': self.start.address,
            'amount': self.start.amount,
            'currency': self.start.currency.id,
            'gateway': self.start.gateway.id,
            'gift_card': self.start.gift_card.id,
            'credit_account': self.start.party.account_receivable.id,
        }])
        PaymentTransaction.capture([transaction])

        return 'done'

    def default_done(self, data):
        """
        Returns a message with relevant details.
        """
        currency = self.start.gift_card.currency.code
        return {
            'done_msg': 'The gift card was redeemed with {0} {3} captured in'
            ' this transaction, {1} {3} captured overall and {2} {3} remaining.'
            .format(
                self.start.amount, self.start.gift_card.amount_captured,
                self.start.gift_card.amount_available, currency
            ),
        }

    def check_giftcard_state(self, gift_card):
        """
        Checks that the gift card is in active state, else throws error.
        """
        if gift_card.state == 'used':
            self.raise_user_error('gift_card_redeemed')
        elif gift_card.state != 'active':
            self.raise_user_error('gift_card_inactive')
