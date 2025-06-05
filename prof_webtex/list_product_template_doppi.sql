select pp.active,pp.id,pp.default_code,pp.name_template,pp.product_tmpl_id,spt.min_id,spt.max_id from product_product pp inner join (select pt.name,count(pt.name),min(pt.id) as min_id,max(pt.id) as max_id from product_template as pt group by name having count(name)>1) spt 
on spt.max_id=pp.product_tmpl_id where pp.active=True order by product_tmpl_id

