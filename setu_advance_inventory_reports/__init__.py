from . import controller
from . import wizard
from odoo import api, SUPERUSER_ID

def pre_init(cr):
    # env = api.Environment(cr, SUPERUSER_ID, {})
    create_get_stock_data_sp(cr)
    create_sale_transaction_sp(cr)
    create_get_products_forecasted_stock_data_sp(cr)
    create_overstock_sp(cr)
    create_get_products_stock_movements_sp(cr)
    create_opening_stock_sp(cr)
    create_get_inventory_turnover_ratio_data_sp(cr)
    create_get_inventory_fsn_analysis_report_data_sp(cr)
    create_get_xyz_analysis_data_sp(cr)
    create_get_fsn_xyz_analysis_data_sp(cr)
    create_get_products_outofstock_data_sp(cr)
    create_get_stock_age_data_sp(cr)
    create_get_stock_age_breakdown_data_sp(cr)

def create_get_stock_data_sp(cr):
    query = """
        -- DROP FUNCTION public.get_stock_data(integer[], integer[], integer[], integer[], text, date, date);
        CREATE OR REPLACE FUNCTION public.get_stock_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN transaction_type text,
            IN start_date date,
            IN end_date date)
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, product_qty numeric) AS
        $BODY$
        DECLARE 
            source_usage text;
            dest_usage text;
        BEGIN
            source_usage := case 
                        when transaction_type in ('sales','transit_out','production_out','internal_out', 'adjustment_out', 'internal_in','purchase_return') 
                            then 'internal' 
                        when transaction_type = 'purchase' then 'supplier'
                        when transaction_type = 'transit_in' then 'transit'
                        when transaction_type = 'adjustment_in' then 'inventory'
                        when transaction_type = 'production_in' then 'production'
                        when transaction_type = 'sales_return' then 'customer'
                    end;
            dest_usage := case 
                        when transaction_type in ('purchase','transit_in','adjustment_in','production_in', 'internal_in', 'internal_out', 'sales_return') 
                            then 'internal' 
                        when transaction_type = 'sales' then 'customer'
                        when transaction_type = 'transit_out' then 'transit'
                        when transaction_type = 'adjustment_out' then 'inventory'
                        when transaction_type = 'production_out' then 'production'
                        when transaction_type = 'purchase_return' then 'supplier'
                    end;
                
            RETURN QUERY 
            Select 
                T.company_id,
                T.company_name,
                T.product_id,
                T.product_name,
                T.category_id,
                T.category_name,
                T.warehouse_id,
                T.warehouse_name,
                coalesce(sum(T.product_qty),0) as product_qty
            From
            (
                Select 
                    move.company_id,
                    cmp.name as company_name,
                    move.product_id as product_id,
                    prod.default_code as product_name,
                    tmpl.categ_id as category_id,
                    cat.complete_name as category_name,
                    case when transaction_type in ('sales','transit_out','production_out','internal_out', 'adjustment_out', 'purchase_return') then 
                        source_warehouse.id else  dest_warehouse.id end as warehouse_id,
                    case when transaction_type in ('sales','transit_out','production_out','internal_out', 'adjustment_out', 'purchase_return') then 
                        source_warehouse.name else  dest_warehouse.name end as warehouse_name,
                    move.product_uom_qty as product_qty
                From 
                    stock_move move
                        Inner Join stock_location source on source.id = move.location_id
                        Inner Join stock_location dest on dest.id = move.location_dest_id
                        Inner Join res_company cmp on cmp.id = move.company_id
                        Inner Join product_product prod on prod.id = move.product_id 
                        Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                        Inner Join product_category cat on cat.id = tmpl.categ_id
                        Left Join stock_warehouse source_warehouse ON source.parent_path::text ~~ concat('%/', source_warehouse.view_location_id, '/%')
                        Left Join stock_warehouse dest_warehouse ON dest.parent_path::text ~~ concat('%/', dest_warehouse.view_location_id, '/%')
                where prod.active = true and tmpl.active = true
                and source.usage = source_usage and dest.usage = dest_usage 
                and move.date::date >= start_date and move.date::date <= end_date 
                and move.state = 'done'
                and tmpl.type = 'product'
                
                --company dynamic condition
                and 1 = case when array_length(company_ids,1) >= 1 then 
                    case when move.company_id = ANY(company_ids) then 1 else 0 end
                    else 1 end
                --product dynamic condition
                and 1 = case when array_length(product_ids,1) >= 1 then 
                    case when move.product_id = ANY(product_ids) then 1 else 0 end
                    else 1 end
                --category dynamic condition
                and 1 = case when array_length(category_ids,1) >= 1 then 
                    case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                    else 1 end
                --warehouse dynamic condition
                and 1 = case when array_length(warehouse_ids,1) >= 1 then 
                        case when transaction_type in ('sales','transit_out','production_out','internal_out', 'adjustment_out','purchase_return'	) then 
                            case when source_warehouse.id = ANY(warehouse_ids) then 1 else 0 end 
                        else  
                            case when dest_warehouse.id = ANY(warehouse_ids) then 1 else 0 end
                        end
                    else 1 end
            )T
            group by T.company_id, T.product_id, T.category_id, T.warehouse_id, T.company_name, T.product_name, T.category_name, T.warehouse_name
            ;
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_sale_transaction_sp(cr):
    query = """
        -- DROP FUNCTION public.get_sales_transaction_data(integer[], integer[], integer[], integer[], date, date);

        CREATE OR REPLACE FUNCTION public.get_sales_transaction_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date)
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, sales numeric) AS
        $BODY$
        BEGIN
            Return Query
            Select 	
                cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name, sum(product_qty) as total_sales
            From
            (	
                select 
                    T.company_id as cmp_id, T.company_name as cmp_name, 
                    T.product_id as p_id, T.product_name as prod_name, 
                    T.product_category_id as categ_id, T.category_name as cat_name, 
                    T.warehouse_id as wh_id, T.warehouse_name as ware_name,  
                    product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales' ,start_date, end_date) T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    product_qty * -1 
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sale_return' ,start_date, end_date) T
        
            )T
            group by cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name;
        
        END; 
        
        $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_get_products_forecasted_stock_data_sp(cr):
    query="""
        -- DROP FUNCTION public.get_products_forecasted_stock_data(integer[], integer[], integer[], integer[]);
        
        CREATE OR REPLACE FUNCTION public.get_products_forecasted_stock_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[])
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, qty_available numeric, outgoing numeric, incoming numeric, forecasted_stock numeric) AS
        $BODY$
        BEGIN
            Return Query
            Select 
                T.company_id, cmp.name as company_name, T.product_id, coalesce(prod.default_code, tmpl.name) as product_name,
                T.categ_id as product_category_id, cat.complete_name as category_name, T.warehouse_id, ware.name as warehouse_name, 
                T.qty_available::numeric, T.incoming::numeric, T.outgoing::numeric, (T.qty_available + T.incoming - T.outgoing)::numeric as forecasted_qty
            From
            (
                Select 
                    quant.company_id,
                    quant.product_id,
                    tmpl.categ_id,
                    ware.id as warehouse_id,
                    quantity as qty_available,
                    reserved_quantity as outgoing,
                    0 as incoming
                from 
                    stock_quant quant
                        Inner Join stock_location loc on loc.id = quant.location_id
                        Inner Join product_product prod on prod.id = quant.product_id
                        Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                        Left Join stock_warehouse ware ON loc.parent_path::text ~~ concat('%/', ware.view_location_id, '/%')
                Where loc.usage = 'internal' and prod.active = True and tmpl.active = True and tmpl.type = 'product'
                    --company dynamic condition
                    and 1 = case when array_length(company_ids,1) >= 1 then 
                        case when quant.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    --product dynamic condition
                    and 1 = case when array_length(product_ids,1) >= 1 then 
                        case when quant.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    --category dynamic condition
                    and 1 = case when array_length(category_ids,1) >= 1 then 
                        case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                    --warehouse dynamic condition
                    and 1 = case when array_length(warehouse_ids,1) >= 1 then 
                        case when ware.id = ANY(warehouse_ids) then 1 else 0 end
                        else 1 end
        
                Union All
        
                Select 
                    move.company_id,
                    move.product_id,
                    tmpl.categ_id,
                    dest_ware.id as warehouse_id,
                    0 as qty_available,
                    0 as outgoing,
                    move.product_uom_qty
                from 
                    stock_move move
                        Inner Join stock_location source on source.id = move.location_id
                        Inner Join stock_location dest_location on dest_location.id = move.location_dest_id
                        Inner Join product_product prod on prod.id = move.product_id
                        Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                        Left Join stock_warehouse source_ware ON source.parent_path::text ~~ concat('%/', source_ware.view_location_id, '/%')
                        Left Join stock_warehouse dest_ware ON dest_location.parent_path::text ~~ concat('%/', dest_ware.view_location_id, '/%')
                Where 
                    source.usage = 'supplier' and dest_location.usage = 'internal' and move.state not in ('draft','done','cancel') and 
                    prod.active = True and tmpl.active = True and tmpl.type = 'product'
                    --company dynamic condition
                    and 1 = case when array_length(company_ids,1) >= 1 then 
                        case when move.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    --product dynamic condition
                    and 1 = case when array_length(product_ids,1) >= 1 then 
                        case when move.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    --category dynamic condition
                    and 1 = case when array_length(category_ids,1) >= 1 then 
                        case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                    --warehouse dynamic condition
                    and 1 = case when array_length(warehouse_ids,1) >= 1 then 
                        case when dest_ware.id = ANY(warehouse_ids) then 1 else 0 end
                        else 1 end
            )T
                Inner Join res_company cmp on cmp.id = T.company_id
                Inner Join product_product prod on prod.id = T.product_id 
                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                Inner Join product_category cat on cat.id = tmpl.categ_id
                Inner Join stock_warehouse ware on ware.id = T.warehouse_id;
        
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;

    """
    cr.execute(query)

def create_overstock_sp(cr):
    query="""
        -- DROP FUNCTION public.get_products_overstock_data(integer[], integer[], integer[], integer[], date, date, integer);
        
        CREATE OR REPLACE FUNCTION public.get_products_overstock_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date,
            IN advance_stock_days integer)
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, sales numeric, ads numeric, qty_available numeric, outgoing numeric, incoming numeric, forecasted_stock numeric, demanded_qty numeric, coverage_days numeric, overstock_qty numeric, overstock_value numeric, last_purchase_date date, last_purchase_qty numeric, last_purchase_price numeric, currency_name character varying, vendor_name character varying, wh_overstock_qty_per numeric, wh_overstock_value_per numeric, turnover_ratio numeric, stock_movement text) AS
        $BODY$
        BEGIN
            Drop Table if exists overstock_transaction_table;
            CREATE TEMPORARY TABLE overstock_transaction_table(
                company_id INT,
                company_name character varying,
                product_id INT,
                product_name character varying,
                product_category_id INT,
                category_name character varying, 
                warehouse_id INT,
                warehouse_name character varying, 
                sales numeric DEFAULT 0,
                ads numeric DEFAULT 0,
                qty_available Numeric DEFAULT 0,
                outgoing numeric DEFAULT 0,
                incoming Numeric DEFAULT 0,
                forecasted_stock Numeric DEFAULT 0,
                demanded_qty Numeric DEFAULT 0,
                coverage_days Numeric DEFAULT 0,
                overstock_qty Numeric DEFAULT 0,
                overstock_value Numeric DEFAULT 0,
                last_purchase_date Date,
                last_purchase_qty Numeric,
                last_purchase_price Numeric,
                currency_name character varying,
                vendor_name character varying
            );
        
            Insert into overstock_transaction_table
            Select 
                final_data.company_id, cmp.name, final_data.product_id, prod.default_code, 
                tmpl.categ_id, cat.complete_name, final_data.warehouse_id, ware.name,
                final_data.sales, final_data.ads, final_data.qty_available, final_data.outgoing, final_data.incoming,
                final_data.forecasted_stock, final_data.demanded_qty, final_data.coverage_days, final_data.overstock_qty,
                round((final_data.overstock_qty * stock_value)::numeric,0) ovestock_value, final_data.purchase_date, 
                final_data.purchase_qty, final_data.purchase_price, final_data.currency, final_data.vendor
            From
            (
                Select 
                    stock_data.* , coalesce(round(sales_data.sales,0),0) as sales, coalesce(sales_data.ads,0) as ads, 
                    Round(coalesce(advance_stock_days * sales_data.ads,0),0) as demanded_qty, 
                    coalesce(Round((stock_data.forecasted_stock / case when sales_data.ads <= 0.0000 then 0.001 else sales_data.ads end)::numeric, 0),0) as coverage_days,
                    coalesce(ir_property.value_float,0) as stock_value, 
                    coalesce(Round((stock_data.forecasted_stock - (advance_stock_days * coalesce(sales_data.ads,0)))::numeric,0),0) as overstock_qty,
                    po_data.purchase_date, po_data.purchase_qty, po_data.purchase_price, po_data.currency, po_data.vendor
                From
                (
                    Select T.* from get_products_forecasted_stock_data(company_ids, product_ids, category_ids, warehouse_ids) T
                    where t.forecasted_stock > 0
                )stock_data
        
                Left Join
                (
                    select *, Round(D1.sales / ((end_date - start_date) + 1),2) as ads 
                    from get_sales_transaction_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date) D1
                )sales_data
                    on stock_data.product_id = sales_data.product_id and stock_data.warehouse_id = sales_data.warehouse_id 
                    Left Join ir_property on ir_property.name = 'standard_price' and ir_property.res_id = 'product.product,' || stock_data.product_id
                    and ir_property.company_id = stock_data.company_id
                Left Join 
                (
                    Select
                        po_line.product_id, 
                        ware.id as warehouse_id,
                        po.date_order::date as purchase_date,
                        po_line.product_uom_qty as purchase_qty,
                        po_line.price_unit as purchase_price,
                        cur.name as currency,
                        partner.name as vendor
                    From
                    (
                        Select categ_id, pol.product_id, max(pol.id) po_line_id 
                        from purchase_order_line pol
                            Inner Join product_product prod on prod.id = pol.product_id 
                            Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                            
                        where 1 = case when array_length(product_ids,1) >= 1 then 
                                case when pol.product_id = ANY(product_ids) then 1 else 0 end
                              else 1 end
                        and 1 = case when array_length(category_ids,1) >= 1 then 
                                case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                            else 1 end
                        group by pol.product_id, categ_id
                    )p_l
                        Inner Join purchase_order_line po_line on p_l.po_line_id = po_line.id
                        Inner Join purchase_order po on po.id = po_line.order_id
                        Inner join stock_picking_type picking_type on picking_type.id = po.picking_type_id
                        Inner Join stock_warehouse ware on ware.id = picking_type.warehouse_id 	
                        Inner Join res_partner partner on partner.id = po.partner_id
                        Inner Join res_currency cur on cur.id = po.currency_id
                    where 1 = case when array_length(warehouse_ids,1) >= 1 then 					
                            case when ware.id = ANY(warehouse_ids) then 1 else 0 end
                          else 1 end
                    and 1 = case when array_length(company_ids,1) >= 1 then 
                            case when po.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                )po_data
                    on po_data.product_id = stock_data.product_id and po_data.warehouse_id = stock_data.warehouse_id
            )final_data
                Inner Join res_company cmp on cmp.id = final_data.company_id
                Inner Join product_product prod on prod.id = final_data.product_id 
                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                Inner Join product_category cat on cat.id = tmpl.categ_id
                Inner Join stock_warehouse ware on ware.id = final_data.warehouse_id;
        
            Return Query
            with all_data as (
                Select * from overstock_transaction_table
            ),
            warehouse_wise_overstock as(
                Select ott.warehouse_id, ott.company_id, sum(ott.overstock_qty) as total_overstock_qty, sum(ott.overstock_value) as total_overstock_value
                from overstock_transaction_table ott
                group by ott.warehouse_id, ott.company_id
            ),
            fsn_analysis as(
                Select * 
                from get_inventory_fsn_analysis_report(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, 'all') f_data
            )
        
            Select 
                all_data.*, 
                case when wwover.total_overstock_qty <= 0.00 then 0 else 
                    Round(all_data.overstock_qty / wwover.total_overstock_qty * 100,2) 
                end as warehouse_overstock_qty ,
                case when wwover.total_overstock_value <= 0.00 then 0 else
                    Round(all_data.overstock_value / wwover.total_overstock_value * 100,2) 
                end as warehouse_overstock_value,
                fsn.turnover_ratio,
                fsn.stock_movement
            from all_data
                Inner Join warehouse_wise_overstock wwover on wwover.warehouse_id = all_data.warehouse_id
                Left Join fsn_analysis fsn on fsn.product_id = all_data.product_id and fsn.warehouse_id = all_data.warehouse_id;
            
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_get_products_stock_movements_sp(cr):
    query = """
    -- DROP FUNCTION public.get_products_stock_movements(integer[], integer[], integer[], integer[], date, date);
    
    CREATE OR REPLACE FUNCTION public.get_products_stock_movements(
        IN company_ids integer[],
        IN product_ids integer[],
        IN category_ids integer[],
        IN warehouse_ids integer[],
        IN start_date date,
        IN end_date date)
      RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, opening_stock numeric, sales numeric, sales_return numeric, purchase numeric, purchase_return numeric, internal_in numeric, internal_out numeric, adjustment_in numeric, adjustment_out numeric, production_in numeric, production_out numeric, transit_in numeric, transit_out numeric, closing numeric) AS
    $BODY$
        DECLARE
            tr_start_date date;
            tr_end_date date;
    
    BEGIN	
        Drop Table if exists transaction_table;
        CREATE TEMPORARY TABLE transaction_table(
            company_id INT,
            company_name character varying,
            product_id INT,
            product_name character varying,
            product_category_id INT,
            category_name character varying, 
            warehouse_id INT,
            warehouse_name character varying, 
            opening_stock Numeric DEFAULT 0,
            sales Numeric DEFAULT 0,
            sales_return numeric DEFAULT 0,
            purchase Numeric DEFAULT 0,
            purchase_return numeric DEFAULT 0,
            internal_in Numeric DEFAULT 0,
            internal_out Numeric DEFAULT 0,
            adjustment_in Numeric DEFAULT 0,
            adjustment_out Numeric DEFAULT 0,
            production_in Numeric DEFAULT 0,
            production_out Numeric DEFAULT 0,
            transit_in Numeric DEFAULT 0,
            transit_out Numeric DEFAULT 0,
            closing Numeric DEFAULT 0
        );
    
        IF start_Date is not null then 
            tr_start_date := '1900-01-01';
            tr_end_date := start_date - interval '1 day';
            Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, opening_stock)
            select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, T.opening_stock
            from get_products_opening_stock(company_ids, product_ids, category_ids, warehouse_ids, tr_start_date, tr_end_date) T;
        END IF;
    
        -- Sales
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, sales)
        select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales', start_date, end_date)T;
    
        -- Sales Return
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, sales_return)
        select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales_return', start_date, end_date)T;
    
        -- Purchase 
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, purchase)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'purchase', start_date, end_date)T;
    
        -- Purchase Return
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, purchase_return)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'purchase_return', start_date, end_date)T;
        
        -- Internal IN
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, internal_in)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'internal_in', start_date, end_date)T;
    
    
        -- Internal Out 
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, internal_out)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'internal_out', start_date, end_date)T;
        
        -- Adjustment IN
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, adjustment_in)
        select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'adjustment_in', start_date, end_date)T;
    
    
        -- Adjustment Out 
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, adjustment_out)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'adjustment_out', start_date, end_date)T;
    
    
        -- Production IN
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, production_in)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'production_in', start_date, end_date)T;
    
    
        -- Production Out 
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, production_out)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'prodution_out', start_date, end_date)T;
        
    
        -- Transit IN
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, transit_in)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'transit_in', start_date, end_date)T;
    
        -- Transit Out 
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, transit_out)
        select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
        from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'transit_out', start_date, end_date)T;
    
        
        RETURN QUERY 
        Select Tr_data.*,  
            Tr_data.opening_stock - Tr_data.sales + Tr_data.sales_return + Tr_data.purchase - Tr_data.purchase_return
            + Tr_data.internal_in - Tr_data.internal_out + Tr_data.adjustment_in - Tr_data.adjustment_out 
            + Tr_data.production_in - Tr_data.production_out + Tr_data.transit_in - Tr_data.transit_out as closing
        From 
        (
            Select 
                T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name,
                sum(T.opening_stock) as opening_stock,
                sum(T.sales) as sales,
                sum(T.sales_return) as sales_return,
                sum(T.purchase) as purchase,
                sum(T.purchase_return) as purchase_return,
                sum(T.internal_in) as internal_in,
                sum(T.internal_out) as internal_out,
                sum(T.adjustment_in) as adjustment_in,
                sum(T.adjustment_out) as adjustment_out,
                sum(T.production_in) as production_in,
                sum(T.production_out) as production_out,
                sum(T.transit_in) as transit_in,
                sum(T.transit_out) as transit_out
            From
                transaction_table T
            group by 
                T.company_id, T.company_name, T.product_id, T.product_name,
                T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name
        )Tr_data;
       
    END; $BODY$
      LANGUAGE plpgsql VOLATILE
      COST 100
      ROWS 1000;
    """
    cr.execute(query)

def create_opening_stock_sp(cr):
    query="""
        -- DROP FUNCTION public.get_products_opening_stock(integer[], integer[], integer[], integer[], date, date);
        
        CREATE OR REPLACE FUNCTION public.get_products_opening_stock(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN tr_start_date date,
            IN tr_end_date date)
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, opening_stock numeric) AS
        $BODY$
        BEGIN
            RETURN QUERY
            Select 
                cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name, sum(product_qty) as op_stock
            From
            (
                select 
                    T.company_id as cmp_id, T.company_name as cmp_name, 
                    T.product_id as p_id, T.product_name as prod_name, 
                    T.product_category_id as categ_id, T.category_name as cat_name, 
                    T.warehouse_id as wh_id, T.warehouse_name as ware_name,  
                    (product_qty * -1) as product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales' ,tr_start_date, tr_end_date) T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    (product_qty * -1) as product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'purchase_return' ,tr_start_date, tr_end_date) T
        
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    (product_qty * -1) as product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'production_out' ,tr_start_date, tr_end_date)T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    (product_qty * -1) as product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'internal_out' ,tr_start_date, tr_end_date) T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    (product_qty * -1) as product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'adjustment_out' ,tr_start_date, tr_end_date) T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    (product_qty * -1) as product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'transit_out' ,tr_start_date, tr_end_date) T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'purchase' ,tr_start_date, tr_end_date) T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sale_return' ,tr_start_date, tr_end_date) T
                
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'transit_in' ,tr_start_date, tr_end_date) T
        
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'adjustment_in' ,tr_start_date, tr_end_date) T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'production_in' ,tr_start_date, tr_end_date) T
        
                Union All
        
                select 
                    T.company_id as cmp_id, T.company_name, 
                    T.product_id as p_id, T.product_name, 
                    T.product_category_id as categ_id, T.category_name, 
                    T.warehouse_id as wh_id, T.warehouse_name, 
                    product_qty
                from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'internal_in' ,tr_start_date, tr_end_date) T		
        
            )T
            group by cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name;   
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_get_inventory_turnover_ratio_data_sp(cr):
    query = """
        -- DROP FUNCTION public.get_inventory_turnover_ratio_data(integer[], integer[], integer[], integer[], date, date);
        
        CREATE OR REPLACE FUNCTION public.get_inventory_turnover_ratio_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date
        )
        RETURNS TABLE(
            company_id integer, company_name character varying, 
            product_id integer, product_name character varying, 
            product_category_id integer, category_name character varying, 
            warehouse_id integer, warehouse_name character varying, 
            opening_stock numeric, closing_stock numeric, 
            average_stock numeric, sales numeric,
            turnover_ratio numeric
        ) AS
        $BODY$
        BEGIN
            Return Query
            Select
                t_data.*, 
                case when t_data.average_stock = 0.0 then 1 else
                    round(t_data.sales / t_data.average_stock, 2) 
                end as turnover_ratio  
            From
            (
                Select 
                    T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, 
                    T.warehouse_id, T.warehouse_name, T.opening_stock, T.closing, coalesce(Round((T.opening_stock + T.closing) / 2.0, 2)) as average_stock,
                    (T.sales - T.sales_return + T.production_out) as sales
                from get_products_stock_movements(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date) T
            )t_data; 
        
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_get_inventory_fsn_analysis_report_data_sp(cr):
    query = """
        -- DROP FUNCTION public.get_inventory_fsn_analysis_report(integer[], integer[], integer[], integer[], date, date, text);
        
        CREATE OR REPLACE FUNCTION public.get_inventory_fsn_analysis_report(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date,
            IN stock_movement_type text
        )
        RETURNS TABLE(
            company_id integer, company_name character varying, 
            product_id integer, product_name character varying, 
            product_category_id integer, category_name character varying, 
            warehouse_id integer, warehouse_name character varying, 
            opening_stock numeric, closing_stock numeric, 
            average_stock numeric, sales numeric,
            turnover_ratio numeric, stock_movement text
        ) AS
        $BODY$
        BEGIN
            Return Query
            Select * From 
            (
                Select 
                    t_data.*, 
                    case 
                        when t_data.turnover_ratio > 3 then 'Fast Moving'
                        when t_data.turnover_ratio >= 1 and t_data.turnover_ratio <= 3 then 'Slow Moving'
                        when t_data.turnover_ratio < 1 then 'Non Moving'
                    end as stock_movement
                From
                (
                    Select 
                        *
                    from get_inventory_turnover_ratio_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date) T
                )t_data
            )report_data
            where 
            1 = case when stock_movement_type = 'all' then 1 
            else
                case when stock_movement_type = 'fast' then 
                    case when report_data.stock_movement = 'Fast Moving' then 1 else 0 end
                else 
                    case when stock_movement_type = 'slow' then 
                        case when report_data.stock_movement = 'Slow Moving' then 1 else 0 end
                    else 
                        case when stock_movement_type = 'non' then 
                            case when report_data.stock_movement = 'Non Moving' then 1 else 0 end
                        else 0 end
        
                    end
                end
            end; 
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_get_xyz_analysis_data_sp(cr):
    query = """
        -- DROP FUNCTION public.get_inventory_xyz_analysis_data(integer[], integer[], integer[], text);
        CREATE OR REPLACE FUNCTION public.get_inventory_xyz_analysis_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN inventory_analysis_type text)
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, current_stock numeric, stock_value numeric, stock_value_per numeric, cum_stock_value_per numeric, analysis_category text) AS
        $BODY$
                BEGIN
                    Return Query
                    
                    with all_data as (
                        Select 
                            layer.company_id,
                            cmp.name as company_name,
                            layer.product_id,
                            coalesce(prod.default_code, tmpl.name) as product_name,
                            tmpl.categ_id as product_category_id,
                            cat.name as category_name,
                            sum(remaining_qty) as current_stock,
                            sum(remaining_value) as stock_value
                        from 
                            stock_valuation_layer layer
                                Inner Join res_company cmp on cmp.id = layer.company_id
                                Inner Join product_product prod on prod.id = layer.product_id
                                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                                Inner Join product_category cat on cat.id = tmpl.categ_id
                        Where prod.active = True and tmpl.active = True and tmpl.type = 'product' and remaining_qty > 0
                            --company dynamic condition
                            and 1 = case when array_length(company_ids,1) >= 1 then 
                                case when layer.company_id = ANY(company_ids) then 1 else 0 end
                                else 1 end
                            --product dynamic condition
                            and 1 = case when array_length(product_ids,1) >= 1 then 
                                case when layer.product_id = ANY(product_ids) then 1 else 0 end
                                else 1 end
                            --category dynamic condition
                            and 1 = case when array_length(category_ids,1) >= 1 then 
                                case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                                else 1 end
                       group by layer.company_id, cmp.name, layer.product_id, coalesce(prod.default_code, tmpl.name), tmpl.categ_id, cat.name
                    ),
                    warehouse_wise_xyz_analysis as(
                        Select a.company_id, a.company_name, sum(a.current_stock) as total_current_stock, sum(a.stock_value) as total_stock_value
                        from all_data a
                        group by a.company_id, a.company_name
                    )
                    Select final_data.* from 
                    (
                        Select 
                            result.*,
                            case 
                                when result.cum_stock_value_per < 70 then 'X' 
                                when result.cum_stock_value_per >= 70 and result.cum_stock_value_per <= 90 then 'Y'
                                when result.cum_stock_value_per > 90 then 'Z'
                            end as analysis_category 
                        from
                        (
                            Select 
                                *, 
                                sum(cum_data.warehouse_stock_value_per) 
                    over (partition by cum_data.company_id order by cum_data.company_id, cum_data.warehouse_stock_value_per desc rows between unbounded preceding and current row) as cum_stock_value_per
                            from 
                            (
                                Select 
                                    all_data.*, 
                                    case when wwxyz.total_stock_value <= 0.00 then 0 else 
                                        Round((all_data.stock_value / wwxyz.total_stock_value * 100.0)::numeric,2) 
                                    end as warehouse_stock_value_per
                                from all_data
                                    Inner Join warehouse_wise_xyz_analysis wwxyz on all_data.company_id = wwxyz.company_id
                                order by warehouse_stock_value_per desc
                            )cum_data
                        )result
                    )final_data
                    where 
                    1 = case when inventory_analysis_type = 'all' then 1 
                    else
                        case when inventory_analysis_type = 'high_stock' then 
                            case when final_data.analysis_category = 'X' then 1 else 0 end
                        else 
                            case when inventory_analysis_type = 'medium_stock' then 
                                case when final_data.analysis_category = 'Y' then 1 else 0 end
                            else 
                                case when inventory_analysis_type = 'low_stock' then 
                                    case when final_data.analysis_category = 'Z' then 1 else 0 end
                                else 0 end
                
                            end
                        end
                    end;
                    
                END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_get_fsn_xyz_analysis_data_sp(cr):
    query = """
        -- DROP FUNCTION public.get_inventory_fsn_xyz_analysis_report(integer[], integer[], integer[], integer[], date, date, text, text);

        CREATE OR REPLACE FUNCTION public.get_inventory_fsn_xyz_analysis_report(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date,
            IN stock_movement_type text,
            IN stock_value_type text)
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, average_stock numeric, sales numeric, turnover_ratio numeric, fsn_classification text, current_stock numeric, stock_value numeric, xyz_classification text, combine_classification text) AS
        $BODY$
                BEGIN
                    Return Query
                    Select 
                        xyz.company_id, xyz.company_name, xyz.product_id, xyz.product_name, xyz.product_category_id, xyz.category_name,
                        fsn.average_stock, fsn.sales, fsn.turnover_ratio, fsn.stock_movement as fsn_classification,
                        xyz.current_stock, xyz.stock_value, xyz.analysis_category as xyz_classification,
                        ((case 
                            when fsn.stock_movement = 'Fast Moving' then 'F'
                            when fsn.stock_movement = 'Slow Moving' then 'S'
                            when fsn.stock_movement = 'Non Moving' then 'N'
                        end) ||  xyz.analysis_category)::text as combine_classification
                         
                    from 
                    (
                        Select T1.* 
                        From get_inventory_xyz_analysis_data(company_ids, product_ids, category_ids, stock_value_type) T1 
                    ) xyz
                        Inner Join 
                    (
                        Select T.*
                        From 
                        get_inventory_fsn_analysis_report(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, stock_movement_type) T
                    ) fsn
                        on xyz.product_id = fsn.product_id and xyz.company_id = fsn.company_id
                    order by xyz.stock_value desc;
                END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_get_products_outofstock_data_sp(cr):
    query="""-- Function: public.get_products_outofstock_data(integer[], integer[], integer[], integer[], date, date, integer)
            
            -- DROP FUNCTION public.get_products_outofstock_data(integer[], integer[], integer[], integer[], date, date, integer);
            
            CREATE OR REPLACE FUNCTION public.get_products_outofstock_data(
                IN company_ids integer[],
                IN product_ids integer[],
                IN category_ids integer[],
                IN warehouse_ids integer[],
                IN start_date date,
                IN end_date date,
                IN advance_stock_days integer)
              RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, qty_available numeric, outgoing numeric, incoming numeric, forecasted_stock numeric, sales numeric, ads numeric, demanded_qty numeric, in_stock_days numeric, out_of_stock_days numeric, cost_price numeric, out_of_stock_ratio numeric, out_of_stock_qty numeric, out_of_stock_value numeric, out_of_stock_qty_per numeric, out_of_stock_value_per numeric, turnover_ratio numeric, stock_movement text) AS
            $BODY$
                    BEGIN
                        Drop Table if exists outofstock_transaction_table;
                        CREATE TEMPORARY TABLE outofstock_transaction_table(
                            company_id INT,
                            company_name character varying,
                            product_id INT,
                            product_name character varying,
                            product_category_id INT,
                            category_name character varying, 
                            warehouse_id INT,
                            warehouse_name character varying, 
                            qty_available Numeric DEFAULT 0,
                            outgoing numeric DEFAULT 0,
                            incoming Numeric DEFAULT 0,
                            forecasted_stock Numeric DEFAULT 0,
                            sales numeric DEFAULT 0,
                            ads numeric DEFAULT 0,
                            demanded_qty numeric, 
                            in_stock_days numeric, 
                            out_of_stock_days numeric, 
                            cost_price numeric,
                            out_of_stock_ratio numeric, 
                            out_of_stock_qty numeric,																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																
                            out_of_stock_value numeric
                        );
                    
                        Insert into outofstock_transaction_table
                        Select stockout_data.*,  
                            round((stockout_data.out_of_stock_days / advance_stock_days * 100)::numeric, 0) as out_of_stock_ratio,
                            round(stockout_data.out_of_stock_days * stockout_data.ads,0) as out_of_stock_qty,
                            stockout_data.out_of_stock_days * stockout_data.ads * stockout_data.cost_price as out_of_stock_value
                        from 
                        (
                            Select 
                                final_data.*,
                                case when (advance_stock_days - final_data.in_stock_days) > 0 then (advance_stock_days - final_data.in_stock_days) 
                                else 0 end as out_of_stock_days,
                                coalesce(ir_property.value_float,0) as cost_price
                            From
                            (
                                Select 
                                    stock_data.* , coalesce(round(sales_data.sales,0),0) as sales, coalesce(sales_data.ads,0) as ads, 
                                    Round(coalesce(advance_stock_days * sales_data.ads,0),0) as demanded_qty, 
                        case when 
                            coalesce(Round((stock_data.forecasted_stock / case when sales_data.ads <= 0.0000 then 0.001 else sales_data.ads end)::numeric, 0),0) < 0 then 0 
                                    else 
                            coalesce(Round((stock_data.forecasted_stock / case when sales_data.ads <= 0.0000 then 0.001 else sales_data.ads end)::numeric, 0),0)
                        end as in_stock_days
                                From
                                (
                                    Select  
                            T.company_id, T.company_name, T.product_id , T.product_name , T.product_category_id, T.category_name , 
                            T.warehouse_id, T.warehouse_name, T.qty_available, T.outgoing, T.incoming, 
                            case when T.forecasted_stock > 0 then T.forecasted_stock else 0 end as forecasted_stock
                                    from get_products_forecasted_stock_data(company_ids, product_ids, category_ids, warehouse_ids)T
                                )stock_data
                    
                                Left Join
                                (
                                    select *, Round(D1.sales / ((end_date - start_date) + 1),2) as ads 
                                    from get_sales_transaction_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date) D1
                                )sales_data
                                    on stock_data.product_id = sales_data.product_id and stock_data.warehouse_id = sales_data.warehouse_id 
                            )final_data
                                Left Join ir_property on 'product.product,' || final_data.product_id = ir_property.res_id
                                                and ir_property.name = 'standard_price' and ir_property.company_id = final_data.company_id
                        )stockout_data;
                            
                        Return Query
                        with all_data as (
                            Select * from outofstock_transaction_table
                        ),
                        warehouse_wise_outofstock as(
                            Select ott.warehouse_id, ott.company_id, 
                                sum(ott.out_of_stock_qty) as total_stockout_qty, sum(ott.out_of_stock_value) as total_stockout_value
                            from outofstock_transaction_table ott
                            group by ott.warehouse_id, ott.company_id
                        ),
                        fsn_analysis as(
                            Select * 
                            from get_inventory_fsn_analysis_report(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, 'all') f_data
                        )
                        Select 
                            all_data.*, 
                            case when wwover.total_stockout_qty <= 0.00 then 0 else 
                                Round((all_data.out_of_stock_qty / wwover.total_stockout_qty * 100)::numeric,2) 
                            end as warehouse_stockout_qty ,
                            case when wwover.total_stockout_value <= 0.00 then 0 else
                                Round((all_data.out_of_stock_value / wwover.total_stockout_value * 100)::numeric,2) 
                            end as warehouse_stockout_value,
                            case when fsn.turnover_ratio > 0 then fsn.turnover_ratio else 0 end as turnover_ratio,
                            fsn.stock_movement
                        from all_data
                            Inner Join warehouse_wise_outofstock wwover on wwover.warehouse_id = all_data.warehouse_id
                            Left Join fsn_analysis fsn on fsn.product_id = all_data.product_id and fsn.warehouse_id = all_data.warehouse_id;
                    END; $BODY$
              LANGUAGE plpgsql VOLATILE
              COST 100
              ROWS 1000;

    """
    cr.execute(query)

def create_get_stock_age_data_sp(cr):
    query = """
                
        -- DROP FUNCTION public.inventory_stock_age_report(integer[], integer[], integer[]);
        CREATE OR REPLACE FUNCTION public.inventory_stock_age_report(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[])
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, current_stock numeric, current_stock_value numeric, oldest_date date, days_old integer, oldest_stock_qty numeric, oldest_stock_value numeric, stock_qty_ratio numeric, stock_value_ratio numeric) AS
        $BODY$
                BEGIN
                Drop Table if exists stock_age_table;
                CREATE TEMPORARY TABLE stock_age_table(
                    row_id INT,
                    company_id INT,
                    company_name character varying,
                    in_date date,
                    product_id INT,
                    product_name character varying,
                    product_category_id INT,
                    category_name character varying, 
                    current_stock numeric DEFAULT 0, 
                    current_stock_value numeric DEFAULT 0
                );
                Insert into stock_age_table
                Select 
                    row_number() over(partition by layer.company_id, layer.product_id order by layer.company_id, layer.product_id, move.date) row_id,
                    layer.company_id,
                    cmp.name as company_name,
                    move.date, 
                    layer.product_id, 
                    prod.default_code as product_code,
        -- 			tmpl.name,
                    tmpl.categ_id as category_id,
                    cat.complete_name as category_name,
                    sum(layer.remaining_qty) stock_qty,
                    sum(layer.remaining_value) stock_value
                from 
                    stock_valuation_layer layer
                        Inner Join stock_move move on move.id = layer.stock_move_id
                        Inner Join product_product prod on prod.id = layer.product_id
                        Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                        Inner Join product_category cat on cat.id = tmpl.categ_id
                        Inner Join res_company cmp on cmp.id = layer.company_id
                Where remaining_qty > 0 and prod.active = True and tmpl.active = True and 
                1 = case when array_length(product_ids,1) >= 1 then 
                    case when layer.product_id = ANY(product_ids) then 1 else 0 end
                    else 1 end
                and 1 = case when array_length(category_ids,1) >= 1 then 
                    case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                    else 1 end
                and 1 = case when array_length(company_ids,1) >= 1 then 
                    case when layer.company_id = ANY(company_ids) then 1 else 0 end
                    else 1 end
                group by layer.company_id, cmp.name, move.date, layer.product_id, prod.default_code, tmpl.name, tmpl.categ_id, cat.complete_name;
        
                Return Query
                with all_data as (
                    Select st.company_id, st.company_name, st.product_id, st.product_name, st.product_category_id, st.category_name, 
                        sum(st.current_stock) as total_stock, sum(st.current_stock_value) as total_stock_value
                    from stock_age_table st
                    group by st.company_id, st.company_name, st.product_id, st.product_name, st.product_category_id, st.category_name
                ),
                company_wise_stock_age_table as(
                    Select sat.company_id, sum(sat.current_stock) as total_stock_qty, sum(sat.current_stock_value) as total_stock_value
                    from stock_age_table sat
                    group by sat.company_id
                ),
                oldest_stock_data as (
                    Select st.company_id, st.product_id, st.in_date, st.current_stock, st.current_stock_value,	
                        (now()::date - st.in_date) days_old
                    from stock_age_table st
                    where row_id = 1
                )
        
                Select 
                    all_data.*, oldest.in_date, oldest.days_old, oldest.current_stock, oldest.current_stock_value,
                    case when cmp_age.total_stock_qty <= 0.00 then 0 else 
                        Round(all_data.total_stock / cmp_age.total_stock_qty * 100,3)
                    end as stock_qty_ratio,
                    case when cmp_age.total_stock_value <= 0.00 then 0 else 
                        Round(all_data.total_stock_value / cmp_age.total_stock_value * 100,4)
                    end as stock_value_ratio
                From
                    all_data
                        Inner Join oldest_stock_data oldest on oldest.company_id = all_data.company_id and all_data.product_id = oldest.product_id
                        Inner Join company_wise_stock_age_table cmp_age on cmp_age.company_id = all_data.company_id;
            END; 
        $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def create_get_stock_age_breakdown_data_sp(cr):
    query = """
        -- DROP FUNCTION get_inventory_age_breakdown_data(integer[],integer[],integer[],integer) 
        
        CREATE OR REPLACE FUNCTION public.get_inventory_age_breakdown_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN breakdown_days integer
        )
        RETURNS TABLE(
            company_id integer, company_name character varying, product_id integer, product_name character varying, 
            product_category_id integer, category_name character varying, total_stock numeric, total_stock_value numeric,
            breakdown1_qty numeric, breckdown1_value numeric,
            breakdown2_qty numeric, breckdown2_value numeric, breakdown3_qty numeric, breckdown3_value numeric,
            breakdown4_qty numeric, breckdown4_value numeric, breakdown5_qty numeric, breckdown5_value numeric,
            breakdown6_qty numeric, breckdown6_value numeric, breakdown7_qty numeric, breckdown7_value numeric
        ) as
        $BODY$
            BEGIN	
                Return Query
                Select 
                    GD.company_id, GD.company_name, GD.product_id, GD.product_code, GD.category_id, GD.category_name,
                    sum(stock_qty) as "total_stock", sum(stock_value) as "total_stock_value",
                    sum(GD.breakdown1_qty) as "breakdown1_qty", sum(GD.breakdown1_value) as "breakdown1_value",
                    sum(GD.breakdown2_qty) as "breakdown2_qty", sum(GD.breakdown2_value) as "breakdown2_value",
                    sum(GD.breakdown3_qty) as "breakdown3_qty", sum(GD.breakdown3_value) as "breakdown3_value",
                    sum(GD.breakdown4_qty) as "breakdown4_qty", sum(GD.breakdown4_value) as "breakdown4_value",
                    sum(GD.breakdown5_qty) as "breakdown5_qty", sum(GD.breakdown5_value) as "breakdown5_value",
                    sum(GD.breakdown6_qty) as "breakdown6_qty", sum(GD.breakdown6_value) as "breakdown6_value",
                    sum(GD.breakdown7_qty) as "breakdown7_qty", sum(GD.breakdown7_value) as "breakdown7_value"
                From (
                Select 
                    T.company_id,
                    T.company_name,
                    T.product_id,
                    T.product_code,
                    T.category_id,
                    T.category_name,
                    stock_qty, 
                    stock_value,
                    case when stock_age <= breakdown_days then stock_qty else 0 end as "breakdown1_qty",
                    case when stock_age <= breakdown_days then stock_value else 0 end as "breakdown1_value", 
                    
                    case when stock_age > breakdown_days and stock_age <= (breakdown_days * 2) then stock_qty else 0 end as "breakdown2_qty",
                    case when stock_age > breakdown_days and stock_age <= (breakdown_days * 2) then stock_value else 0 end as "breakdown2_value",
                    
                    case when stock_age > (breakdown_days * 2) and stock_age <= (breakdown_days * 3) then stock_qty else 0 end as "breakdown3_qty",
                    case when stock_age > (breakdown_days * 2) and stock_age <= (breakdown_days * 3) then stock_value else 0 end as "breakdown3_value",
                    
                    case when stock_age > (breakdown_days * 3) and stock_age <= (breakdown_days * 4) then stock_qty else 0 end as "breakdown4_qty",
                    case when stock_age > (breakdown_days * 3) and stock_age <= (breakdown_days * 4) then stock_value else 0 end as "breakdown4_value",
                    
                    case when stock_age > (breakdown_days * 4) and stock_age <= (breakdown_days * 5) then stock_qty else 0 end as "breakdown5_qty",
                    case when stock_age > (breakdown_days * 4) and stock_age <= (breakdown_days * 5) then stock_value else 0 end as "breakdown5_value",
                    
                    case when stock_age > (breakdown_days * 5) and stock_age <= (breakdown_days * 6) then stock_qty else 0 end as "breakdown6_qty",
                    case when stock_age > (breakdown_days * 5) and stock_age <= (breakdown_days * 6) then stock_value else 0 end as "breakdown6_value",
                    
                    case when stock_age > (breakdown_days * 6) then stock_qty else 0 end as "breakdown7_qty",
                    case when stock_age > (breakdown_days * 6) then stock_value else 0 end as "breakdown7_value"
                    
                from 
                (
                    Select 
                        row_number() over(partition by layer.company_id, layer.product_id order by layer.company_id, layer.product_id, move.date) row_id,
                        layer.company_id,
                        cmp.name as company_name,
                        (now()::date - move.date::date) stock_age, 
                        layer.product_id, 
                        prod.default_code as product_code,
                        tmpl.categ_id as category_id,
                        cat.complete_name as category_name,
                        sum(layer.remaining_qty) stock_qty,
                        sum(layer.remaining_value) stock_value
                    from 
                        stock_valuation_layer layer
                            Inner Join stock_move move on move.id = layer.stock_move_id
                            Inner Join product_product prod on prod.id = layer.product_id
                            Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                            Inner Join product_category cat on cat.id = tmpl.categ_id
                            Inner Join res_company cmp on cmp.id = layer.company_id
                    Where remaining_qty > 0 and prod.active = True and tmpl.active = True and --and layer.product_id = 284
                    1 = case when array_length(product_ids,1) >= 1 then 
                        case when layer.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    and 1 = case when array_length(category_ids,1) >= 1 then 
                        case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                    and 1 = case when array_length(company_ids,1) >= 1 then 
                        case when layer.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    group by layer.company_id, cmp.name, move.date, layer.product_id, prod.default_code, tmpl.name, tmpl.categ_id, cat.complete_name
                )T
                )GD
                Group by GD.company_id, GD.company_name, GD.product_id, GD.product_code, GD.category_id, GD.category_name;
            END;
        $BODY$	
        LANGUAGE plpgsql VOLATILE
        COST 100
        ROWS 1000;
    """
    cr.execute(query)
