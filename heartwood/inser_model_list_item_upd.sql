update product_pricelist_item ppi2
set price_surcharge= 

(select min(ppi.price_surcharge) 
from product_pricelist_item ppi inner join product_product pp on ppi.product_id=pp.id where ppi.price_version_id=5 and ppi2.product_tmpl_id=ppi.product_tmpl_id
group by ppi.name,pp.product_tmpl_id,ppi.base,ppi.price_version_id,ppi.min_quantity)