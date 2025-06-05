update res_partner set electronic_invoice_subjected=True,pec_destinatario=pec_mail,codice_destinatario=ipa_code where vat is not null ;
update res_partner set is_pa=True where char_length(ipa_code)=6;
select electronic_invoice_subjected,vat,ipa_code,pec_mail,pec_destinatario,codice_destinatario,is_pa from res_partner where vat is not null ;
