delete from account_invoice_line ail where ail.product_id in (select pp.id  from  product_product pp  
inner join product_template pt on product_tmpl_id=pt.id where pt.categ_id in not null );
delete from sale_order_line sol where sol.product_id in (select pp.id  from  product_product pp  
inner join product_template pt on product_tmpl_id=pt.id where pt.categ_id in not null );
delete from procurement_order po where po.product_id in (select pp.id  from  product_product pp  
inner join product_template pt on product_tmpl_id=pt.id where pt.categ_id in not null );
delete from stock_inventory_line sil where sil.product_id in (select pp.id  from  product_product pp  
inner join product_template pt on product_tmpl_id=pt.id where pt.categ_id in not null );
delete from stock_move sm where sm.product_id in (select pp.id  from  product_product pp  
inner join product_template pt on product_tmpl_id=pt.id where pt.categ_id in not null );
delete from stock_quant sq where sq.product_id in (select pp.id  from  product_product pp  
inner join product_template pt on product_tmpl_id=pt.id where pt.categ_id in not null );
delete from stock_picking;
delete form stock_move;
delete from sale_order;
