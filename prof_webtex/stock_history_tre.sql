select pp.default_code,sh.* from stock_history_tre as sh inner join product_product pp on sh.product_id=pp.id 
where  product_id=3786 and product_categ_id=20 order by product_id,anno,mese