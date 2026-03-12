from odoo import models
from dateutil import parser, relativedelta as RelativeD
import time
from datetime import datetime
import json

relativedelta = RelativeD.relativedelta


class ResCompany(models.Model):
    _inherit = "res.company"

