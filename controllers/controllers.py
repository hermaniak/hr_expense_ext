# -*- coding: utf-8 -*-
from odoo import http

# class HrExpensesExt(http.Controller):
#     @http.route('/hr_expenses_ext/hr_expenses_ext/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_expenses_ext/hr_expenses_ext/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_expenses_ext.listing', {
#             'root': '/hr_expenses_ext/hr_expenses_ext',
#             'objects': http.request.env['hr_expenses_ext.hr_expenses_ext'].search([]),
#         })

#     @http.route('/hr_expenses_ext/hr_expenses_ext/objects/<model("hr_expenses_ext.hr_expenses_ext"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_expenses_ext.object', {
#             'object': obj
#         })