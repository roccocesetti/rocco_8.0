<html>
<head>
    <style type="text/css">
        ${css}
    </style>
</head>
<body>
    <% Finizio=True %>
    <% num_dist=0 %>
    %for dist in objects :
	<% num_dist +=1%>
    <% Totale=0 %>
    <% totsca=0 %>
    <% due_date=None %>
    <% setLang(dist.company_id.partner_id.lang) %>
    <table class="list_table"  width="100%">
    <% counter = 29 %>
     %for line in  get_line_eff(dist.line_ids) :
    		%if not due_date:
    			   <% due_date=line[1].due_date%>	
    		%endif
    		%if not line[1].bank_id.bank.name:
    				<% line[1].bank_id.bank.name='--' %>
    		%endif
    		%if not line[1].bank_id.bank.x_abi:
    				<% line[1].bank_id.bank.x_abi='--' %>
    		%endif
    		%if not line[1].bank_id.bank.x_cab:
    				<% line[1].bank_id.bank.x_cab='--' %>
    		%endif
    		<%righe_nome=get_righe('['+str(line[1].bank_id.bank.x_abi)+'/'+str(line[1].bank_id.bank.x_cab)+']'+str(line[1].bank_id.bank.name)) %>
   			<%righe_eff=get_numeff(line[1].invoice_number) %>
   			<%righe_dat_fat=get_data_fatt(line[1].invoice_date) %>
	   			%if len(righe_nome)>len(righe_eff) and len(righe_nome)>len(righe_dat_fat):
	   				<%counter +=len(righe_nome) %>
				%elif len(righe_eff)>len(righe_nome) and len(righe_eff)>len(righe_dat_fat):
	   				<%counter +=len(righe_eff) %>
				%elif len(righe_dat_fat)>len(righe_nome) and len(righe_dat_fat)>len(righe_eff):
	   				<%counter +=len(righe_dat_fat) %>
				%else:
	   				<%counter +=len(righe_nome) %>				
				%endif
			%if  due_date!=line[1].due_date:
	   			   <%counter +=1 %>
			%endif
			%if counter>28:
	   			%if len(righe_nome)>len(righe_eff) and len(righe_nome)>len(righe_dat_fat):
	   				<%counter =len(righe_nome) %>
				%elif len(righe_eff)>len(righe_nome) and len(righe_eff)>len(righe_dat_fat):
	   				<%counter =len(righe_eff) %>
				%elif len(righe_dat_fat)>len(righe_nome) and len(righe_dat_fat)>len(righe_eff):
	   				<%counter =len(righe_dat_fat) %>
				%else:
	   				<%counter =len(righe_nome) %>				
				%endif
			%if  due_date!=line[1].due_date:
	   			   <%counter +=1 %>
			%endif

   				%if Finizio==False:
   					<p style="page-break-after:always"></p>
   					<br />
   				%endif
        			 <thead  style="text-align:left;margin-left:0%;">
        			
        			<tr>
 <!-- testata inizio-->
 				<% Finizio=False %>
					    <table class="basic_table" width="100%">
					        <tr>

						<td >

					     <table class="dest_address" style="margin-left:0%;border-style:none" >

					        <tr><td style="border-style:none"><b>Richiedente:${dist.company_id.partner_id.title or ''|entity}  ${dist.company_id.partner_id.name |entity}</b></td></tr>
					        <tr><td style="border-style:none">${dist.company_id.partner_id.street or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.company_id.partner_id.street2 or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.company_id.partner_id.zip or ''|entity} ${dist.company_id.partner_id.city or ''|entity} ${dist.company_id.partner_id.province.code or ''|entity}</td></tr>
					        %if dist.company_id.partner_id.country_id :
					        <tr><td style="border-style:none">${dist.company_id.partner_id.country_id.name or ''|entity} </td></tr>
					        %endif
					        %if dist.company_id.partner_id.phone :
					        <tr><td style="border-style:none">${_("Tel")}: ${dist.company_id.partner_id.phone|entity}</td></tr>
					        %endif
					        %if dist.company_id.partner_id.fax :
					        <tr><td style="border-style:none">${_("Fax")}: ${dist.company_id.partner_id.fax|entity}</td></tr>
					        %endif
					        <!--
					        %if dist.company_id.partner_id.email :
					        <tr><td style="border-style:none">${_("E-mail")}: ${dist.company_id.partner_id.email|entity}</td></tr>
					        %endif
					        -->
					        %if dist.company_id.partner_id.vat :
					        <tr><td style="border-style:none">${_("P.iva")}: ${dist.company_id.partner_id.vat|entity}</td></tr>
					        %endif
					    	
					    </table>
					   </td> 
					   <td >

					     <table class="dest_address" style="margin-left:0%;border-style:none" >

					        <tr><td style="vertical-align:text-top;border-style:none" ><b>Banca di Presentazione: ${dist.config.bank_id.bank.name or ''|entity} </b></td></tr>
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.street or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.street2 or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.zip or ''|entity} ${dist.config.bank_id.bank.city or ''|entity} ${dist.config.bank_id.bank.state or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.x_abi or ''|entity} ${dist.config.bank_id.bank.x_cab or ''|entity} </td></tr>
					        %if dist.config.bank_id.bank.country :
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.country.name or ''|entity} </td></tr>
					        %endif
					        %if dist.config.bank_id.bank.phone :
					        <tr><td style="border-style:none">${_("Tel")}: ${dist.config.bank_id.bank.phone|entity}</td></tr>
					        %endif
					        %if dist.config.bank_id.bank.fax:
					        <tr><td style="border-style:none">${_("Fax")}: ${dist.config.bank_id.bank.fax|entity}</td></tr>
					        %endif
					        <!--
					        %if dist.config.bank_id.bank.email :
					        <tr><td style="border-style:none">${_("E-mail")}: ${dist.config.bank_id.bank.email|entity}</td></tr>
					        %endif
					        -->
					    </table>
					   </td> 
         			  </tr>
        			 </table>					   

						    <br />
							    	<span class="title">${_("Distinta Effetti")} ${dist.name or ''|entity}  ${_("Del")} ${dist.date_created or ''|entity}</span>

 
 
 <!-- testata fine  -->       			
        			
        			
        			</tr>
        			<tr>
						<td>
	        				<table class="list_table"  width="100%">
											<thead>
	        				       			<tr>
						        				<th  width="5%"  style="text-align:left">${_("Prog.")}</th>	 
						        				<th  width="10%"  style="text-align:left">${_("Numero fattura")}</th>	 
						        				<th  width="10%"  style="text-align:center">${_("Data Fattura")}</th>
						        				<th  width="10%"  style="text-align:center">${_("Data Scadenza")}</th>
						        				<th  width="20%" style="text-align:center;font-size:8;">${_("Cliente")}</th>
						        				<th  width="10%" style="text-align:right;font-size:9;">${_("Importo")}</th>
						        				<th  width="10%" style="text-align:right;font-size:9;">${_("Prog.Scadenza")}</th>
						        				<th  width="25%" style="text-align:center;font-size:8" >${_("Banca Appoggio")}</th>
											</tr>
	        								</thead>
	        				</table>
	        			</td>		
        			</tr>
        				<br />
        			
        			</thead>
   			%endif
 
        <tbody>
						%if  due_date!=line[1].due_date:
							<tr>
							<td>
					        	<table class="list_table"  width="100%">
									<tbody>
								            	<td width="5%" style="border-top:2px solid""/>
								            	<td width="10%" style="border-top:2px solid"/>
								            	<td width="10%" style="border-top:2px solid"/>
								            	<td width="10%" style="border-top:2px solid"/>
								            	<td width="20%" style="text-align:right;border-top:2px solid">Totale Scadenza </tb>
								            	<td width="10%" style="text-align:right;border-top:2px solid">${formatLang(totsca) }</td>
								            	<td width="10%" style="text-align:right;border-top:2px solid">${formatLang(Totale) }</td>
								            	<td width="25%" style="text-align:right;border-top:2px solid" />
					        		
					        		</tbody>
					        	</table>
							</td>
				
					    	</tr>
						<%totsca=0 %>
						<%due_date=line[1].due_date %>
						%endif	        		
  
        <tr>
			<td>
	        	<table class="list_table"  width="100%">
					<tbody>
	        			<tr>
					    	<% Totale+=line[1].amount %>
					    	<% totsca+=line[1].amount %>
				        	<td width="5%" style="text-align:left;font-size:9;vertical-align:text-top;">${ line[1].sequence|entity} /${ counter}</td>
				        	<td width="10%" style="text-align:left;font-size:9;vertical-align:text-top;">${ line[1].invoice_number|entity}</td>
				        	<td width="10%" style="text-align:center;font-size:9;vertical-align:text-top;">${ get_data(str(line[1].invoice_date))|entity}</td>
				        	<td width="10%" style="text-align:center;font-size:9;vertical-align:text-top;">${ get_data(str(line[1].due_date))|entity}</td>
				        	<td width="20%" style="text-align:right;vertical-align:text-top;font-size:8">${line[1].partner_id.name}  </td>
				        	<td width="10%" style="text-align:right;vertical-align:text-top;">${formatLang(line[1].amount,digits=2)}  </td>
				        	<td width="10%" style="text-align:right;vertical-align:text-top;">${formatLang(Totale,digits=2)}  </td>
				        	<td colspan=2 width="25%" style="vertical-align:text-top;text-align:center">
				        			        	<table class="list_table"  width="100%">
					        						%for riga in righe_nome:
					        						<tr>
						        						<td style="font-size:8;vertical-align:text-top;text-align:center">
						        							${riga or '---' |entity}
						        						</td>
					        						</tr>
					        						%endfor
				        						</table>	
				        	</td>
	        			</tr>
	        		</tbody>
	        	</table>
			</td>
        </tr>
        %endfor

        </tbody>
    </table>
    <table class="list_table" width="100%">
   			%if counter>33:
   				%if Finizio==False:
   			    	<p style="page-break-after:always"></p> 
   					<br />
   				%endif
   				<%counter =1%>
        			<thead>
        			<tr>
 <!-- testata inizio-->
 				<% Finizio=False %>
					    <table class="basic_table" width="100%">
					        <tr>

						<td >

					     <table class="dest_address" style="margin-left:0%;border-style:none" >

					        <tr><td style="border-style:none"><b>Richiedente:${dist.company_id.partner_id.title or ''|entity}  ${dist.company_id.partner_id.name |entity}</b></td></tr>
					        <tr><td style="border-style:none">${dist.company_id.partner_id.street or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.company_id.partner_id.street2 or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.company_id.partner_id.zip or ''|entity} ${dist.company_idpartner_id.city or ''|entity} ${dist.company_id.partner_id.province.code or ''|entity}</td></tr>
					        %if dist.company_id.partner_id.country_id :
					        <tr><td style="border-style:none">${dist.company_id.partner_id.country_id.name or ''|entity} </td></tr>
					        %endif
					        %if dist.company_id.partner_id.phone :
					        <tr><td style="border-style:none">${_("Tel")}: ${dist.company_id.partner_id.phone|entity}</td></tr>
					        %endif
					        %if dist.company_id.partner_id.fax :
					        <tr><td style="border-style:none">${_("Fax")}: ${dist.company_id.partner_id.fax|entity}</td></tr>
					        %endif
					        <!--
					        %if dist.company_id.partner_id.email :
					        <tr><td style="border-style:none">${_("E-mail")}: ${dist.company_id.partner_id.email|entity}</td></tr>
					        %endif
					        -->
					        %if dist.company_id.partner_id.vat :
					        <tr><td style="border-style:none">${_("P.iva")}: ${dist.company_id.partner_id.vat|entity}</td></tr>
					        %endif
					    </table>
					   </td> 
					   <td >

					     <table class="dest_address" style="margin-left:0%;border-style:none" >

					        <tr><td style="vertical-align:text-top;border-style:none"><b>Banca di Presentazione: ${dist.config.bank_id.bank.name or ''|entity} </b></td></tr>
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.street or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.street2 or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.zip or ''|entity} ${dist.config.bank_id.bank.city or ''|entity} ${dist.config.bank_id.bank.state or ''|entity}</td></tr>
					        <tr><td style="border-style:none">${dist.config.bank_id.bank.x_abi or ''|entity} ${dist.config.bank_id.bank.x_cab or ''|entity} </td></tr>
					        %if dist.bank_id.bank.country :
					        <tr>
					        <td style="border-style:none">${dist.bank_id.bank.country.name or ''|entity} </td>
					        </tr>
					        %endif
					        %if dist.bank_id.bank.phone :
					        <tr><td style="border-style:none">${_("Tel")}: ${dist.bank_id.bank.phone|entity}</td></tr>
					        %endif
					        %if dist.bank_id.bank.fax :
					        <tr><td style="border-style:none">${_("Fax")}: ${dist.bank_id.bank.fax|entity}</td></tr>
					        %endif
					        <!--
					        %if dist.bank_id.bank.email :
					        <tr><td style="border-style:none">${_("E-mail")}: ${dist.bank_id.bank.email|entity}</td></tr>
					        %endif
					    </table>
					   </td> 
         			  </tr>
        			 </table>					   

						    <br />
							    	<span class="title">${_("Distinta Effetti")} ${dist.name or ''|entity}  ${_("Del")} ${dist.date_created or ''|entity}</span>
 
 <!-- testata fine  -->       			
       			
        			
        			</tr>
        			<tr>
						<td>
	        				<table class="list_table"  width="100%">
											<thead>
	        				       			<tr>
						        				<th  width="5%"  style="text-align:left">${_("Prog.")}</th>	 
						        				<th  width="10%"  style="text-align:left">${_("Numero fattura")}</th>	 
						        				<th  width="10%"  style="text-align:center">${_("Data Fattura")}</th>
						        				<th  width="10%"  style="text-align:center">${_("Data Scadenza")}</th>
						        				<th  width="20%" style="text-align:center;font-size:8;">${_("Cliente")}</th>
						        				<th  width="10%" style="text-align:right;font-size:9;">${_("Importo")}</th>
						        				<th  width="10%" style="text-align:right;font-size:9;">${_("Prog.Scadenza")}</th>
						        				<th  width="25%" style="text-align:center;font-size:8" >${_("Banca Appoggio")}</th>
	        								</tr>
	        								</thead>
	        				</table>
	        			</td>		
        			</tr>
        				<br />
        			
        			</thead>
   			%endif
 



<!--  -->

			<tr>
			<td>
	        	<table class="list_table"  width="100%">
					<tbody>
				            	<td width="5%" style="border-top:2px solid""/>
				            	<td width="10%" style="border-top:2px solid"/>
				            	<td width="10%" style="border-top:2px solid"/>
				            	<td width="10%" style="border-top:2px solid"/>
				            	<td width="20%" style="text-align:right;border-top:2px solid">Totale</tb>
				            	<td width="10%" style="text-align:right;border-top:2px solid">${formatLang(Totale) }</td>
				            	<td width="10%" style="text-align:right;border-top:2px solid">${formatLang(Totale) }</td>
				            	<td width="25%" style="text-align:right;border-top:2px solid" />
	        		</tbody>
	        	</table>
			</td>

	    	</tr>
<!--  -->
    </table>        
    %if num_dist<len(objects):
    <p style="page-break-after:always"></p>
    %endif
    %endfor
</body>
</html>
