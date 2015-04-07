# -*- coding: utf-8 -*-
"""
    sale.py

    :copyright: (c) 2014-2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import fields, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Bool
from trytond.wizard import Wizard

__all__ = [
    'SaleLine', 'Sale', 'AddSalePaymentView', 'Payment', 'AddSalePayment'
]
__metaclass__ = PoolMeta


class SaleLine:
    "SaleLine"
    __name__ = 'sale.line'

    gift_card_delivery_mode = fields.Function(
        fields.Selection([
            ('virtual', 'Virtual'),
            ('physical', 'Physical'),
            ('combined', 'Combined'),
        ], 'Gift Card Delivery Mode', states={
            'invisible': ~Bool(Eval('is_gift_card')),
        }, depends=['is_gift_card']), 'on_change_with_gift_card_delivery_mode'
    )

    is_gift_card = fields.Function(
        fields.Boolean('Gift Card'),
        'on_change_with_is_gift_card'
    )
    gift_cards = fields.One2Many(
        'gift_card.gift_card', "sale_line", "Gift Cards", readonly=True
    )
    message = fields.Text(
        "Message", states={'invisible': ~Bool(Eval('is_gift_card'))}
    )

    recipient_email = fields.Char(
        "Recipient Email", states={
            'invisible': ~(
                Bool(Eval('is_gift_card')) &
                (Eval('gift_card_delivery_mode').in_(['virtual', 'combined']))
            ),
            'required': (
                Bool(Eval('is_gift_card')) &
                (Eval('gift_card_delivery_mode').in_(['virtual', 'combined']))
            ),
        }, depends=['gift_card_delivery_mode', 'is_gift_card']
    )

    recipient_name = fields.Char(
        "Recipient Name", states={
            'invisible': ~Bool(Eval('is_gift_card')),
        }, depends=['is_gift_card']
    )
    allow_open_amount = fields.Function(
        fields.Boolean("Allow Open Amount?", states={
            'invisible': ~Bool(Eval('is_gift_card'))
        }, depends=['is_gift_card']), 'on_change_with_allow_open_amount'
    )

    gc_price = fields.Many2One(
        'product.product.gift_card.price', "Gift Card Price", states={
            'required': (
                ~Bool(Eval('allow_open_amount')) & Bool(Eval('is_gift_card'))
            ),
            'invisible': ~(
                ~Bool(Eval('allow_open_amount')) & Bool(Eval('is_gift_card'))
            )
        }, depends=['allow_open_amount', 'is_gift_card', 'product'], domain=[
            ('product', '=', Eval('product'))
        ]
    )

    @fields.depends('product')
    def on_change_with_allow_open_amount(self, name=None):
        if self.product:
            return self.product.allow_open_amount

    @fields.depends('gc_price', 'unit_price')
    def on_change_gc_price(self, name=None):
        res = {}
        if self.gc_price:
            res['unit_price'] = self.gc_price.price
        return res

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()

        cls.unit_price.states['readonly'] = (
            ~Bool(Eval('allow_open_amount')) & Bool(Eval('is_gift_card'))
        )

        cls._error_messages.update({
            'amounts_out_of_range':
                'Gift card amount must be within %s %s and %s %s'
        })

    @fields.depends('product', 'is_gift_card')
    def on_change_with_gift_card_delivery_mode(self, name=None):
        """
        Returns delivery mode of the gift card product
        """
        if not (self.product and self.is_gift_card):
            return None

        return self.product.gift_card_delivery_mode

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default['gift_cards'] = None
        return super(SaleLine, cls).copy(lines, default=default)

    @fields.depends('product')
    def on_change_with_is_gift_card(self, name=None):
        """
        Returns boolean value to tell if product is gift card or not
        """
        return self.product and self.product.is_gift_card

    def get_invoice_line(self, invoice_type):
        """
        Pick up liability account from gift card configuration for invoices
        """
        GiftCardConfiguration = Pool().get('gift_card.configuration')

        lines = super(SaleLine, self).get_invoice_line(invoice_type)

        if lines and self.is_gift_card:
            liability_account = GiftCardConfiguration(1).liability_account

            if not liability_account:
                self.raise_user_error(
                    "Liability Account is missing from Gift Card "
                    "Configuration"
                )

            for invoice_line in lines:
                invoice_line.account = liability_account

        return lines

    @fields.depends('is_gift_card')
    def on_change_is_gift_card(self):
        ModelData = Pool().get('ir.model.data')

        if self.is_gift_card:
            return {
                'product': None,
                'description': 'Gift Card',
                'unit': ModelData.get_id('product', 'uom_unit'),
            }
        return {
            'description': None,
            'unit': None,
        }

    def create_gift_cards(self):
        '''
        Create the actual gift card for this line
        '''
        GiftCard = Pool().get('gift_card.gift_card')

        if not self.is_gift_card:
            # Not a gift card line
            return None

        product = self.product

        if product.allow_open_amount and not (
            product.gc_min <= self.unit_price <= product.gc_max
        ):
            self.raise_user_error(
                "amounts_out_of_range", (
                    self.sale.currency.code, product.gc_min,
                    self.sale.currency.code, product.gc_max
                )
            )

        if self.sale.gift_card_method == 'order':
            quantity = self.quantity
        else:
            # On invoice paid
            quantity_paid = 0
            for invoice_line in self.invoice_lines:
                if invoice_line.invoice.state == 'paid':
                    invoice_line.quantity
                    quantity_paid += invoice_line.quantity

            # XXX: Do not consider cancelled ones in the gift cards.
            # card could have been cancelled for reasons like wrong message ?
            quantity_created = len(self.gift_cards)
            # Remove already created gift cards
            quantity = quantity_paid - quantity_created

        if not quantity > 0:
            # No more gift cards to create
            return

        gift_cards = GiftCard.create([{
            'amount': self.unit_price,
            'sale_line': self.id,
            'message': self.message,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'origin': '%s,%d' % (self.sale.__name__, self.sale.id),
        } for each in range(0, int(quantity))])

        GiftCard.activate(gift_cards)

        return gift_cards


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    # Gift card creation method
    gift_card_method = fields.Selection([
        ('order', 'On Order Processed'),
        ('invoice', 'On Invoice Paid'),
    ], 'Gift Card Creation Method', required=True)

    @staticmethod
    def default_gift_card_method():
        SaleConfig = Pool().get('sale.configuration')
        config = SaleConfig(1)

        return config.gift_card_method

    def create_gift_cards(self):
        '''
        Create the gift cards if not already created
        '''
        for line in filter(lambda l: l.is_gift_card, self.lines):
            line.create_gift_cards()

    @classmethod
    def get_payment_method_priority(cls):
        """Priority order for payment methods. Downstream modules can override
        this method to change the method priority.
        """
        return ('gift_card',) + \
            super(Sale, cls).get_payment_method_priority()

    @classmethod
    @ModelView.button
    def process(cls, sales):
        """
        Create gift card on processing sale
        """

        super(Sale, cls).process(sales)

        for sale in sales:
            if sale.state not in ('confirmed', 'processing', 'done'):
                continue        # pragma: no cover
            sale.create_gift_cards()


class Payment:
    'Payment'
    __name__ = 'sale.payment'

    gift_card = fields.Many2One(
        "gift_card.gift_card", "Gift Card", states={
            'required': Eval('method') == 'gift_card',
            'invisible': ~(Eval('method') == 'gift_card'),
        }, domain=[('state', '=', 'active')], depends=['method']
    )

    def _create_payment_transaction(self, amount, description):
        """Creates an active record for gateway transaction.
        """
        payment_transaction = super(Payment, self)._create_payment_transaction(
            amount, description,
        )
        payment_transaction.gift_card = self.gift_card

        return payment_transaction

    @classmethod
    def validate(cls, payments):
        """
        Validate payments
        """
        super(Payment, cls).validate(payments)

        for payment in payments:
            payment.check_gift_card_amount()

    def check_gift_card_amount(self):
        """
        Payment should not be created if gift card has insufficient amount
        """
        if self.gift_card and self.gift_card.amount_available < self.amount:
            self.raise_user_error(
                'insufficient_amount', (
                    self.gift_card.number, self.sale.currency.code, self.amount,
                )
            )

    @classmethod
    def __setup__(cls):
        super(Payment, cls).__setup__()

        cls._error_messages.update({
            'insufficient_amount':
                'Gift card %s has no sufficient amount to pay %s %s'
        })


class AddSalePaymentView:
    """
    View for adding Sale Payments
    """
    __name__ = 'sale.payment.add_view'

    gift_card = fields.Many2One(
        "gift_card.gift_card", "Gift Card", states={
            'required': Eval('method') == 'gift_card',
            'invisible': ~(Eval('method') == 'gift_card'),
        }, domain=[('state', '=', 'active')], depends=['method']
    )

    @classmethod
    def __setup__(cls):
        super(AddSalePaymentView, cls).__setup__()

        for field in [
            'owner', 'number', 'expiry_year', 'expiry_month',
            'csc', 'swipe_data', 'payment_profile'
        ]:
            getattr(cls, field).states['invisible'] = (
                getattr(cls, field).states['invisible'] |
                (Eval('method') == 'gift_card')
            )


class AddSalePayment(Wizard):
    """
    Wizard to add a Sale Payment
    """
    __name__ = 'sale.payment.add'

    def create_sale_payment(self, profile=None):
        """
        Helper function to create new payment
        """
        sale_payment = super(AddSalePayment, self).create_sale_payment(
            profile=profile
        )
        # XXX: While a value will exist for the field gift_card when
        # it's the Tryton client calling the wizard, it is not going
        # to be there as an attribute when called from API (from another
        # module/model for example).
        sale_payment.gift_card = (self.payment_info.method == 'gift_card')  \
            and self.payment_info.gift_card or None

        return sale_payment
