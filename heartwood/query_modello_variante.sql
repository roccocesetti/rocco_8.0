select 5 as price_version_id,pp.id,pp.product_tmpl_id,pp.default_code,pp.name_template,0 as price_surcharge,ppi.price_surcharge as costo_modello  
from product_product pp 
inner join 
product_pricelist_item ppi on pp.product_tmpl_id=ppi.product_tmpl_id and ppi.price_version_id=5 and ppi.product_id is null  and ppi.product_tmpl_id is not null



where pp.default_code is not null and (pp.id not in (select ppi1.product_id from product_pricelist_item ppi1 where ppi1.price_version_id=5 and ppi1.product_tmpl_id is Null) )