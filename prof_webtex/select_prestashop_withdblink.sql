SELECT dblink_connect('host=94.32.192.213 user=postgres password=29830000 dbname=webtex_22_05_2017 port=5434');
SELECT * FROM dblink('host=94.32.192.213
                              user=odoo80
                              password=29830000
                              dbname=webtex_22_05_2017 port=5434', 'SELECT * FROM prestashop_product ') 
                              AS 
                              t1
                              (
   id integer ,
  create_uid integer,
  need_sync character varying,
  create_date timestamp without time zone, 
  name character varying(100), 
  presta_product_id integer, 
  product_name integer, 
  presta_product_attr_id integer, 
  erp_product_id integer, 
  write_date timestamp without time zone, 
  erp_template_id integer, 
  write_uid integer 
  ) left join prestashop_product pp1 on pp1.id=t1.id where  t1.id is null