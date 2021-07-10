odoo.define('account_dynamic_reports.DynamicTbMain', function (require) {
'use strict';
var ActionManager = require('web.ActionManager');
var AbstractAction = require('web.AbstractAction');
var Dialog = require('web.Dialog');
var FavoriteMenu = require('web.FavoriteMenu');
var web_client = require('web.web_client');
var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var field_utils = require('web.field_utils');
var rpc = require('web.rpc');
var time = require('web.time');
var session = require('web.session');
var utils = require('web.utils');
var round_di = utils.round_decimals;
var QWeb = core.qweb;
var _t = core._t;
var exports = {};
var DynamicFrMain = AbstractAction.extend({
template:'DynamicFrMain',
events: {
'click #filter_apply_button': 'update_with_filter',
'click #pdf': 'print_pdf',
'click #xlsx': 'print_xlsx',
'click .view-source': 'view_gl',
},
init : function(view, code){
this._super(view, code);
this.wizard_id = code.context.wizard_id | null;
this.account_report_id = code.context.account_report_id | null;
this.session = session;
},
start : function(){
var self = this;
self.initial_render = true;
if(! self.wizard_id){
self._rpc({
model: 'ins.financial.report',
method: 'create',
context: {report_name: this.account_report_id},
args: [{
res_model: this.res_model,
}]
}).then(function (record) {
self.wizard_id = record;
self.plot_data(self.initial_render);
})
}else{
self.plot_data(self.initial_render);
}
},
print_pdf : function(e){
e.preventDefault();
var self = this;
self._rpc({
model: 'ins.financial.report',
method: 'get_report_values',
args: [[self.wizard_id]],
}).then(function(data){
var action = {
'type': 'ir.actions.report',
'report_type': 'qweb-pdf',
'report_name': 'account_dynamic_reports.ins_report_financial',
'report_file': 'account_dynamic_reports.ins_report_financial',
'data': {'js_data':data},
'context': {'active_model':'ins.financial.report',
'landscape':1,
'from_js': true
},
'display_name': 'Finance Report',
};
return self.do_action(action);
});
},
print_xlsx : function(){
var self = this;
self._rpc({
model: 'ins.financial.report',
method: 'action_xlsx',
args: [[self.wizard_id]],
}).then(function(action){
action.context.active_ids = [self.wizard_id];
return self.do_action(action);
});
},
formatWithSign : function(amount, formatOptions, sign){
var currency_id = formatOptions.currency_id;
currency_id = session.get_currency(currency_id);
var without_sign = field_utils.format.monetary(Math.abs(amount), {}, formatOptions);
if(!amount){return '-'};
if (currency_id.position === "after") {
return sign + '&nbsp;' + without_sign + '&nbsp;' + currency_id.symbol;
} else {
return currency_id.symbol + '&nbsp;' + sign + '&nbsp;' + without_sign;
}
return without_sign;
},
plot_data : function(initial_render = true){
var self = this;
var node = self.$('.py-data-container');
var last;
while (last = node.lastChild) node.removeChild(last);
self._rpc({
model: 'ins.financial.report',
method: 'get_report_values',
args: [[self.wizard_id]],
}).then(function (datas) {
self.filter_data = datas.form;
self.account_data = datas.report_lines;
var formatOptions = {
currency_id: datas.currency,
noSymbol: true,};
self.initial_balance = self.formatWithSign(datas.initial_balance, formatOptions, datas.initial_balance < 0 ? '-' : '');
self.current_balance = self.formatWithSign(datas.current_balance, formatOptions, datas.current_balance < 0 ? '-' : '');
self.ending_balance = self.formatWithSign(datas.ending_balance, formatOptions, datas.ending_balance < 0 ? '-' : '');
_.each(self.account_data, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.balance_cmp = self.formatWithSign(k.balance_cmp, formatOptions, k.balance < 0 ? '-' : '');
});
if(initial_render){
self.$('.py-control-panel').html(QWeb.render('FilterSectionFr', {
filter_data : self.filter_data,
}));
self.$el.find('#date_from').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('#date_to').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('#date_from_cmp').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('#date_to_cmp').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('.date_filter-multiple').select2({
maximumSelectionSize: 1,
placeholder:'Select Date...',
});
self.$el.find('.journal-multiple').select2({
placeholder:'Select Journal...',
});
self.$el.find('.analytic-tag-multiple').select2({
placeholder:'Analytic Tags...',
});
self.$el.find('.analytic-multiple').select2({
placeholder:'Select Analytic...',
});
self.$el.find('.extra-multiple').select2({
placeholder:'Extra Options...',
})
.val('debit_credit').trigger('change')
;
}
self.$('.py-data-container').html(QWeb.render('DataSectionFr', {
account_data : self.account_data,
filter_data : self.filter_data,
}));
if(parseFloat(datas.initial_balance) > 0 || parseFloat(datas.current_balance) > 0 || parseFloat(datas.ending_balance) > 0){
$(".py-data-container").append(QWeb.render('SummarySectionFr', {
initial_balance : self.initial_balance,
current_balance : self.current_balance,
ending_balance: self.ending_balance}));
}
});},
view_gl : function(event){
event.preventDefault();
var self = this;
if(self.filter_data.date_from == false || self.filter_data.date_to == false){
    alert("'Start Date' and 'End Date' are mandatory!");
    return true;
}
var domains = {
account_ids : [$(event.currentTarget).data('account-id')] ,
initial_balance : (self.filter_data.rtype == 'CASH' || self.filter_data.rtype == 'PANDL') ? false : true
}
var context = {};
if ($("#date_from").val()){
var dateObject = $("#date_from").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
domains.date_from = dateString;
}
if ($("#date_to").val()){
var dateObject = $("#date_to").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
domains.date_to = dateString;
}
if(!domains.date_from && !domains.date_to && !domains.date_range){domains.date_from = self.filter_data.date_from;
domains.date_to = self.filter_data.date_to;}
var journal_ids = [];
var journal_list = $(".journal-multiple").select2('data')
for (var i=0; i < journal_list.length; i++){
journal_ids.push(parseInt(journal_list[i].id))
}
domains.journal_ids = journal_ids
var analytic_ids = [];
var analytic_list = $(".analytic-multiple").select2('data')
for (var i=0; i < analytic_list.length; i++){
analytic_ids.push(parseInt(analytic_list[i].id))
}
domains.analytic_ids = analytic_ids
var analytic_tag_ids = [];
var analytic_tag_list = $(".analytic-tag-multiple").select2('data')
for (var i=0; i < analytic_tag_list.length; i++){
analytic_tag_ids.push(parseInt(analytic_tag_list[i].id))
}
domains.analytic_tag_ids = analytic_tag_ids
var fr_wizard_id = 0;
self._rpc({
model: 'ins.general.ledger',
method: 'create',
args: [{}]
}).then(function (record){
fr_wizard_id = record;
self._rpc({
model: 'ins.general.ledger',
method: 'write',
args: [fr_wizard_id, domains]
}).then(function () {
var action = {
type: 'ir.actions.client',
name: 'GL View',
tag: 'dynamic.gl',
nodestroy: true ,
target: 'new',
context: {
wizard_id:fr_wizard_id,
active_id: self.wizard_id,
active_model:'ins.financial.report'
}
}
return self.do_action(action);
})
})
},
update_with_filter : function(event){
event.preventDefault();
var self = this;
self.initial_render = false;
var output = {date_range:false, enable_filter:false, debit_credit:false};
if($(".date_filter-multiple").select2('data').length === 1){
output.date_range = $(".date_filter-multiple").select2('data')[0].id
}
if ($("#date_from").val()){
var dateObject = $("#date_from").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_from = dateString;
output.date_to = false;
}
if ($("#date_to").val()){
var dateObject = $("#date_to").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_to = dateString;
output.date_from = false;
}
if ($("#date_from").val() && $("#date_to").val()) {
var dateObject = $("#date_from").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_from = dateString;
var dateObject = $("#date_to").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_to = dateString;
}
if ($("#date_from_cmp").val()){
var dateObject = $("#date_from_cmp").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_from_cmp = dateString;
output.enable_filter = true;
}
if ($("#date_to_cmp").val()){
var dateObject = $("#date_to_cmp").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_to_cmp = dateString;
output.enable_filter = true;
}
var journal_ids = [];
var journal_list = $(".journal-multiple").select2('data')
for (var i=0; i < journal_list.length; i++){
journal_ids.push(parseInt(journal_list[i].id))
}
output.journal_ids = journal_ids
var analytic_ids = [];
var analytic_list = $(".analytic-multiple").select2('data')
for (var i=0; i < analytic_list.length; i++){
analytic_ids.push(parseInt(analytic_list[i].id))
}
output.analytic_ids = analytic_ids
var analytic_tag_ids = [];
var analytic_tag_list = $(".analytic-tag-multiple").select2('data')
for (var i=0; i < analytic_tag_list.length; i++){
analytic_tag_ids.push(parseInt(analytic_tag_list[i].id))
}
output.analytic_tag_ids = analytic_tag_ids
var options_list = $(".extra-multiple").select2('data')
for (var i=0; i < options_list.length; i++){
if(options_list[i].id === 'debit_credit'){
output.debit_credit = true;
}
}
self._rpc({
model: 'ins.financial.report',
method: 'write',
args: [self.wizard_id, output],
}).then(function(res){
self.plot_data(self.initial_render);
});
},
});
var DynamicGlMain = AbstractAction.extend({
template:'DynamicGlMain',
events: {
'click #filter_apply_button': 'update_with_filter',
'click #pdf': 'print_pdf',
'click #xlsx': 'print_xlsx',
'click .view-source': 'view_move_line',
'click .py-mline': 'fetch_move_lines',
'click .py-mline-page': 'fetch_move_lines_by_page'
},
init : function(view, code){
this._super(view, code);
this.wizard_id = code.context.wizard_id | null;
this.session = session;
},
start : function(){
var self = this;
self.initial_render = true;
if(! self.wizard_id){
self._rpc({
model: 'ins.general.ledger',
method: 'create',
args: [{res_model: this.res_model}]
}).then(function (record) {
self.wizard_id = record;
self.plot_data(self.initial_render);
})
}else{
self.plot_data(self.initial_render);
}
},
print_pdf : function(e){
e.preventDefault();
var self = this;
self._rpc({
model: 'ins.general.ledger',
method: 'get_report_datas',
args: [[self.wizard_id]],
}).then(function(data){
var action = {
'type': 'ir.actions.report',
'report_type': 'qweb-pdf',
'report_name': 'account_dynamic_reports.general_ledger',
'report_file': 'account_dynamic_reports.general_ledger',
'data': {'js_data':data},
'context': {'active_model':'ins.general.ledger',
'landscape':1,
'from_js': true
},
'display_name': 'General Ledger',
};
return self.do_action(action);
});
},
print_xlsx : function(){
var self = this;
self._rpc({
model: 'ins.general.ledger',
method: 'action_xlsx',
args: [[self.wizard_id]],
}).then(function(action){
action.context.active_ids = [self.wizard_id];
return self.do_action(action);
});
},
formatWithSign : function(amount, formatOptions, sign){
var currency_id = formatOptions.currency_id;
currency_id = session.get_currency(currency_id);
var without_sign = field_utils.format.monetary(Math.abs(amount), {}, formatOptions);
if(!amount){return '-'};
if (currency_id.position === "after") {
return sign + '&nbsp;' + without_sign + '&nbsp;' + currency_id.symbol;
} else {
return currency_id.symbol + '&nbsp;' + sign + '&nbsp;' + without_sign;
}
return without_sign;
},
plot_data : function(initial_render = true){
var self = this;
self.loader_disable_ui();
var node = self.$('.py-data-container-orig');
var last;
while (last = node.lastChild) node.removeChild(last);
self._rpc({
model: 'ins.general.ledger',
method: 'get_report_datas',
args: [[self.wizard_id]],
}).then(function (datas) {
self.filter_data = datas[0]
self.account_data = datas[1]
_.each(self.account_data, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {isUTC: true}));
_.each(k.lines, function (ks, vs){
ks.debit = self.formatWithSign(ks.debit, formatOptions, ks.debit < 0 ? '-' : '');
ks.credit = self.formatWithSign(ks.credit, formatOptions, ks.credit < 0 ? '-' : '');
ks.balance = self.formatWithSign(ks.balance, formatOptions, ks.balance < 0 ? '-' : '');
ks.ldate = field_utils.format.date(field_utils.parse.date(ks.ldate, {}, {isUTC: true}));
});
});
if(initial_render){
self.$('.py-control-panel').html(QWeb.render('FilterSection', {
filter_data : datas[0],
}));
self.$el.find('#date_from').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('#date_to').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('.date_filter-multiple').select2({
maximumSelectionSize: 1,
placeholder:'Select Date...',
});
self.$el.find('.extra-multiple').select2({
placeholder:'Extra Options...',
})
.val(['include_details','initial_balance']).trigger('change')
;
self.$el.find('.account-multiple').select2({
placeholder:'Select Account...',
});
self.$el.find('.account-tag-multiple').select2({
placeholder:'Account Tags...',
});
self.$el.find('.analytic-tag-multiple').select2({
placeholder:'Analytic Tags...',
});
self.$el.find('.analytic-multiple').select2({
placeholder:'Select Analytic...',
});
self.$el.find('.journal-multiple').select2({
placeholder:'Select Journal...',
});
}
self.$('.py-data-container-orig').html(QWeb.render('DataSection', {
account_data : datas[1]
}));
self.loader_enable_ui();
});
},
gl_lines_by_page : function(offset, account_id){
var self = this;
return self._rpc({
model: 'ins.general.ledger',
method: 'build_detailed_move_lines',
args: [self.wizard_id, offset, account_id],
})
},
fetch_move_lines_by_page : function(event){
event.preventDefault();
var self = this;
var account_id = $(event.currentTarget).data('account-id');
var offset = parseInt($(event.currentTarget).data('page-number')) - 1;
var total_rows = parseInt($(event.currentTarget).data('count'));
self.loader_disable_ui();
self.gl_lines_by_page(offset, account_id).then(function(datas){
_.each(datas[2], function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {isUTC: true}));
});
$(event.currentTarget).parent().parent().parent().find('.py-mline-table-div').remove();
$(event.currentTarget).parent().parent().find('a').css({'background-color': 'white','font-weight': 'normal'});
$(event.currentTarget).parent().parent().after(
QWeb.render('SubSection', {
count: datas[0],
offset: datas[1],
account_data : datas[2],
}));
$(event.currentTarget).css({
'background-color': '#00ede8',
'font-weight': 'bold',
});
self.loader_enable_ui()
})
},
fetch_move_lines : function(event){
event.preventDefault();
var self = this;
var account_id = $(event.currentTarget).data('account-id');
var offset = 0;
var td = $(event.currentTarget).next('tr').find('td');
if (td.length == 1){
self.loader_disable_ui();
self.gl_lines_by_page(offset, account_id).then(function(datas){
_.each(datas[2], function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {isUTC: true}));
});
$(event.currentTarget).next('tr').find('td .py-mline-table-div').remove();
$(event.currentTarget).next('tr').find('td ul').after(
QWeb.render('SubSection', {
count: datas[0],
offset: datas[1],
account_data : datas[2],
}))
$(event.currentTarget).next('tr').find('td ul li:first a').css({
'background-color': '#00ede8',
'font-weight': 'bold',
});
self.loader_enable_ui();
})
}
},
view_move_line : function(event){
event.preventDefault();
var self = this;
var context = {};
var redirect_to_document = function (res_model, res_id, view_id) {
var action = {
type:'ir.actions.act_window',
view_type: 'form',
view_mode: 'form',
res_model: res_model,
views: [[view_id || false, 'form']],
res_id: res_id,
target: 'current',
context: context,
};
self.do_notify(_("Redirected"), "Window has been redirected");
return self.do_action(action);
};
redirect_to_document('account.move',$(event.currentTarget).data('move-id'));
},
update_with_filter : function(event){
event.preventDefault();
var self = this;
self.initial_render = false;
var output = {date_range:false};
output.display_accounts = 'balance_not_zero';
output.initial_balance = false;
output.include_details = false;
var journal_ids = [];
var journal_list = $(".journal-multiple").select2('data')
for (var i=0; i < journal_list.length; i++){
journal_ids.push(parseInt(journal_list[i].id))
}
output.journal_ids = journal_ids
var account_ids = [];
var account_list = $(".account-multiple").select2('data')
for (var i=0; i < account_list.length; i++){
account_ids.push(parseInt(account_list[i].id))
}
output.account_ids = account_ids
var account_tag_ids = [];
var account_tag_list = $(".account-tag-multiple").select2('data')
for (var i=0; i < account_tag_list.length; i++){
account_tag_ids.push(parseInt(account_tag_list[i].id))
}
output.account_tag_ids = account_tag_ids
var analytic_ids = [];
var analytic_list = $(".analytic-multiple").select2('data')
for (var i=0; i < analytic_list.length; i++){
analytic_ids.push(parseInt(analytic_list[i].id))
}
output.analytic_ids = analytic_ids
var analytic_tag_ids = [];
var analytic_tag_list = $(".analytic-tag-multiple").select2('data')
for (var i=0; i < analytic_tag_list.length; i++){
analytic_tag_ids.push(parseInt(analytic_tag_list[i].id))
}
output.analytic_tag_ids = analytic_tag_ids
if($(".date_filter-multiple").select2('data').length === 1){
output.date_range = $(".date_filter-multiple").select2('data')[0].id
}
var options_list = $(".extra-multiple").select2('data')
for (var i=0; i < options_list.length; i++){
if(options_list[i].id === 'initial_balance'){
output.initial_balance = true;
}
if(options_list[i].id === 'bal_not_zero'){
output.display_accounts = 'balance_not_zero';
}
if(options_list[i].id === 'include_details'){
output.include_details = true;
}
}
if ($("#date_from").val()){
var dateObject = $("#date_from").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_from = dateString;
}
if ($("#date_to").val()){
var dateObject = $("#date_to").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_to = dateString;
}
self._rpc({
model: 'ins.general.ledger',
method: 'write',
args: [[self.wizard_id], output],
}).then(function(res){
self.plot_data(self.initial_render);
});
},
loader_disable_ui: function(){
$('.py-main-container').addClass('ui-disabled');
$('.py-main-container').css({'opacity': '0.4','cursor':'wait'});
$('#loader').css({'visibility':'visible','opacity': '1'});
},
loader_enable_ui: function(){
$('.py-main-container').removeClass('ui-disabled');
$('#loader').css({'visibility':'hidden'});
$('.py-main-container').css({'opacity': '1','cursor':'auto'});
},
});
var DynamicPaMain = AbstractAction.extend({
template:'DynamicPaMain',
events: {
'click #filter_apply_button': 'update_with_filter',
'click #pdf': 'print_pdf',
'click #xlsx': 'print_xlsx',
'click .view-source': 'view_move_line',
'click .py-mline': 'fetch_move_lines',
'click .py-mline-page': 'fetch_move_lines_by_page'
},
init : function(view, code){
this._super(view, code);
this.wizard_id = code.context.wizard_id | null;
this.session = session;
},
start : function(){
var self = this;
self.initial_render = true;
if(! self.wizard_id){
self._rpc({
model: 'ins.partner.ageing',
method: 'create',
args: [{res_model: this.res_model}]
}).then(function (record) {
self.wizard_id = record;
self.plot_data(self.initial_render);
})
}else{
self.plot_data(self.initial_render);
}
},
print_pdf : function(e){
e.preventDefault();
var self = this;
self._rpc({
model: 'ins.partner.ageing',
method: 'get_report_datas',
args: [[self.wizard_id]],
}).then(function(data){
var action = {
'type': 'ir.actions.report',
'report_type': 'qweb-pdf',
'report_name': 'account_dynamic_reports.partner_ageing',
'report_file': 'account_dynamic_reports.partner_ageing',
'data': {'js_data':data},
'context': {'active_model':'ins.partner.ageing',
'landscape':1,
'from_js': true
},
'display_name': 'Partner Ageing',
};
return self.do_action(action);
});
},
print_xlsx : function(){
var self = this;
self._rpc({
model: 'ins.partner.ageing',
method: 'action_xlsx',
args: [[self.wizard_id]],
}).then(function(action){
action.context.active_ids = [self.wizard_id];
return self.do_action(action);
});
},
formatWithSign : function(amount, formatOptions, sign){
var currency_id = formatOptions.currency_id;
currency_id = session.get_currency(currency_id);
var without_sign = field_utils.format.monetary(Math.abs(amount), {}, formatOptions);
if(!amount){return '-'};
if (currency_id.position === "after") {
return sign + '&nbsp;' + without_sign + '&nbsp;' + currency_id.symbol;
} else {
return currency_id.symbol + '&nbsp;' + sign + '&nbsp;' + without_sign;
}
return without_sign;
},
plot_data : function(initial_render = true){
var self = this;
self.loader_disable_ui();
var node = self.$('.py-data-container-orig');
var last;
while (last = node.lastChild) node.removeChild(last);
self._rpc({
model: 'ins.partner.ageing',
method: 'get_report_datas',
args: [[self.wizard_id]],
}).then(function (datas) {
self.filter_data = datas[0]
self.ageing_data = datas[1]
self.period_dict = datas[2]
self.period_list = datas[3]
_.each(self.ageing_data, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
for(var z = 0; z < self.period_list.length; z++){
k[self.period_list[z]] = self.formatWithSign(k[self.period_list[z]], formatOptions, k[self.period_list[z]] < 0 ? '-' : '');
}
k.total = self.formatWithSign(k.total, formatOptions, k.total < 0 ? '-' : '');
});
if(initial_render){
self.$('.py-control-panel').html(QWeb.render('FilterSectionPa', {
filter_data : self.filter_data,
}));
self.$el.find('#as_on_date').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('.type-multiple').select2({
maximumSelectionSize: 1,
placeholder:'Select Account Type...',
});
self.$el.find('.partner-type-multiple').select2({
maximumSelectionSize: 1,
placeholder:'Select Partner Type...',
});
self.$el.find('.partner-multiple').select2({
placeholder:'Select Partner...',
});
self.$el.find('.partner-tag-multiple').select2({
placeholder:'Select Tag...',
});
self.$el.find('.extra-multiple').select2({
placeholder:'Extra Options...',
})
.val('include_details').trigger('change')
;
}
self.$('.py-data-container-orig').html(QWeb.render('DataSectionPa', {
ageing_data : self.ageing_data,
period_dict : self.period_dict,
period_list : self.period_list
}));
self.loader_enable_ui();
});
},
ageing_lines_by_page : function(offset, account_id){
var self = this;
return self._rpc({
model: 'ins.partner.ageing',
method: 'process_detailed_data',
args: [self.wizard_id, offset, account_id],
})
},
fetch_move_lines_by_page : function(event){
event.preventDefault();
var self = this;
var partner_id = $(event.currentTarget).data('partner-id');
var offset = parseInt($(event.currentTarget).data('page-number')) - 1;
var total_rows = parseInt($(event.currentTarget).data('count'));
self.loader_disable_ui();
self.ageing_lines_by_page(offset, partner_id).then(function(datas){
var count = datas[0];
var offset = datas[1];
var account_data = datas[2];
var period_list = datas[3];
_.each(account_data, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.range_0 = self.formatWithSign(k.range_0, formatOptions, k.range_0 < 0 ? '-' : '');
k.range_1 = self.formatWithSign(k.range_1, formatOptions, k.range_1 < 0 ? '-' : '');
k.range_2 = self.formatWithSign(k.range_2, formatOptions, k.range_2 < 0 ? '-' : '');
k.range_3 = self.formatWithSign(k.range_3, formatOptions, k.range_3 < 0 ? '-' : '');
k.range_4 = self.formatWithSign(k.range_4, formatOptions, k.range_4 < 0 ? '-' : '');
k.range_5 = self.formatWithSign(k.range_5, formatOptions, k.range_5 < 0 ? '-' : '');
k.range_6 = self.formatWithSign(k.range_6, formatOptions, k.range_6 < 0 ? '-' : '');
k.date_maturity = field_utils.format.date(field_utils.parse.date(k.date_maturity, {}, {isUTC: true}));
});
$(event.currentTarget).parent().parent().parent().find('.py-mline-table-div').remove();
$(event.currentTarget).parent().parent().find('a').css({'background-color': 'white','font-weight': 'normal'});
$(event.currentTarget).parent().parent().after(
QWeb.render('SubSectionPa', {
count: count,
offset: offset,
account_data : account_data,
period_list: period_list
}));
$(event.currentTarget).css({
'background-color': '#00ede8',
'font-weight': 'bold',
});
self.loader_enable_ui()
})
},
fetch_move_lines : function(event){
event.preventDefault();
var self = this;
var partner_id = $(event.currentTarget).data('partner-id');
var offset = 0;
var td = $(event.currentTarget).next('tr').find('td');
if (td.length == 1){
self.loader_disable_ui();
self.ageing_lines_by_page(offset, partner_id).then(function(datas){
var count = datas[0];
var offset = datas[1];
var account_data = datas[2];
var period_list = datas[3];
_.each(account_data, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.range_0 = self.formatWithSign(k.range_0, formatOptions, k.range_0 < 0 ? '-' : '');
k.range_1 = self.formatWithSign(k.range_1, formatOptions, k.range_1 < 0 ? '-' : '');
k.range_2 = self.formatWithSign(k.range_2, formatOptions, k.range_2 < 0 ? '-' : '');
k.range_3 = self.formatWithSign(k.range_3, formatOptions, k.range_3 < 0 ? '-' : '');
k.range_4 = self.formatWithSign(k.range_4, formatOptions, k.range_4 < 0 ? '-' : '');
k.range_5 = self.formatWithSign(k.range_5, formatOptions, k.range_5 < 0 ? '-' : '');
k.range_6 = self.formatWithSign(k.range_6, formatOptions, k.range_6 < 0 ? '-' : '');
k.date_maturity = field_utils.format.date(field_utils.parse.date(k.date_maturity, {}, {isUTC: true}));
});
$(event.currentTarget).next('tr').find('td .py-mline-table-div').remove();
$(event.currentTarget).next('tr').find('td ul').after(
QWeb.render('SubSectionPa', {
count: count,
offset: offset,
account_data: account_data,
period_list: period_list
}))
$(event.currentTarget).next('tr').find('td ul li:first a').css({
'background-color': '#00ede8',
'font-weight': 'bold',
});
self.loader_enable_ui();
})
}
},
view_move_line : function(event){
event.preventDefault();
var self = this;
var context = {};
var redirect_to_document = function (res_model, res_id, view_id) {
var action = {
type:'ir.actions.act_window',
view_type: 'form',
view_mode: 'form',
res_model: res_model,
views: [[view_id || false, 'form']],
res_id: res_id,
target: 'current',
context: context,
};
self.do_notify(_("Redirected"), "Window has been redirected");
return self.do_action(action);
};
redirect_to_document('account.move',$(event.currentTarget).data('move-id'));
},
update_with_filter : function(event){
event.preventDefault();
var self = this;
self.initial_render = false;
var output = {}
output.type = false;
output.include_details = false;
output.partner_type = false;
output.bucket_1 = $("#bucket_1").val();
output.bucket_2 = $("#bucket_2").val();
output.bucket_3 = $("#bucket_3").val();
output.bucket_4 = $("#bucket_4").val();
output.bucket_5 = $("#bucket_5").val();
if((parseInt(output.bucket_1) >= parseInt(output.bucket_2)) | (parseInt(output.bucket_2) >= parseInt(output.bucket_3)) |
(parseInt(output.bucket_3) >= parseInt(output.bucket_4)) | (parseInt(output.bucket_4) >= parseInt(output.bucket_5))){
alert('Bucket order must be ascending');
return;
}
if($(".type-multiple").select2('data').length === 1){
output.type = $(".type-multiple").select2('data')[0].id
}
if($(".partner-type-multiple").select2('data').length === 1){
output.partner_type = $(".partner-type-multiple").select2('data')[0].id
}
var partner_ids = [];
var partner_list = $(".partner-multiple").select2('data')
for (var i=0; i < partner_list.length; i++){
partner_ids.push(parseInt(partner_list[i].id))
}
output.partner_ids = partner_ids
var partner_tag_ids = [];
var partner_tag_list = $(".partner-tag-multiple").select2('data')
for (var i=0; i < partner_tag_list.length; i++){
partner_tag_ids.push(parseInt(partner_tag_list[i].id))
}
output.partner_category_ids = partner_tag_ids
if ($("#as_on_date").val()){
var dateObject = $("#as_on_date").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.as_on_date = dateString;
}
var options_list = $(".extra-multiple").select2('data')
for (var i=0; i < options_list.length; i++){
if(options_list[i].id === 'include_details'){
output.include_details = true;
}
}
self._rpc({
model: 'ins.partner.ageing',
method: 'write',
args: [self.wizard_id, output],
}).then(function(res){
self.plot_data(self.initial_render);
});
},
loader_disable_ui: function(){
$('.py-main-container').addClass('ui-disabled');
$('.py-main-container').css({'opacity': '0.4','cursor':'wait'});
$('#loader').css({'visibility':'visible','opacity': '1'});
},
loader_enable_ui: function(){
$('.py-main-container').removeClass('ui-disabled');
$('#loader').css({'visibility':'hidden'});
$('.py-main-container').css({'opacity': '1','cursor':'auto'});
},
});
var DynamicPlMain = AbstractAction.extend({
template:'DynamicPlMain',
events: {
'click #filter_apply_button': 'update_with_filter',
'click #pdf': 'print_pdf',
'click #xlsx': 'print_xlsx',
'click .view-source': 'view_move_line',
'click .py-mline': 'fetch_move_lines',
'click .py-mline-page': 'fetch_move_lines_by_page'
},
init : function(view, code){
this._super(view, code);
this.wizard_id = code.context.wizard_id | null;
this.session = session;
},
start : function(){
var self = this;
self.initial_render = true;
if(! self.wizard_id){
self._rpc({
model: 'ins.partner.ledger',
method: 'create',
args: [{res_model: this.res_model}]
}).then(function (record) {
self.wizard_id = record;
self.plot_data(self.initial_render);
})
}else{
self.plot_data(self.initial_render);
}
},
print_pdf : function(e){
e.preventDefault();
var self = this;
self._rpc({
model: 'ins.partner.ledger',
method: 'get_report_datas',
args: [[self.wizard_id]],
}).then(function(data){
var action = {
'type': 'ir.actions.report',
'report_type': 'qweb-pdf',
'report_name': 'account_dynamic_reports.partner_ledger',
'report_file': 'account_dynamic_reports.partner_ledger',
'data': {'js_data':data},
'context': {'active_model':'ins.partner.ledger',
'landscape':1,
'from_js': true
},
'display_name': 'Partner Ledger',
};
return self.do_action(action);
});
},
print_xlsx : function(){
var self = this;
self._rpc({
model: 'ins.partner.ledger',
method: 'action_xlsx',
args: [[self.wizard_id]],
}).then(function(action){
action.context.active_ids = [self.wizard_id];
return self.do_action(action);
});
},
formatWithSign : function(amount, formatOptions, sign){
var currency_id = formatOptions.currency_id;
currency_id = session.get_currency(currency_id);
var without_sign = field_utils.format.monetary(Math.abs(amount), {}, formatOptions);
if(!amount){return '-'};
if (currency_id.position === "after") {
return sign + '&nbsp;' + without_sign + '&nbsp;' + currency_id.symbol;
} else {
return currency_id.symbol + '&nbsp;' + sign + '&nbsp;' + without_sign;
}
return without_sign;
},
plot_data : function(initial_render = true){
var self = this;
self.loader_disable_ui();
var node = self.$('.py-data-container-orig');
var last;
while (last = node.lastChild) node.removeChild(last);
self._rpc({
model: 'ins.partner.ledger',
method: 'get_report_datas',
args: [[self.wizard_id]],
}).then(function (datas) {
self.filter_data = datas[0]
self.account_data = datas[1]
_.each(self.account_data, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {isUTC: true}));
_.each(k.lines, function (ks, vs){
ks.debit = self.formatWithSign(ks.debit, formatOptions, ks.debit < 0 ? '-' : '');
ks.credit = self.formatWithSign(ks.credit, formatOptions, ks.credit < 0 ? '-' : '');
ks.balance = self.formatWithSign(ks.balance, formatOptions, ks.balance < 0 ? '-' : '');
ks.ldate = field_utils.format.date(field_utils.parse.date(ks.ldate, {}, {isUTC: true}));
});
});
if(initial_render){
self.$('.py-control-panel').html(QWeb.render('FilterSectionPl', {
filter_data : datas[0],
}));
self.$el.find('#date_from').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('#date_to').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('.date_filter-multiple').select2({
maximumSelectionSize: 1,
placeholder:'Select Date...',
});
self.$el.find('.extra-multiple').select2({
placeholder:'Extra Options...',
})
.val(['include_details','initial_balance']).trigger('change');
self.$el.find('.type-multiple').select2({
maximumSelectionSize: 1,
placeholder:'Select Account Type...',
});
self.$el.find('.reconciled-multiple').select2({
maximumSelectionSize: 1,
placeholder:'Select Reconciled...',
});
self.$el.find('.partner-multiple').select2({
placeholder:'Select Partner...',
});
self.$el.find('.partner-tag-multiple').select2({
placeholder:'Select Tag...',
});
self.$el.find('.account-multiple').select2({
placeholder:'Select Account...',
});
self.$el.find('.journal-multiple').select2({
placeholder:'Select Journal...',
});
}
self.$('.py-data-container-orig').html(QWeb.render('DataSectionPl', {
account_data : datas[1]
}));
self.loader_enable_ui();
});
},
pl_lines_by_page : function(offset, account_id){
var self = this;
return self._rpc({
model: 'ins.partner.ledger',
method: 'build_detailed_move_lines',
args: [self.wizard_id, offset, account_id],
})
},
fetch_move_lines_by_page : function(event){
event.preventDefault();
var self = this;
var account_id = $(event.currentTarget).data('account-id');
var offset = parseInt($(event.currentTarget).data('page-number')) - 1;
var total_rows = parseInt($(event.currentTarget).data('count'));
self.loader_disable_ui();
self.pl_lines_by_page(offset, account_id).then(function(datas){
_.each(datas[2], function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {isUTC: true}));
});
$(event.currentTarget).parent().parent().parent().find('.py-mline-table-div').remove();
$(event.currentTarget).parent().parent().find('a').css({'background-color': 'white','font-weight': 'normal'});
$(event.currentTarget).parent().parent().after(
QWeb.render('SubSectionPl', {
count: datas[0],
offset: datas[1],
account_data : datas[2],
}));
$(event.currentTarget).css({
'background-color': '#00ede8',
'font-weight': 'bold',
});
self.loader_enable_ui()
})
},
fetch_move_lines : function(event){
event.preventDefault();
var self = this;
var account_id = $(event.currentTarget).data('account-id');
var offset = 0;
var td = $(event.currentTarget).next('tr').find('td');
if (td.length == 1){
self.loader_disable_ui();
self.pl_lines_by_page(offset, account_id).then(function(datas){
_.each(datas[2], function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {isUTC: true}));
});
$(event.currentTarget).next('tr').find('td .py-mline-table-div').remove();
$(event.currentTarget).next('tr').find('td ul').after(
QWeb.render('SubSectionPl', {
count: datas[0],
offset: datas[1],
account_data : datas[2],
}))
$(event.currentTarget).next('tr').find('td ul li:first a').css({
'background-color': '#00ede8',
'font-weight': 'bold',
});
self.loader_enable_ui();
})
}
},
view_move_line : function(event){
event.preventDefault();
var self = this;
var context = {};
var redirect_to_document = function (res_model, res_id, view_id) {
var action = {
type:'ir.actions.act_window',
view_type: 'form',
view_mode: 'form',
res_model: res_model,
views: [[view_id || false, 'form']],
res_id: res_id,
target: 'current',
context: context,
};
self.do_notify(_("Redirected"), "Window has been redirected");
return self.do_action(action);
};
redirect_to_document('account.move',$(event.currentTarget).data('move-id'));
},
update_with_filter : function(event){
event.preventDefault();
var self = this;
self.initial_render = false;
var output = {date_range:false};
output.type = false;
output.display_accounts = 'balance_not_zero';
output.initial_balance = false;
output.balance_less_than_zero = false;
output.balance_greater_than_zero = false;
output.reconciled = false;
output.include_details = false;
if($(".reconciled-multiple").select2('data').length === 1){
output.reconciled = $(".reconciled-multiple").select2('data')[0].id
}
var journal_ids = [];
var journal_list = $(".journal-multiple").select2('data')
for (var i=0; i < journal_list.length; i++){
journal_ids.push(parseInt(journal_list[i].id))
}
output.journal_ids = journal_ids
var partner_ids = [];
var partner_list = $(".partner-multiple").select2('data')
for (var i=0; i < partner_list.length; i++){
partner_ids.push(parseInt(partner_list[i].id))
}
output.partner_ids = partner_ids
var partner_tag_ids = [];
var partner_tag_list = $(".partner-tag-multiple").select2('data')
for (var i=0; i < partner_tag_list.length; i++){
partner_tag_ids.push(parseInt(partner_tag_list[i].id))
}
output.partner_category_ids = partner_tag_ids
var account_ids = [];
var account_list = $(".account-multiple").select2('data')
for (var i=0; i < account_list.length; i++){
account_ids.push(parseInt(account_list[i].id))
}
output.account_ids = account_ids
if($(".date_filter-multiple").select2('data').length === 1){
output.date_range = $(".date_filter-multiple").select2('data')[0].id}
if($(".type-multiple").select2('data').length === 1){
output.type = $(".type-multiple").select2('data')[0].id}
var options_list = $(".extra-multiple").select2('data')
for (var i=0; i < options_list.length; i++){
if(options_list[i].id === 'initial_balance'){
output.initial_balance = true;}
if(options_list[i].id === 'bal_not_zero'){
output.display_accounts = 'balance_not_zero';}
if(options_list[i].id === 'include_details'){
output.include_details = true;}
if(options_list[i].id === 'balance_less_than_zero'){
output.balance_less_than_zero = true;}
if(options_list[i].id === 'balance_greater_than_zero'){
output.balance_greater_than_zero = true;}}
if ($("#date_from").val()){
var dateObject = $("#date_from").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_from = dateString;
}
if ($("#date_to").val()){
var dateObject = $("#date_to").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_to = dateString;
}
self._rpc({
model: 'ins.partner.ledger',
method: 'write',
args: [self.wizard_id, output],
}).then(function(res){
self.plot_data(self.initial_render);
});
},
loader_disable_ui: function(){
$('.py-main-container').addClass('ui-disabled');
$('.py-main-container').css({'opacity': '0.4','cursor':'wait'});
$('#loader').css({'visibility':'visible','opacity': '1'});
},
loader_enable_ui: function(){
$('.py-main-container').removeClass('ui-disabled');
$('#loader').css({'visibility':'hidden'});
$('.py-main-container').css({'opacity': '1','cursor':'auto'});
},
});
var DynamicTbMain = AbstractAction.extend({
template:'DynamicTbMain',
events: {
'click #filter_apply_button': 'update_with_filter',
'click #pdf': 'print_pdf',
'click #xlsx': 'print_xlsx',
'click .view-source': 'view_gl',
},
init : function(view, code){
this._super(view, code);
this.wizard_id = code.context.wizard_id | null;
this.session = session;
},
start : function(){
var self = this;
self.initial_render = true;
if(! self.wizard_id){
self._rpc({
model: 'ins.trial.balance',
method: 'create',
args: [{res_model: this.res_model}]
}).then(function (record) {
self.wizard_id = record;
self.plot_data(self.initial_render);
})
}else{
self.plot_data(self.initial_render);
}
},
print_pdf : function(e){
e.preventDefault();
var self = this;
self._rpc({
model: 'ins.trial.balance',
method: 'get_report_datas',
args: [[self.wizard_id]]
}).then(function(data){
var action = {
'type': 'ir.actions.report',
'report_type': 'qweb-pdf',
'report_name': 'account_dynamic_reports.trial_balance',
'report_file': 'account_dynamic_reports.trial_balance',
'data': {'js_data':data},
'context': {'active_model':'ins.trial.balance',
'landscape':1,
'from_js': true
},
'display_name': 'General Ledger',
};
return self.do_action(action);
});
},
print_xlsx : function(){
var self = this;
self._rpc({
model: 'ins.trial.balance',
method: 'action_xlsx',
args: [[self.wizard_id]],
}).then(function(action){
action.context.active_ids = [self.wizard_id];
return self.do_action(action);
});
},
formatWithSign : function(amount, formatOptions, sign){
var currency_id = formatOptions.currency_id;
currency_id = session.get_currency(currency_id);
var without_sign = field_utils.format.monetary(Math.abs(amount), {}, formatOptions);
if(!amount){return '-'};
if (currency_id.position === "after") {
return sign + '&nbsp;' + without_sign + '&nbsp;' + currency_id.symbol;
} else {
return currency_id.symbol + '&nbsp;' + sign + '&nbsp;' + without_sign;
}
return without_sign;
},
plot_data : function(initial_render = true){
var self = this;
var node = self.$('.py-data-container');
var last;
while (last = node.lastChild) node.removeChild(last);
self._rpc({
model: 'ins.trial.balance',
method: 'get_report_datas',
args: [[self.wizard_id]],
}).then(function (datas) {
self.filter_data = datas[0];
self.account_data = datas[1];
self.retained = datas[2];
self.subtotal = datas[3];
_.each(self.account_data, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.initial_debit = self.formatWithSign(k.initial_debit, formatOptions, k.initial_debit < 0 ? '-' : '');
k.initial_credit = self.formatWithSign(k.initial_credit, formatOptions, k.initial_credit < 0 ? '-' : '');
k.initial_balance = self.formatWithSign(k.initial_balance, formatOptions, k.initial_balance < 0 ? '-' : '');
k.ending_debit = self.formatWithSign(k.ending_debit, formatOptions, k.ending_debit < 0 ? '-' : '');
k.ending_credit = self.formatWithSign(k.ending_credit, formatOptions, k.ending_credit < 0 ? '-' : '');
k.ending_balance = self.formatWithSign(k.ending_balance, formatOptions, k.ending_balance < 0 ? '-' : '');
});
_.each(self.retained, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.initial_debit = self.formatWithSign(k.initial_debit, formatOptions, k.initial_debit < 0 ? '-' : '');
k.initial_credit = self.formatWithSign(k.initial_credit, formatOptions, k.initial_credit < 0 ? '-' : '');
k.initial_balance = self.formatWithSign(k.initial_balance, formatOptions, k.initial_balance < 0 ? '-' : '');
k.ending_debit = self.formatWithSign(k.ending_debit, formatOptions, k.ending_debit < 0 ? '-' : '');
k.ending_credit = self.formatWithSign(k.ending_credit, formatOptions, k.ending_credit < 0 ? '-' : '');
k.ending_balance = self.formatWithSign(k.ending_balance, formatOptions, k.ending_balance < 0 ? '-' : '');
});
_.each(self.subtotal, function (k, v){
var formatOptions = {
currency_id: k.company_currency_id,
noSymbol: true,
};
k.debit = self.formatWithSign(k.debit, formatOptions, k.debit < 0 ? '-' : '');
k.credit = self.formatWithSign(k.credit, formatOptions, k.credit < 0 ? '-' : '');
k.balance = self.formatWithSign(k.balance, formatOptions, k.balance < 0 ? '-' : '');
k.initial_debit = self.formatWithSign(k.initial_debit, formatOptions, k.initial_debit < 0 ? '-' : '');
k.initial_credit = self.formatWithSign(k.initial_credit, formatOptions, k.initial_credit < 0 ? '-' : '');
k.initial_balance = self.formatWithSign(k.initial_balance, formatOptions, k.initial_balance < 0 ? '-' : '');
k.ending_debit = self.formatWithSign(k.ending_debit, formatOptions, k.ending_debit < 0 ? '-' : '');
k.ending_credit = self.formatWithSign(k.ending_credit, formatOptions, k.ending_credit < 0 ? '-' : '');
k.ending_balance = self.formatWithSign(k.ending_balance, formatOptions, k.ending_balance < 0 ? '-' : '');
});
self.filter_data.date_from_tmp = self.filter_data.date_from;
self.filter_data.date_to_tmp = self.filter_data.date_to;
self.filter_data.date_from = field_utils.format.date(field_utils.parse.date(self.filter_data.date_from, {}, {isUTC: true}));
self.filter_data.date_to = field_utils.format.date(field_utils.parse.date(self.filter_data.date_to, {}, {isUTC: true}));
if(initial_render){
self.$('.py-control-panel').html(QWeb.render('FilterSectionTb', {
filter_data : self.filter_data,
}));
self.$el.find('#date_from').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('#date_to').datepicker({ dateFormat: 'dd-mm-yy' });
self.$el.find('.date_filter-multiple').select2({
maximumSelectionSize: 1,
placeholder:'Select Date...',
});
self.$el.find('.extra-multiple').select2({
placeholder:'Extra Options...',
}).val('bal_not_zero').trigger('change');
self.$el.find('.analytic-multiple').select2({
placeholder:'Select Analytic...',
});
self.$el.find('.journal-multiple').select2({
placeholder:'Select Journal...',
});
}
self.$('.py-data-container').html(QWeb.render('DataSectionTb', {
account_data : self.account_data,
retained : self.retained,
subtotal : self.subtotal,
filter_data : self.filter_data,
}));
});
},
view_gl : function(event){
event.preventDefault();
var self = this;
var domains = {account_ids : [$(event.currentTarget).data('account-id')],
initial_balance : false}
var context = {};
var journal_ids = [];
var journal_list = $(".journal-multiple").select2('data')
for (var i=0; i < journal_list.length; i++){
journal_ids.push(parseInt(journal_list[i].id))
}
domains.journal_ids = journal_ids
var analytic_ids = [];
var analytic_list = $(".analytic-multiple").select2('data')
for (var i=0; i < analytic_list.length; i++){
analytic_ids.push(parseInt(analytic_list[i].id))
}
domains.analytic_ids = analytic_ids
if($(".date_filter-multiple").select2('data').length === 1){
domains.date_range = $(".date_filter-multiple").select2('data')[0].id
}
if ($("#date_from").val()){
var dateObject = $("#date_from").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
domains.date_from = dateString;
}
if ($("#date_to").val()){
var dateObject = $("#date_to").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
domains.date_to = dateString;
}
if(!domains.date_from && !domains.date_to && !domains.date_range){domains.date_from = self.filter_data.date_from_tmp;
domains.date_to = self.filter_data.date_to_tmp;}
var gl_wizard_id = 0;
self._rpc({
model: 'ins.general.ledger',
method: 'create',
args: [{}]
}).then(function (record){
gl_wizard_id = record;
self._rpc({
model: 'ins.general.ledger',
method: 'write',
args: [gl_wizard_id, domains]
}).then(function () {
var action = {
type: 'ir.actions.client',
name: 'GL View',
tag: 'dynamic.gl',
nodestroy: true ,
target: 'new',
context: {
wizard_id:gl_wizard_id,
active_id: self.wizard_id,
active_model:'ins.trial.balance'
}
}
return self.do_action(action);
})
})
},
update_with_filter : function(event){
event.preventDefault();
var self = this;
self.initial_render = false;
var output = {date_range:false};
output.display_accounts = 'all';
output.show_hierarchy = false;
var journal_ids = [];
var journal_list = $(".journal-multiple").select2('data')
for (var i=0; i < journal_list.length; i++){
journal_ids.push(parseInt(journal_list[i].id))
}
output.journal_ids = journal_ids
var analytic_ids = [];
var analytic_list = $(".analytic-multiple").select2('data')
for (var i=0; i < analytic_list.length; i++){
analytic_ids.push(parseInt(analytic_list[i].id))
}
output.analytic_ids = analytic_ids
if($(".date_filter-multiple").select2('data').length === 1){
output.date_range = $(".date_filter-multiple").select2('data')[0].id
}
var options_list = $(".extra-multiple").select2('data')
for (var i=0; i < options_list.length; i++){
if(options_list[i].id === 'bal_not_zero'){
output.display_accounts = 'balance_not_zero';
}
if(options_list[i].id === 'show_hierarchy'){
output.show_hierarchy = true;
}
}
if ($("#date_from").val()){
var dateObject = $("#date_from").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_from = dateString;
}
if ($("#date_to").val()){
var dateObject = $("#date_to").datepicker("getDate");
var dateString = $.datepicker.formatDate("yy-mm-dd", dateObject);
output.date_to = dateString;
}
self._rpc({
model: 'ins.trial.balance',
method: 'write',
args: [self.wizard_id, output],
}).then(function(res){
self.plot_data(self.initial_render);
});},});core.action_registry.add('dynamic.fr', DynamicFrMain);core.action_registry.add('dynamic.gl', DynamicGlMain);core.action_registry.add('dynamic.pa', DynamicPaMain);core.action_registry.add('dynamic.pl', DynamicPlMain);core.action_registry.add('dynamic.tb', DynamicTbMain);});
