from odoo import models, fields, api
import base64

import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # Make name field not required
    name = fields.Char(required=False)

    # File upload fields for capture
    captured_image = fields.Binary(
        string="Captured Image",
        attachment=False
    )
    file_data = fields.Binary(
        string="Upload File",
        attachment=False
    )
    capture_filename = fields.Char(string="Filename")
    show_extracted_fields = fields.Boolean(string="Show Extracted Fields", default=False)

    @api.model
    def default_get(self, fields_list):
        """Set default values for new leads to match Capture Lead functionality"""
        res = super(CrmLead, self).default_get(fields_list)
        # Ensure type is set to 'lead' for new records
        if 'type' not in res or not res.get('type'):
            res['type'] = 'lead'
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle file upload during creation"""
        # Check if file is being uploaded during creation
        has_file_flags = [
            bool(('file_data' in vals and vals.get('file_data')) or
                 ('captured_image' in vals and vals.get('captured_image')))
            for vals in vals_list
        ]

        # Create the record
        records = super(CrmLead, self).create(vals_list)

        # If file was uploaded during creation, trigger extraction
        for record, file_in_vals in zip(records, has_file_flags):
            if file_in_vals and not record.show_extracted_fields and not self.env.context.get('auto_extracting'):
                try:
                    _logger.info(f"File detected in create() - triggering extraction for new lead")
                    record.with_context(auto_extracting=True)._extract_and_populate()
                except Exception as e:
                    _logger.error(f"Error extracting data during create: {str(e)}", exc_info=True)

        return records

    # Manav's Logic
    def write(self, vals):
        """Override write to auto-extract and populate fields when file is uploaded"""
        file_in_vals = (
                ('file_data' in vals and vals.get('file_data')) or
                ('captured_image' in vals and vals.get('captured_image'))
        )

        # Capture "had file before" PER RECORD
        leads_state = {}
        for lead in self:
            leads_state[lead.id] = bool(lead.captured_image or lead.file_data)

        res = super(CrmLead, self).write(vals)

        # Odoo 19: invalidate ORM cache so post-write field reads are fresh
        self.invalidate_recordset()

        # Post-write processing PER RECORD
        for lead in self:
            had_file_before = leads_state.get(lead.id, False)
            has_file_after = bool(lead.captured_image or lead.file_data)

            should_extract = (
                    file_in_vals or
                    (has_file_after and not had_file_before)
            )

            if (
                    should_extract and
                    not lead.show_extracted_fields and
                    not lead.env.context.get('auto_extracting')
            ):
                try:
                    _logger.info(
                        f"File detected in write() - triggering extraction for lead {lead.id}"
                    )
                    lead.with_context(auto_extracting=True)._extract_and_populate()
                except Exception as e:
                    _logger.error(
                        f"Error extracting data for lead {lead.id}: {str(e)}",
                        exc_info=True
                    )

        return res

    # def write(self, vals):
    #     """Override write to auto-extract and populate fields when file is uploaded"""
    #     # Check if file is being uploaded
    #     file_in_vals = ('file_data' in vals and vals.get('file_data')) or \
    #                    ('captured_image' in vals and vals.get('captured_image'))
    #
    #     # Check if we had file before (for existing records)
    #     # For new records (no ID yet), had_file_before will be False
    #     had_file_before = False
    #     if self.id:
    #         had_file_before = bool(self.captured_image or self.file_data)
    #
    #     res = super(CrmLead, self).write(vals)
    #
    #     # After write, check if file exists now
    #     has_file_after = bool(self.captured_image or self.file_data)
    #
    #     # Process if file was just uploaded and not already extracted
    #     # For new records: file_in_vals should be True
    #     # For existing records: file_in_vals OR (has_file_after and not had_file_before)
    #     should_extract = False
    #     if file_in_vals:
    #         # File is in vals, definitely should extract
    #         should_extract = True
    #     elif has_file_after and not had_file_before and self.id:
    #         # File appeared after write (for existing records)
    #         should_extract = True
    #
    #     if should_extract and \
    #             not self.show_extracted_fields and \
    #             not self.env.context.get('auto_extracting'):
    #         try:
    #             _logger.info(f"File detected in write() - triggering extraction for lead {self.id or 'new'}")
    #             # Ensure record has ID before extraction
    #             if not self.id:
    #                 # Record not saved yet, extraction will happen after save
    #                 _logger.warning("Record has no ID yet, extraction will be triggered after save")
    #             else:
    #                 self.with_context(auto_extracting=True)._extract_and_populate()
    #         except Exception as e:
    #             _logger.error(f"Error extracting data: {str(e)}", exc_info=True)
    #
    #     return res

    def _extract_and_populate(self):
        """Extract data from uploaded file and populate lead fields"""
        try:
            from .gemini_utils import GeminiExtractor

            api_key = self.env['ir.config_parameter'].sudo().get_param('gemini.api.key')
            _logger.info("Gemini API key present: %s", bool(api_key))
            # _logger.info(f"Got API KEY FROM CONFIG: {api_key}")
            if not api_key:
                _logger.warning("Gemini API key is not set. Please Configure it in Odoo Settings.")
                return

            extractor = GeminiExtractor(api_key=api_key)

            if self.captured_image:
                image_data = base64.b64decode(self.captured_image)
                extracted_data = extractor.extract_from_image(image_data)
            elif self.file_data:
                filename_lower = (self.capture_filename or '').lower()
                if filename_lower.endswith('.pdf'):
                    pdf_data = base64.b64decode(self.file_data)
                    extracted_data = extractor.extract_from_pdf(pdf_data)
                else:
                    image_data = base64.b64decode(self.file_data)
                    extracted_data = extractor.extract_from_image(image_data)
            else:
                return

            # Map extracted data to lead fields
            lead_vals = {}
            # print(f"~~~~~~~~~~~~~~~~~~~~~~Data: Sufiyan: {extracted_data}")

            if extracted_data.get('contact_name'):
                lead_vals['contact_name'] = extracted_data.get('contact_name')

            if extracted_data.get('company_name'):
                lead_vals['partner_name'] = extracted_data.get('company_name')

            if extracted_data.get('email'):
                lead_vals['email_from'] = extracted_data.get('email')

            if extracted_data.get('phone'):
                lead_vals['phone'] = extracted_data.get('phone')

            if extracted_data.get('mobile'):
                lead_vals['mobile'] = extracted_data.get('mobile')

            if extracted_data.get('website'):
                lead_vals['website'] = extracted_data.get('website')

            if extracted_data.get('job_position'):
                lead_vals['function'] = extracted_data.get('job_position')

            if extracted_data.get('street'):
                lead_vals['street'] = extracted_data.get('street')
            if extracted_data.get('street2'):
                lead_vals['street2'] = extracted_data.get('street2')
            if extracted_data.get('city'):
                lead_vals['city'] = extracted_data.get('city')
            if extracted_data.get('zip'):
                lead_vals['zip'] = extracted_data.get('zip')

            if extracted_data.get('state'):
                state_id = self._find_state_id(extracted_data.get('state'))
                if state_id:
                    lead_vals['state_id'] = state_id

            if extracted_data.get('country'):
                country_id = self._find_country_id(extracted_data.get('country'))
                if country_id:
                    lead_vals['country_id'] = country_id

            if extracted_data.get('title'):
                lead_vals['name'] = extracted_data.get('title')
            elif extracted_data.get('company_name'):
                lead_vals['name'] = extracted_data.get('company_name')
            elif extracted_data.get('contact_name'):
                lead_vals['name'] = f"Lead - {extracted_data.get('contact_name')}"

            description_parts = []
            if extracted_data.get('description'):
                description_parts.append(extracted_data.get('description'))
            if extracted_data.get('other_info'):
                description_parts.append(f"\nAdditional Info: {extracted_data.get('other_info')}")

            if description_parts:
                lead_vals['description'] = '\n'.join(description_parts)

            # Update lead with extracted data
            if lead_vals:
                computed_filename = self.capture_filename or 'Captured Attachment'
                if 'name' not in lead_vals or not lead_vals['name']:
                    lead_vals['name'] = f'Captured Lead - ({computed_filename})'

                # Create attachment
                attachment_data = self.captured_image or self.file_data
                if attachment_data:
                    self.env['ir.attachment'].create({
                        'name': computed_filename,
                        'type': 'binary',
                        'datas': attachment_data,
                        'res_model': 'crm.lead',
                        'res_id': self.id,
                        'mimetype': False,
                    })

                # Update lead fields
                super(CrmLead, self.with_context(auto_extracting=True)).write(lead_vals)
                self.write({'show_extracted_fields': True})

                _logger.info(f"Lead {self.id} populated with extracted data")

        except Exception as e:
            _logger.error(f"Error extracting data: {str(e)}", exc_info=True)

    # Used in _extract_and_populate
    def _find_state_id(self, state_name):
        """Find state ID by name"""
        if not state_name:
            return False
        state = self.env['res.country.state'].search([('name', 'ilike', state_name)], limit=1)
        return state.id if state else False

    # Used in _extract_and_populate
    def _find_country_id(self, country_name):
        """Find country ID by name"""
        if not country_name:
            return False
        country = self.env['res.country'].search([('name', 'ilike', country_name)], limit=1)
        return country.id if country else False