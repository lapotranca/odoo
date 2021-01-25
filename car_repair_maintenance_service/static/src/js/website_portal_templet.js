//odoo13 not used
//odoo.define('car_repair_maintenance_service.website_portal_templet', function(require) {

//$(document).ready(function(){
//    console.log('abcd')
//    $("#service_type").hide();
//    
//    var state_options = $("select[name='srvice_type_id']:enabled option:not(:first)");
//    $("#service_id").change(function myFunction() {
//          var select = $("select[name='srvice_type_id']");
//          state_options.detach();
//          var displayed_state = state_options.filter("[data-service_id="+($(this).val() || 0)+"]");
//          var nb = displayed_state.appendTo(select).show().size();
//          select.parent().toggle(nb>=1);
//          var input = document.getElementById("service_id");
//          var service_id = input.options[input.selectedIndex].value;
//          if (service_id != "")
//          {
//            $("#service_type").show();
//          }
//          else
//          {
//          $("#service_type").hide();
//          }
//          
//        });
//    });
//    $("#service_id").change();

//}); 
