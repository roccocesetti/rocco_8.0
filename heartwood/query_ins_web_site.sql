insert into ir_ui_view  

 
  (
  name  , -- View Name
  inherit_id , -- Inherited View
  write_date , -- Last Modification Date
  arch , -- View Architecture
  write_uid , -- Last Updated by
  priority , -- Sequence
  mode , -- View inheritance mode
  active , -- Active
  model , -- Object
  model_data_id , -- Model Data
  type , -- View Type
  field_parent, -- Child Field
  customize_show , -- Show As Optional Inherit
  website_meta_title , -- Website meta title
  website_meta_description , -- Website meta description
  website_meta_keywords , -- Website meta keywords
  page , -- Whether this view is a web page template (complete)
  website_id , -- Website
  key  -- Key
  )

 
(
select  
 name, -- View Name
  inherit_id , -- Inherited View
  write_date , -- Last Modification Date
  arch , -- View Architecture
  write_uid , -- Last Updated by
  priority , -- Sequence
  mode , -- View inheritance mode
  active , -- Active
  model , -- Object
  model_data_id , -- Model Data
  type , -- View Type
  field_parent, -- Child Field
  customize_show , -- Show As Optional Inherit
  website_meta_title , -- Website meta title
  website_meta_description , -- Website meta description
  website_meta_keywords , -- Website meta keywords
  page , -- Whether this view is a web page template (complete)
  3, -- Website
  key  -- Key
 from ir_ui_view where type='qweb' and page=True  order by id
 )