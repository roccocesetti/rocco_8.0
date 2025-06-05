
update    stock_picking_package_preparation_line spppl set  name='[' || (select pp1.default_code from product_product  pp1 where pp1.id=spppl.product_id) || ']' || spppl.name
 where  spppl.package_preparation_id>286 and name not like('%[%');
update    stock_move sm set  name='[' || (select pp1.default_code from product_product  pp1 where pp1.id=sm.product_id) || ']' || sm.name
 where  create_date>'2019-04-1' and name not like('%[%') ; 