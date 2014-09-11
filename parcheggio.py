class stock_move(osv.osv):
    _inherit = 'stock.move'     
    _columns={
              'doc_line_id': fields.one2many('fiscaldoc.righe', 'move_ids', 'Riga Doc. di Vendita', readonly=True),             
               }       
    
stock_move()


class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns={
              'doc_id': fields.one2many('fiscaldoc.header', 'name', 'Documento di Vendita', readonly=True),             
               }       
    
stock_picking()

 