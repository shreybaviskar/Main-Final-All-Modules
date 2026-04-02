from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    """
    Extend account.journal to expose the Transfer Funds wizard
    from the journal dashboard kanban card.
    """
    _inherit = 'account.journal'

    def open_transfer_funds_wizard(self):
        """Open the Transfer Funds wizard pre-filled with this journal as source."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer Funds',
            'res_model': 'driver.transfer.funds.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_journal_id': self.id,
            },
        }


class TransferFundsWizard(models.TransientModel):
    _name = 'driver.transfer.funds.wizard'
    _description = 'Transfer Funds from Driver Cash to Another Journal'

    source_journal_id = fields.Many2one(
        'account.journal',
        string="Source Journal",
        required=True,
        readonly=True,
    )
    destination_journal_id = fields.Many2one(
        'account.journal',
        string="Destination Journal",
        required=True,
        domain="[('id', '!=', source_journal_id)]",
    )
    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        compute='_compute_currency_id',
        store=True,
        readonly=False,
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
    )
    note = fields.Char(string="Memo / Note")

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------

    @api.depends('source_journal_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = (
                rec.source_journal_id.currency_id
                or rec.env.company.currency_id
            )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError("Transfer amount must be greater than zero.")

    @api.constrains('source_journal_id', 'destination_journal_id')
    def _check_different_journals(self):
        for rec in self:
            if (
                rec.source_journal_id
                and rec.destination_journal_id
                and rec.source_journal_id == rec.destination_journal_id
            ):
                raise UserError("Source and destination journals must be different.")

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def action_confirm_transfer(self):
        """
        Create an internal transfer between two journals.

        ── Odoo 18/19 Breaking Change ───────────────────────────────────
        account.payment.is_internal_transfer and destination_journal_id
        were REMOVED in Odoo 18.  The payment-based internal transfer
        workflow no longer exists.

        The correct Odoo 18/19 approach is to create TWO journal entries
        that pass through the company's Internal Transfer account
        (res.company.transfer_account_id), then reconcile the two
        transit lines to zero out that account.

        Accounting flow:
          Outgoing entry (source journal):
            DR  Internal Transfer Account    amount
            CR  Source Journal Liquidity     amount

          Incoming entry (destination journal):
            DR  Destination Journal Liquidity  amount
            CR  Internal Transfer Account      amount

          Reconcile both Internal Transfer Account lines → balance = 0
        ─────────────────────────────────────────────────────────────────
        """
        self.ensure_one()

        company = self.env.company
        ref = self.note or (
            f"Transfer: {self.source_journal_id.name}"
            f" → {self.destination_journal_id.name}"
        )

        # ── 1. Validate required accounts ───────────────────────────────

        transfer_account = company.transfer_account_id
        if not transfer_account:
            raise UserError(
                "No Internal Transfer account is configured for your company.\n"
                "Go to Accounting → Configuration → Settings → Default Accounts "
                "and set an 'Internal Transfer Account'."
            )

        src_liquidity = self.source_journal_id.default_account_id
        if not src_liquidity:
            raise UserError(
                f"Journal '{self.source_journal_id.name}' has no default "
                "liquidity account configured."
            )

        dst_liquidity = self.destination_journal_id.default_account_id
        if not dst_liquidity:
            raise UserError(
                f"Journal '{self.destination_journal_id.name}' has no default "
                "liquidity account configured."
            )

        # ── 2. Outgoing move on source journal ──────────────────────────
        #   DR Internal Transfer Account
        #   CR Source Journal Liquidity Account

        outgoing_move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.source_journal_id.id,
            'date': self.date,
            'ref': ref,
            'line_ids': [
                (0, 0, {
                    'name': ref,
                    'account_id': transfer_account.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'currency_id': self.currency_id.id,
                }),
                (0, 0, {
                    'name': ref,
                    'account_id': src_liquidity.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'currency_id': self.currency_id.id,
                }),
            ],
        })
        outgoing_move.action_post()

        # ── 3. Incoming move on destination journal ──────────────────────
        #   DR Destination Journal Liquidity Account
        #   CR Internal Transfer Account

        incoming_move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.destination_journal_id.id,
            'date': self.date,
            'ref': ref,
            'line_ids': [
                (0, 0, {
                    'name': ref,
                    'account_id': dst_liquidity.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'currency_id': self.currency_id.id,
                }),
                (0, 0, {
                    'name': ref,
                    'account_id': transfer_account.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'currency_id': self.currency_id.id,
                }),
            ],
        })
        incoming_move.action_post()

        # ── 4. Reconcile the two Internal Transfer Account lines ─────────
        # This zeroes out the transit account so the books are balanced.

        transfer_lines = (outgoing_move.line_ids + incoming_move.line_ids).filtered(
            lambda l: l.account_id == transfer_account
        )
        if len(transfer_lines) == 2 and transfer_account.reconcile:
            transfer_lines.reconcile()

        return {'type': 'ir.actions.act_window_close'}