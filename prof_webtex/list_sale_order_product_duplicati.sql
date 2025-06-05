select * from  sale_order_line sm inner join 
(select pp.active,pp.id,pp.default_code,pp.name_template,pp.product_tmpl_id,spt.min_id,spt.max_id 
from product_product pp inner join (select count(pt.presta_product_attr_id),min(pt.erp_product_id) as min_id,max(pt.erp_product_id) as max_id 
from prestashop_product as pt group by presta_product_attr_id having count(pt.presta_product_attr_id)>1) spt 
on spt.max_id=pp.id where pp.active=True and product_tmpl_id=1811
order by product_tmpl_id ) dup on sm.product_id=dup.max_id