INSERT INTO stock_warehouse_orderpoint(
            product_max_qty, create_uid, qty_multiple, create_date, name, 
            location_id, company_id, write_uid, write_date, logic, active, 
            warehouse_id, product_min_qty, group_id, product_id)
    select 1000,1,1,'2017-01-20 00:00:01','OP/' || id,
    12,1,1,'2017-01-20 00:00:01','max',True,
    1,1,Null,id from product_product as pp;
