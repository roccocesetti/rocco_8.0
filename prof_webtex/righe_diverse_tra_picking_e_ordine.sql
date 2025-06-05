
select v_sol.id,v_sol.date_ord,v_sol.num_ord,nr_so,v_sm.date_picking,v_sm.num_picking,nr_pk from 

(select so.id,so.date_order as date_ord,so.name as num_ord,sol.order_id,count(sol.order_id) as nr_so from sale_order_line sol inner join sale_order so on sol.order_id=so.id 
where sol.product_id<>11986 and sol.product_id<>12671 group by so.id,so.date_order,so.name,sol.order_id) v_sol inner join

(select sm.date as date_picking,sp.origin as num_ord,sp.name as num_picking,sm.picking_id,count(sm.picking_id) as nr_pk from stock_move sm inner join stock_picking sp on sm.picking_id=sp.id 
where sp.picking_type_id=2 and sp.state<>'cancel' group by sm.date,sp.origin,sp.name,sm.picking_id) v_sm on  v_sol.num_ord=v_sm.num_ord             
where v_sol.nr_so<>v_sm.nr_pk 