update  sale_order set state='progress' where id=172;
update  stock_picking set state='assigned' where id=185;
update  stock_move set state='assigned' where picking_id=185;