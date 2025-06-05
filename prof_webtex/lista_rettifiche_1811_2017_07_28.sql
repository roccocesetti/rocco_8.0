select sm.* from stock_move sm inner join product_product pp on sm.product_id=pp.id 
where pp.product_tmpl_id=1810 
and sm.name like('%INV:INV%')
and sm.create_date>='2017-07-28 00:00:00'
and sm.create_date<='2017-07-28 23:59:59'