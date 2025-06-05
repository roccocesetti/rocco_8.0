insert into stock_route_product (product_id,route_id)
select srt.product_id,1 from stock_route_product srt group by srt.product_id 