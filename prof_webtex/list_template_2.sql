select pt.name,count(pt.name),min(pt.id) as min_id,max(pt.id) as max_id,spp.co_id from product_template as pt 

left join (select product_tmpl_id,count(pp.id) as co_id from product_product pp group by pp.product_tmpl_id) as spp on pt.id=spp.product_tmpl_id


group by pt.name,spp.co_id

having count(pt.name)>1 
order by count(pt.name) desc