# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import ntpath
import os
import shutil
import zipfile
import tempfile
import logging
from pdf2image import convert_from_bytes
from . import pyPdfScraper
import pytesseract

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero

from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)

class HrExpenseExt(models.Model):

    _inherit = ['hr.expense']
    _description = "Expense Extensions"


    def updateCustomValuesBySubject(self,msg_dict,custom_values):
        email_address = email_split(msg_dict.get('email_from', False))[0]
        if 'employee_id' not in custom_values or not custom_values['employee_id']:
                employee = self.env['hr.employee'].search([
                    '|',
                    ('work_email', 'ilike', email_address),
                    ('user_id.email', 'ilike', email_address)
                ], limit=1)
                if not employee:
                    # fallback to the the first employee.... not a good solution though
                    employee=self.env['hr.employee'].search([],limit=1)
                custom_values.update({'employee_id': employee.id,'company_id': employee.company_id.id})

        # Match the first occurence of '[]' in the string and extract the content inside it
        # Example: '[foo] bar (baz)' becomes 'foo'. This is potentially the product code
        # of the product to encode on the expense. If not, take the default product instead
        # which is 'Fixed Cost'
                         
        expense_description = msg_dict.get('subject', '')
        default_product = self.env.ref('hr_expense.product_product_fixed_cost')
        pattern = '\[([^)]*)\]'
        product_code = re.search(pattern, expense_description)
        if product_code is None:
            product = default_product
        else:
            expense_description = expense_description.replace(product_code.group(), '')
            product = self.env['product.product'].search([('default_code', 'ilike', product_code.group(1))]) or default_product
        pattern = '[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?'
        # Match the last occurence of a float in the string
        # to encode on the expense. If not, take 1.0 instead
        expense_price = re.findall(pattern, expense_description)
        # TODO: International formatting
        if 'name' not in custom_values:
            custom_values.update({'name': expense_description.strip()})
        if 'product_id' not in custom_values:
            custom_values.update({'product_id': product.id,'product_uom_id': product.uom_id.id,'quantity': 1})
        if 'unit_amount' not in custom_values:
            if not expense_price:
                price = 1.0
            else:
                price = expense_price[-1][0]
                expense_description = expense_description.replace(price, '')
                try:
                    price = float(price)
                except ValueError:
                    price = 1.0
            custom_values.update({'unit_amount': price})

        return custom_values
  
    def message_new(self, msg_dict, custom_values=None):
        rc=None
        if custom_values is None:
            custom_values={}
        pdf_attach=[]
        for fname, content, info in msg_dict['attachments']:
            if fname.find('.pdf') != -1:
                pdf_attach.append((fname, content, info))
        
        if len(pdf_attach)==0:
                if re.search(r"https:",msg_dict['body'],re.MULTILINE):
                    tmpdirname=tempfile.mkdtemp()
                    f=open(tmpdirname + '/msg.html','w')
                    f.write(msg_dict['body'].encode('utf8'))
                    tmp_pdffile=pyPdfScraper.get_pdf(tmpdirname + '/msg.html',tmpdirname)
                    f.close()
                    if tmp_pdffile:
                        f=open(tmp_pdffile,'rb')
                        fbin=f.read()
                        f.close()
                        pdf_attach.append((tmp_pdffile,fbin,''))
                        _logger.info('+++ scraping OK')
                    else:
                        _logger.warning('--- Scraping failed, %s' % tmp_pdffile)
        for attachment in pdf_attach:
                    fname, content, info = attachment
                    _logger.info('found pdf Attachment %s, try to OCR' % fname.encode('utf8'))
                    data=self.env['hbit_ocr.hbit_ocr'].ocr(content,'hr.expense')
                    if 'hr.expense' in data and data['hr.expense']:
                        _logger.info('+++ OCR ok, extracted data')
                        custom_values.update(data['hr.expense'])
                    else:
                        _logger.warning('--- OCR Failed')
                    custom_values=self.updateCustomValuesBySubject(msg_dict,custom_values)
                    RecordModel = self.env['hr.expense']
                    rc=RecordModel.create(custom_values)


        return  rc

    @api.multi
    def export_expenses(self):

        for line in self:
            attachment_obj=self.env['ir.attachment']
            config_obj = self.env['ir.config_parameter']
            attachment_data = attachment_obj.search([('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)])
            if len(attachment_data):
                filestore_path = os.path.join(attachment_obj._filestore(), '')
                tar_name='attachments'
                attachment_dir = filestore_path + tar_name
                original_dir = os.getcwd()
                # create directory and remove its content
                if not os.path.exists(attachment_dir):
                    os.makedirs(attachment_dir)
                else:
                    shutil.rmtree(attachment_dir)
                    os.makedirs(attachment_dir)
                tar_dir = os.path.join(attachment_dir, 'attachments')
                tFile = zipfile.ZipFile(tar_dir, 'w')

                for attachment in attachment_data:
                    if attachment.datas_fname.find('.pdf') == -1:
                        continue
                    attachment_name = attachment.datas_fname
                    full_path = attachment_obj._full_path(attachment.store_fname)
                    new_file = os.path.join(attachment_dir, attachment_name)
                    # copying in a new directory with a new name
                    # shutil.copyfile(full_path, new_file)
                    try:
                        shutil.copy2(full_path, new_file)
                    except:
                        pass
                    head, tail = ntpath.split(new_file)
                    # change working directory otherwise it tars all parent directory
                    os.chdir(head)
                    try:
                        tFile.write(tail)
                    except:
                        _logger.error("No such file was found : %s" %tail)

                tFile.close()
                os.chdir(original_dir)
                values = {
                        'name': tar_name + '.zip',
                        'datas_fname': tar_name + '.zip',
                        'res_model': 'hr.expense',
                        'res_id': self.ids[0],
                        'res_name': 'test....',
                        'type': 'binary',
                        'store_fname': 'attachments/attachments',
                        'active': False,
                    }
                attachment_id = self.env['ir.attachment'].create(values)
                config_ids = config_obj.search([('key', '=', 'web.base.url')])
                url = "%s/web/content/%s?download=true" % (config_ids[0].value, attachment_id.id)
                return {
                        'type': 'ir.actions.act_url',
                        'url': url,
                        'nodestroy': False,
                    }

