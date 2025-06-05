                CREATE OR REPLACE VIEW stock_history_due_test AS (
                  SELECT MIN(id) as id,
                    location_id,
                    company_id,
                    product_id,
                    product_categ_id,
                    SUM(quantity) as quantity,
                    anno,
                    mese,
                    COALESCE(SUM(price_unit_on_quant * quantity) / NULLIF(SUM(quantity), 0), 0) as price_unit_on_quant
                    FROM
                    ((SELECT
                        stock_move.id AS id,
                        dest_location.id AS location_id,
                        dest_location.company_id AS company_id,
                        stock_move.product_id AS product_id,
                        product_template.categ_id AS product_categ_id,
                        quant.qty AS quantity,
                        SUBSTRING (cast (stock_move.date as character varying),0 ,5) AS anno,
                        SUBSTRING (cast (stock_move.date as character varying),6 ,2) AS mese,
                        quant.cost as price_unit_on_quant
                    FROM
                        stock_move
                    JOIN
                        stock_quant_move_rel on stock_quant_move_rel.move_id = stock_move.id
                    JOIN
                        stock_quant as quant on stock_quant_move_rel.quant_id = quant.id
                    JOIN
                       stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                    JOIN
                        stock_location source_location ON stock_move.location_id = source_location.id
                    JOIN
                        product_product ON product_product.id = stock_move.product_id
                    JOIN
                        product_template ON product_template.id = product_product.product_tmpl_id
                    WHERE SUBSTRING (cast (stock_move.date as character varying),0 ,5)>='2010' and quant.qty>0 
                    AND stock_move.state = 'done' AND dest_location.usage in ('internal', 'transit')
                      AND (
                        not (source_location.company_id is null and dest_location.company_id is null) or
                        source_location.company_id != dest_location.company_id or
                        source_location.usage not in ('internal', 'transit'))
                    ) UNION ALL
                    (SELECT
                        (-1) * stock_move.id AS id,
                        source_location.id AS location_id,
                        source_location.company_id AS company_id,
                        stock_move.product_id AS product_id,
                        product_template.categ_id AS product_categ_id,
                        - quant.qty AS quantity,
                        SUBSTRING (cast (stock_move.date as character varying),0 ,5) AS anno,
                        SUBSTRING (cast (stock_move.date as character varying),6 ,2) AS mese,
                        quant.cost as price_unit_on_quant
                    FROM
                        stock_move
                    JOIN
                        stock_quant_move_rel on stock_quant_move_rel.move_id = stock_move.id
                    JOIN
                        stock_quant as quant on stock_quant_move_rel.quant_id = quant.id
                    JOIN
                        stock_location source_location ON stock_move.location_id = source_location.id
                    JOIN
                        stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                    JOIN
                        product_product ON product_product.id = stock_move.product_id
                    JOIN
                        product_template ON product_template.id = product_product.product_tmpl_id
                    WHERE  SUBSTRING (cast (stock_move.date as character varying),0 ,5)>='2010' and stock_move.date<='2020-06-20' and stock_move.date>='2010-01-01' 
                    and quant.qty>0 AND stock_move.state = 'done' AND source_location.usage in ('internal', 'transit')
                     AND (
                        not (dest_location.company_id is null and source_location.company_id is null) or
                        dest_location.company_id != source_location.company_id or
                        dest_location.usage not in ('internal', 'transit'))
                    )) 
                    AS foo
                    GROUP BY location_id, company_id, product_id, product_categ_id, anno,mese  
                )