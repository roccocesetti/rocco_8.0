delete from stock_move  sm_2 where id in

(select   max(sm.id)  as id from stock_move sm 

inner join product_product pp on pp.id=sm.product_id
inner join 
( select sp.name,sp.id from stock_picking sp inner join (select po.name,po.id from procurement_group  po inner join 
(select so.id as id ,so.name as name,so.note as note_ord from sale_order so where so.note='nota__credito_creata') so1 on po.name=so1.name) pg 
on sp.group_id=pg.id and sp.name like('%/IN/%') 
group by sp.name ,sp.id  order by sp.name,sp.id ) sp_2 on sm.picking_id=sp_2.id
group by sm.origin,sm.name, pp.default_code,sm.product_id,sm.price_unit,product_uom_qty having count(*)>1) 