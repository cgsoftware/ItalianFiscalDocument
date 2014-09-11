# -*- encoding: utf-8 -*-
##############################################################################
#    
#    Copyright (C) 2009 Italian Community (http://www). 
#    All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Gestione Documenti Fiscali Italiani',
    'version': '0.1',
    'category': 'ItalianFiscalDocument',
    'description': """Questo Modulo fornisce una gestione più organica dei documenti fiscali come fatture/note credito/note di addebito DDT/ Bolle di vendita / Ricevute e Fatture fiscali.
		      Il modulo si integra e si frappone tra l'attuale gestione ordini e la gestione del magazzino e della contabilità in modo da influire poco sui work flow standard e con la possibilità 
		      di inserne di nuovi per ogni tipologia di documento.
    """,
    'author': 'C & G Software sas',
    'website': 'http://www.cgsoftware.it',
    "depends" : ['base', 'account', 'base_vat', 'product', 'l10n_it_base', 'l10n_it_sale','price_for_partner','commission'],
    "update_xml" : [
		    'FiscalDocumentAccessori_view.xml',
		    'FiscalDocument_view.xml', 
		    'wizard/StampaDoc.xml',
		    'wizard/GeneraFattDifferite.xml',
		    'wizard/EvadiOrdini.xml', 
		    'security/ir.model.access.csv',
		    'product_view.xml'
		    ],
    "active": False,
    "installable": True
}

