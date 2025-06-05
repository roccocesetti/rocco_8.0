insert into product_pricelist_item
(name,sequence,product_tmpl_id,base,price_version_id,min_quantity,price_surcharge) 

(select ppi.name,5,pp.product_tmpl_id,ppi.base,ppi.price_version_id,ppi.min_quantity,min(ppi.price_surcharge) 
from product_pricelist_item ppi inner join product_product pp on ppi.product_id=pp.id where ppi.price_version_id=5
group by ppi.name,5,pp.product_tmpl_id,ppi.base,ppi.price_version_id,ppi.min_quantity)