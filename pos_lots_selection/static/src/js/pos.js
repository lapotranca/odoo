odoo.define('pos_lots_selection.product_lot', function(require) {
    "use strict";

    var gui = require('point_of_sale.gui');
    var rpc = require('web.rpc');
    var screens = require('point_of_sale.screens');
    var models = require('point_of_sale.models');
    var PopupWidget = require('point_of_sale.popups');
    var core = require('web.core');
    var ActionpadWidget = require('point_of_sale.screens').ActionpadWidget;
    var _t = core._t;

    ActionpadWidget.include({
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.pay').unbind();
            this.$('.pay').click(function(){
                var order = self.pos.get_order();
                var sum_lot_qty = {};
                _.each(order.orderlines.models, function(line){
                    console.log('line ', line, line.product);
                    console.log('line ');
                    _.each(line.lot_ids, function(lotline_id){
                        console.log("lotline_id.qty_done ", lotline_id.qty_done);
                        if(sum_lot_qty[line.product.id] == undefined){
                            sum_lot_qty[line.product.id] = {};
                        }
                        if(sum_lot_qty[line.product.id][lotline_id.lot_id] == undefined){
                            sum_lot_qty[line.product.id][lotline_id.lot_id] = 0;
                        }
                        sum_lot_qty[line.product.id][lotline_id.lot_id] = sum_lot_qty[line.product.id][lotline_id.lot_id] + lotline_id.qty_done;
                    });
                    // line.product.lot_result.lot_id[0]
                });
                var has_valid_product_lot = _.every(order.orderlines.models, function(line){
                    console.log('line ', line, line.product);
                    console.log('line ');
                    return line.has_valid_product_lot();
                });
                var has_more_donethan_allowed = false;
                _.each(order.orderlines.models, function(line){
                    _.each(line.product.lot_result, function(lot_res){
                        if(sum_lot_qty[line.product.id] == undefined){
                            has_valid_product_lot = false;
                            return;
                        }
                        var done_qty = sum_lot_qty[line.product.id][lot_res.lot_id[0]];
                        var allowed_qty = lot_res.quantity;
                        if(done_qty>allowed_qty){
                            has_more_donethan_allowed = true;
                        }
                    });
                });
                if(has_more_donethan_allowed){
                    self.gui.show_popup('confirm',{//we can replace 'confirm' with 'alert'/'error'
                        'title': _t('More done quantities'),
                        'body':  _t('More Quantities done than available in the lot.'),
                    });
                }
                else if(!has_valid_product_lot){
                    self.gui.show_popup('confirm',{//we can replace 'confirm' with 'alert'/'error'
                        'title': _t('Empty Serial/Lot Quantity'),
                        'body':  _t('One or more product(s) require Lot Quantity to proceed further.'),
                    });
                }else{
                    self.gui.show_screen('payment');
                }
            });
        },
    });
    models.Order = models.Order.extend({
        display_lot_popup: function() {//custom function
            var self  = this;
            var order_line = this.get_selected_orderline();
            var product = order_line.get_product();
            var picking_type_id = this.pos.config.picking_type_id[0];

            rpc.query({
                model: 'stock.quant',
                method: 'get_pos_quants',
                args: [[product.id, picking_type_id]],
            }).then(function(backend_result) {
                if (backend_result) {
                    if (order_line) {
                        product.lot_result = backend_result;
                        // order_line.compute_lot_lines();
                        self.pos.gui.show_popup('PackLotLinePopupWidgetNew', {
                            'title': 'Lot/Serial Number(s)',
                            'pack_lot_lines': backend_result,
                            'order_line': order_line,
                            'order': this,
                        });
                    }
                }

            });
        },
    });

    screens.OrderWidget.include({
        render_orderline: function(orderline) {
            var node = this._super(orderline);
            var line_extra = node.querySelector('.quant-line-extra');
            if (line_extra) {
                line_extra.addEventListener('click', (function() {
                    this.show_popup_lot(orderline);
                }.bind(this)));
            }
            return node;
        },
        show_popup_lot: function(orderline) {//custom function
            this.pos.get_order().select_orderline(orderline);
            var order = this.pos.get_order();
            order.display_lot_popup();
        },
    });

    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr, options) {
            _super_orderline.initialize.apply(this, arguments);
            console.log("this, arguments ", this, arguments);
            if(!this.lot_ids){
                this.lot_ids = [];
            }
            if(!this.has_product_customlot){
                this.has_product_customlot = false;
            }
        },
        has_valid_product_lot: function() {
            if(!this.has_product_lot){ // if product has lots
                return true;
            }
            var expected_qty = 0;
            _.each(this.lot_ids, function(ld){expected_qty=expected_qty+ld.qty_done;});

            if(this.quantity != expected_qty){
                this.lot_ids = [];
                this.has_product_customlot = false;
                return false;
            }
            if(this.lot_ids.length > 0 && this.has_product_customlot){
                return this.has_product_customlot;
            }
            return false;// but there is no lot_ids and 
        },
        set_lot_ids: function(lot_ids) {//custom function
            this.lot_ids = lot_ids;
        },
        get_lot_ids: function() {//custom function
            return this.lot_ids;
        },
        export_as_JSON: function() {
            var data = _super_orderline.export_as_JSON.apply(this, arguments);
            data.lot_ids = this.lot_ids;
            data.has_product_customlot = this.has_product_customlot;
            return data;
        },
        init_from_JSON: function(json) {
            this.lot_ids = json.lot_ids;
            this.has_product_customlot = json.has_product_customlot;
            _super_orderline.init_from_JSON.call(this, json);
        },
    });

    // new widget, so fine if we dont check it in details for v13
    var PackLotLinePopupWidgetNew = PopupWidget.extend({
        template: 'PackLotLinePopupWidgetNew',
        events: _.extend({}, PopupWidget.prototype.events, {}),
        show: function(options) {
            this._super(options);
            this.update_qty();

            this.$('.lot_qty_autocheckbox').click(function(event){
                var ev_target = $(event.target);
                var checked = ev_target[0].checked;
                if(checked){
                    $('.'+ev_target.attr('id')).val(parseInt(ev_target.attr('data-lot_qty')));
                }
                if(!checked){
                    $('.'+ev_target.attr('id')).val("");
                }
            });

        },
        update_qty: function(){
            var order_line = this.pos.get_order().get_selected_orderline();
            var get_lot_ids = order_line.get_lot_ids();
            if (get_lot_ids != 'undefined' && get_lot_ids.length > 0) {
                $('.popup').find('.lot_inputs').each(function(index, el) {
                    var cid = $(el).attr('data-lot-index');
                    $.each(get_lot_ids, function(index, dict) {
                        if (dict['lot_id'] == cid) {
                            $(el).val(dict['qty_done']);
                        }
                     });
                });
            }
        },
        click_cancel: function(){
            this._super();
            // this.pos.get_order().get_selected_orderline().set_quantity(0);
        },
        click_confirm: function() {
            var self = this;
            var order_line = this.options.order_line;
            var pack_lot_lines = this.options.pack_lot_lines;
            var lot_inputs = self.$('.lot_inputs');
            var lot_ids = [];
            var has_error = false;
            var has_blank_inputs = false;
            var has_atleast_onefilled = false;
            if (lot_inputs) {
                var sum = 0;
                _.each(lot_inputs, function(lotinput) {
                    var lotinput_val = $(lotinput).val(); 
                    var lot_qty = parseInt(lotinput_val);
                    if(lotinput_val == ""){
                        lot_qty = 0;
                    }
                    var datalotqty = $(lotinput).parent().parent().children('td.lot_qty').data('lotqty');
                    if(lot_qty > datalotqty || lot_qty <= 0){
                        $(lotinput).css('border','2px solid red');
                        has_blank_inputs = true;
                    }
                    else if (lot_qty) {
                        sum += lot_qty;
                        var lot_id = lotinput.getAttribute('data-lot-index');
                        var package_id = lotinput.getAttribute('data-package_id');
                        lot_ids.push({
                            'lot_id': parseInt(lot_id),
                            'qty_done': lot_qty,
                            'package_id': package_id,
                        });
                        order_line.has_product_customlot = true;
                        has_atleast_onefilled = true;
                    }
                });
                if(has_blank_inputs && !has_atleast_onefilled)
                    return;
                order_line.set_quantity(sum);
                order_line.set_lot_ids(lot_ids);
                this.gui.close_popup();
            }
        },
    });
    gui.define_popup({
        name: 'PackLotLinePopupWidgetNew',
        widget: PackLotLinePopupWidgetNew
    });

    return {PackLotLinePopupWidgetNew:PackLotLinePopupWidgetNew};

});
