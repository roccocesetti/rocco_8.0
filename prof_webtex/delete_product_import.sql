delete from product_supplierinfo psi where  psi.product_tmpl_id=
(select pt.id from product_template pt where pt.create_date>='2017-01-20 00:00:01' and pt.name not ilike('%X_ALPHA%') and psi.product_tmpl_id=pt.id);

delete from procurement_order po where  po.product_id=
(select pp.id from product_product pp where pp.product_tmpl_id=
(select pt.id from product_template pt where pt.create_date>='2017-01-20 00:00:01' and pt.name not ilike('%X_ALPHA%') and pp.product_tmpl_id=pt.id) and po.product_id=pp.id);


delete from product_template pt where (pt.create_date>='2017-01-20 00:00:01') and  pt.id not in(9143,9144);  