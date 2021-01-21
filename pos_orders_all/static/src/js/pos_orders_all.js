odoo.define('pos_orders_all.pos', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var core = require('web.core');
	var gui = require('point_of_sale.gui');
	var popups = require('point_of_sale.popups');
	var QWeb = core.qweb;
	var rpc = require('web.rpc');
	
	var utils = require('web.utils');
	var session = require('web.session');
	var time = require('web.time');
	var round_pr = utils.round_precision;
	var chrome = require('point_of_sale.chrome');

	var _t = core._t;

	var prd_list_count = 0;

	chrome.OrderSelectorWidget.include({
		events: {
			"click .pos-stock-sync": "do_pos_lock_screen",
		},

		init: function(parent, options) {
			this._super(parent, options);
			this.do_pos_lock_screen();
		},

		do_pos_lock_screen: function (e) {
			var self = this;
			this.pos.set('is_sync',true);
			this.product_list_widget = new screens.ProductListWidget(this,{
				click_product_action: function(product){ self.click_product(product); },
				product_list: this.pos.db.get_product_by_category(0)
			});
			this.product_list_widget.renderElement();
		},
	});

	// Load Models here...

	models.load_models({
		model:  'sale.order',
		fields: ['name','partner_id','user_id','amount_untaxed',
				 'order_line','amount_tax','amount_total','company_id','date_order'],
		domain: null,
		loaded: function(self,order){
			var i=0;
			self.all_sale_orders_list = order;
			self.get_orders_by_id = {};
			order.forEach(function(orders) {
				self.get_orders_by_id[orders.id] = orders;
			});
		},
	});

	models.load_models({
		model: 'sale.order.line',
		fields: ['order_id', 'product_id', 'discount', 'product_uom_qty', 'price_unit','price_subtotal'],
		domain: function(self) {
			var order_lines = []
			var orders = self.all_sale_orders_list;
			for (var i = 0; i < orders.length; i++) {
				order_lines = order_lines.concat(orders[i]['order_line']);
			}
			return [
				['id', 'in', order_lines]
			];
		},
		loaded: function(self, sale_order_line) {
			self.all_sale_orders_line_list = sale_order_line;
			self.get_lines_by_id = {};
			sale_order_line.forEach(function(line) {
				self.get_lines_by_id[line.id] = line;
			});

			self.sale_order_line = sale_order_line;
		},
	});


	models.load_models({
		model: 'stock.location',
		fields: [],
		//ids:    function(self){ return [self.config.stock_location_id[0]]; },
		loaded: function(self, locations){
			var i;
			self.locations = locations[0];
			if (self.config.show_stock_location == 'specific')
			{
				// associate the Locations with their quants.
				var ilen = locations.length;
				for(i = 0; i < ilen; i++){
					if(locations[i].id === self.config.stock_location_id[0]){
						var ayaz = locations[i];
						self.locations = ayaz;
					}
				}
			}
		},
	});

	models.load_models({
		model: 'pos.order',
		fields: ['return_order_ref','name', 'id', 'date_order','discount_type', 'partner_id', 'pos_reference', 'lines', 'amount_total','amount_tax','session_id', 'state', 'company_id','coupon_id','barcode'],
		domain: function(self){ 
			var current = self.pos_session.id
			if (self.config.pos_session_limit == 'all')
			{
				return [['state', 'not in', ['draft', 'cancel']]]; 
			}
			if (self.config.pos_session_limit == 'last3')
			{
				return [['state', 'not in', ['draft', 'cancel']],['session_id', 'in',[current,current-1,current-2,current-3]]]; 
			}
			if (self.config.pos_session_limit == 'last5')
			{
				return [['state', 'not in', ['draft', 'cancel']],['session_id', 'in',[current,current-1,current-2,current-3,current-4,current-5]]]; 
			}
		}, 
		loaded: function(self, orders){
			self.db.all_orders_list = orders;

			self.db.get_orders_by_id = {};
			orders.forEach(function(order) {
				self.db.get_orders_by_id[order.id] = order;
			});
			self.orders = orders;
		},
	});
	
	models.load_models({
		model: 'pos.gift.coupon',
		fields: ['name','apply_coupon_on', 'c_barcode', 'user_id', 'issue_date', 'expiry_date', 'partner_id', 'order_ids', 'active', 'amount', 'description','used','coupon_count', 'coupon_apply_times','expiry_date','partner_true','partner_id'],
		domain: null,
		loaded: function(self, pos_gift_coupon) { 
			self.pos_gift_coupon = pos_gift_coupon;    
		},
	});
	
	models.load_models({
		model: 'pos.coupons.setting',
		fields: ['name', 'product_id', 'min_coupan_value', 'max_coupan_value', 'max_exp_date', 'default_name', 'default_value', 'default_availability', 'active'],
		domain: null,
		loaded: function(self, pos_coupons_setting) { 
			self.pos_coupons_setting = pos_coupons_setting;
		},
	});

	models.load_models({
		model: 'pos.order.line',
		fields: ['return_qty','original_line_id','order_id', 'product_id', 'discount', 'qty', 'price_unit','discount_line_type'],
		domain: function(self) {
			var order_lines = []
			var orders = self.db.all_orders_list;
			for (var i = 0; i < orders.length; i++) {
				order_lines = order_lines.concat(orders[i]['lines']);
			}
			return [
				['id', 'in', order_lines]
			];
		},
		loaded: function(self, pos_order_line) {
			self.db.all_orders_line_list = pos_order_line;
			self.db.get_lines_by_id = {};
			pos_order_line.forEach(function(line) {
				self.db.get_lines_by_id[line.id] = line;
			});

			self.pos_order_line = pos_order_line;
		},
	});


	// bi_pos_custom_discount load models
	models.load_models({
		model: 'pos.custom.discount',
		fields: ['name','discount','description','available_pos_ids'],
		domain: function(self) {
			return [
				['id', 'in', self.config.custom_discount_ids]
			];
		},
		loaded: function(self, pos_custom_discount) {
			
			self.pos_custom_discount = pos_custom_discount;
		},

	});
	
	

	var SaleOrderButtonWidget = screens.ActionButtonWidget.extend({
		template: 'SaleOrderButtonWidget',
		button_click: function() {
			var self = this;
			this.gui.show_screen('see_all_sale_orders_screen_widget', {});
		},

	});

	screens.define_action_button({
		'name': 'See All Orders Button Widget',
		'widget': SaleOrderButtonWidget,
		'condition': function() {
			return true;
		},
	});
	
	
	var _super_posmodel = models.PosModel.prototype;
	models.PosModel = models.PosModel.extend({
		
		initialize: function (session, attributes) {
			var product_model = _.find(this.models, function(model){ return model.model === 'product.product'; });
			product_model.fields.push('available_quantity','qty_available','virtual_available','incoming_qty','outgoing_qty','type');

			return _super_posmodel.initialize.call(this, session, attributes);
		},
		
		push_order: function(order, opts){
			var self = this;
			var pushed = _super_posmodel.push_order.call(this, order, opts);
			var client = order && order.get_client();
			if (order){
				if (this.config.pos_display_stock === true && this.config.pos_stock_type == 'onhand' || this.config.pos_stock_type == 'available'){
				order.orderlines.each(function(line){
					var product = line.get_product();
					product['bi_on_hand'] -= line.get_quantity();
					product['bi_available'] -= line.get_quantity();
					product.qty_available -= line.get_quantity();
					self.load_product_qty(product);
				})
				}
			}
			return pushed;
		},
		
		load_product_qty:function(product){
			var product_qty_final = $("[data-product-id='"+product.id+"'] #stockqty");
			product_qty_final.html(product.bi_on_hand);
			var product_qty_avail = $("[data-product-id='"+product.id+"'] #availqty");
			product_qty_avail.html(product.bi_available);
		},

		_save_to_server: function(orders, options) {
			var self = this;
			return _super_posmodel._save_to_server.call(this, orders, options).then(function(new_orders) {
				if (new_orders != null) {
					new_orders.forEach(function(order) {
						if (order) {
							rpc.query({
								model: 'pos.order',
								method: 'return_new_order',
								args: [order['id']],
								
								}).then(function(output) {
									self.db.all_orders_list.unshift(output);
									self.db.get_orders_by_id[order['id']] = order;
							});
							rpc.query({
								model: 'pos.order',
								method: 'return_new_order_line',
								args: [order['id']],
							
							}).then(function(output1) {
									for(var ln=0; ln < output1.length; ln++){
										self.db.all_orders_line_list.unshift(output1[ln]);
									}
							});
						}
					});
				}
				return new_orders;
			});
		}
		
	});
	
	screens.ProductListWidget.include({
		init: function(parent, options) {
			var self = this;
			this._super(parent,options);
			this.model = options.model;
			this.productwidgets = [];
			this.weight = options.weight || 0;
			this.show_scale = options.show_scale || false;
			this.next_screen = options.next_screen || false;

			this.click_product_handler = function(){
				self.check_quantity(this.dataset.productId,options);
			};
		},

		check_quantity: function(prd,options) {
			var self = this;
			var product = self.pos.db.get_product_by_id(prd);
			if(self.pos.config.pos_display_stock)
			{
				if(self.pos.config.show_stock_location == 'specific')
				{
					if (product.type == 'product')
					{
						var partner_id = self.pos.get_client();
						var location = self.pos.locations;

						rpc.query({
								model: 'stock.quant',
								method: 'get_single_product',
								args: [partner_id ? partner_id.id : 0,product.id, location],
							
							},{async : false}).then(function(output) {
								if (self.pos.config.pos_allow_order == false)
								{
									if (output[0][1] <= self.pos.config.pos_deny_order)
									{
										self.gui.show_popup('error',{
											'title': _t('Deny Order'),
											'body': _t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock.")
										});
									}
									else if (output[0][1] <= 0)
									{
										self.gui.show_popup('error',{
											'title': _t('Error: Out of Stock'),
											'body': _t("(" + product.display_name + ")" + " is Out of Stock."),
										});
									}
									else{
										options.click_product_action(product);
									}
								}
								else if(self.pos.config.pos_allow_order == true)
								{
									if (output[0][1] <= self.pos.config.pos_deny_order)
									{
										self.gui.show_popup('error',{
											'title': _t('Deny Order'),
											'body': _t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock.")
										});
									}
									else{
										options.click_product_action(product);
									}
								}
								else{
									options.click_product_action(product);		
								}
						});
					}
					else{
						options.click_product_action(product);
					}
				}
				else{

					if (product.type == 'product' && self.pos.config.pos_allow_order == false)
					{
					// Deny POS Order When Product is Out of Stock
						if (product.qty_available <= self.pos.config.pos_deny_order && self.pos.config.pos_allow_order == false)
						{
							self.gui.show_popup('error',{
								'title': _t('Deny Order'),
								'body': _t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock.")
							});
						}
						 
						
						// Allow POS Order When Product is Out of Stock
						else if (product.qty_available <= 0 && self.pos.config.pos_allow_order == false)
						{
							self.gui.show_popup('error',{
								'title': _t('Error: Out of Stock'),
								'body': _t("(" + product.display_name + ")" + " is Out of Stock."),
							});
						} else {
							options.click_product_action(product);
						}
					}
					else if(product.type == 'product' && self.pos.config.pos_allow_order == true && product.qty_available <= self.pos.config.pos_deny_order){
					self.gui.show_popup('error',{
							'title': _t('Error: Out of Stock'),
							'body': _t("(" + product.display_name + ")" + " is Out of Stock."),
						});
					}	
					else if(product.type == 'product' && self.pos.config.pos_allow_order == true && product.qty_available >= self.pos.config.pos_deny_order){
						options.click_product_action(product);
					} 
					else {
						options.click_product_action(product);
					}
				}
			}
			else{
				options.click_product_action(product);
			}
		},

		renderElement: function() {
			var self = this;
			var el_str  = QWeb.render(this.template, {widget: this});
			var el_node = document.createElement('div');
				el_node.innerHTML = el_str;
				el_node = el_node.childNodes[1];
			if(this.el && this.el.parentNode){
				this.el.parentNode.replaceChild(el_node,this.el);
			}
			this.el = el_node;
			var list_container = el_node.querySelector('.product-list');

			if (self.pos.config.show_stock_location == 'specific')
			{
				var x_sync = this.pos.get("is_sync")
				var location = self.pos.locations;
				if(x_sync == true){
					if (self.pos.config.pos_stock_type == 'onhand')
					{
						rpc.query({
								model: 'stock.quant',
								method: 'get_stock_location_qty',
								args: [1, location],
							
							},{async : false}).then(function(output) {
								self.pos.loc_onhand = output[0];
								for(var i = 0, len = self.product_list.length; i < len; i++){
									self.product_list[i]['bi_on_hand'] = self.product_list[i].qty_available;
									self.product_list[i]['bi_available'] = self.product_list[i].virtual_available;

									for(let key in self.pos.loc_onhand)
									{
										if(self.product_list[i].id == key)
										{
											self.product_list[i]['bi_on_hand'] = self.pos.loc_onhand[key];

											var product_qty_final = $("[data-product-id='"+self.product_list[i].id+"'] #stockqty");
											product_qty_final.html(self.pos.loc_onhand[key])
											var product_qty_avail = $("[data-product-id='"+self.product_list[i].id+"'] #availqty");
											product_qty_avail.html(self.product_list[i].virtual_available);
										}
									}
									var product_node = self.render_product(self.product_list[i]);
									product_node.addEventListener('click',self.click_product_handler);
									product_node.addEventListener('keypress',self.keypress_product_handler);
									list_container.appendChild(product_node);
								}
								self.pos.set("is_sync",false);
						});
					}
					if (self.pos.config.pos_stock_type == 'available')
					{
						rpc.query({
								model: 'product.product',
								method: 'get_stock_location_avail_qty',
								args: [1, location],
							
						},{async : false}).then(function(output) {
								
							self.pos.loc_available = output[0];
							for(var i = 0, len = self.product_list.length; i < len; i++){
								self.product_list[i]['bi_on_hand'] = self.product_list[i].qty_available;
								self.product_list[i]['bi_available'] = self.product_list[i].virtual_available;

								for(let key in self.pos.loc_available)
								{
									if(self.product_list[i].id == key)
									{
										self.product_list[i]['bi_available'] = self.pos.loc_available[key];
										var product_qty_final = $("[data-product-id='"+self.product_list[i].id+"'] #stockqty");
										product_qty_final.html(self.product_list[i].qty_available)
										var product_qty_avail = $("[data-product-id='"+self.product_list[i].id+"'] #availqty");
										product_qty_avail.html(self.pos.loc_available[key]);
									}
								}
								var product_node = self.render_product(self.product_list[i]);
								product_node.addEventListener('click',self.click_product_handler);
								product_node.addEventListener('keypress',self.keypress_product_handler);
								list_container.appendChild(product_node);
							}
							self.pos.set("is_sync",false);
						});
					}
				}else{
					for(var i = 0, len = self.product_list.length; i < len; i++){
						var product_node = this.render_product(self.product_list[i]);
						product_node.addEventListener('click',this.click_product_handler);
						product_node.addEventListener('keypress',this.keypress_product_handler);
						list_container.appendChild(product_node);
					}
				}
			}
			else{
				for(var i = 0, len = self.product_list.length; i < len; i++){
					self.product_list[i]['bi_on_hand'] = self.product_list[i].qty_available;
					self.product_list[i]['bi_available'] = self.product_list[i].virtual_available;
					var product_node = this.render_product(self.product_list[i]);
					product_node.addEventListener('click',this.click_product_handler);
					product_node.addEventListener('keypress',this.keypress_product_handler);
					list_container.appendChild(product_node);
				}
			}

			prd_list_count += 1;
			if(prd_list_count > 0){
				self.pos.set("is_sync",false);
			}
		},

	});
	
	var ValidQtyPopupWidget = popups.extend({
		template: 'ValidQtyPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		//
		show: function(options) {
			var self = this;
			this._super(options);
		},
		//
		renderElement: function() {
			var self = this;
			this._super();
			this.$('#back_to_products').click(function() {
				self.gui.show_screen('products');
			});            	
		},

	});
	gui.define_popup({
		name: 'valid_qty_popup_widget',
		widget: ValidQtyPopupWidget
	});

	// End Popup start
	
	// ActionpadWidget start
	screens.ActionpadWidget.include({
		renderElement: function() {
			var self = this;
			this._super();
			this.$('.pay').click(function(){
				var order = self.pos.get_order();
				var has_valid_product_lot = _.every(order.orderlines.models, function(line){
					return line.has_valid_product_lot();
				});
				if(!has_valid_product_lot){
					self.gui.show_popup('error',{
						'title': _t('Empty Serial/Lot Number'),
						'body':  _t('One or more product(s) required serial/lot number.'),
						confirm: function(){
							self.gui.show_screen('payment');
						},
					});
				}else{
					self.gui.show_screen('payment');
				}
				if(self.pos.config.pos_display_stock)
				{
					if (self.pos.config.show_stock_location == 'specific')
					{
						var partner_id = self.pos.get_client();
						var location = self.pos.locations;
						var lines = order.get_orderlines();
						var prods = [];

						for (var i = 0; i < lines.length; i++) {
							if (lines[i].product.type == 'product'){
								prods.push(lines[i].product.id)
							}
						}
						rpc.query({
							model: 'stock.quant',
							method: 'get_products_stock_location_qty',
							args: [partner_id ? partner_id.id : 0, location,prods],
						},{async:false}).then(function(output) {
							var flag = 0;
							for (var i = 0; i < lines.length; i++) {
								var keys = $.map(output[0], function(value, key) {
									if (lines[i].product.type == 'product' && lines[i].product['id'] == key){
										if(self.pos.config.pos_allow_order == false && lines[i].quantity > value){
											flag = flag + 1;
											self.gui.show_popup('valid_qty_popup_widget', {});
										}
										var check = value - lines[i].quantity;
										if(self.pos.config.pos_allow_order == true && check <= self.pos.config.pos_deny_order){
											flag = flag + 1;
											self.gui.show_popup('valid_qty_popup_widget', {});
										}
									}
								});
							}
							if(flag > 0){
								self.gui.show_popup('valid_qty_popup_widget', {});
							}
							else{
								self.gui.show_screen('payment');
							}
						});
					
					} else {
						// When Ordered Qty it More than Available Qty, Raise Error popup
						var lines = order.get_orderlines();
						for (var i = 0; i < lines.length; i++) {
							if (lines[i].product.type == 'product'){
								if (self.pos.config.pos_allow_order == false && lines[i].quantity > lines[i].product['qty_available']){
									self.gui.show_popup('valid_qty_popup_widget', {});
									break;
								}
								var check = lines[i].product['qty_available'] - lines[i].quantity;
								if(self.pos.config.pos_allow_order == true && check <= self.pos.config.pos_deny_order){
									self.gui.show_popup('valid_qty_popup_widget', {});
									break;
								}
							}
							else { 
								 self.gui.show_screen('payment');   
							}
						}
					}	
				}
								
			});
			this.$('.set-customer').click(function(){
				self.gui.show_screen('clientlist');
			});
			
		},
	});  
	// End ActionpadWidget start
			
		
	var _super_order = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function(attr, options) {
			this.barcode = this.barcode || "";
			this.return_order_ref = this.return_order_ref || false;
			this.coupon_id = this.coupon_id || false;
			this.coup_maxamount = this.coup_maxamount || 0.0;
			this.set_barcode();
			_super_order.initialize.call(this,attr,options);
		},

		set_barcode: function(){
			var self = this;	
			var temp = Math.floor(100000000000+ Math.random() * 9000000000000)
			self.barcode =  temp.toString();
		},

		set_return_order_ref: function (return_order_ref) {
			this.return_order_ref = return_order_ref;
		},

		export_as_JSON: function() {
			var json = _super_order.export_as_JSON.apply(this,arguments);
			json.coupon_id = this.coupon_id;
			json.coup_maxamount = this.coup_maxamount;
			json.barcode = this.barcode;
			json.return_order_ref = this.return_order_ref  || false;
			return json;
		},

		init_from_JSON: function(json){
			_super_order.init_from_JSON.apply(this,arguments);
			this.coupon_id = json.coupon_id;
			this.coup_maxamount = json.coup_maxamount;
			this.barcode = json.barcode;
			this.return_order_ref = json.return_order_ref || false;
		},
		
		get_total_items: function() {
			var utils = require('web.utils');
			var round_pr = utils.round_precision;
			return round_pr(this.orderlines.reduce((function(sum, orderLine) {
				return sum + orderLine.quantity;
			}), 0), this.pos.currency.rounding);
		},
		
	   get_fixed_discount: function() {
			var total=0.0;
			var i;
			for(i=0;i<this.orderlines.models.length;i++) 
			{
				total = total + Math.min(Math.max(parseFloat(this.orderlines.models[i].discount * this.orderlines.models[i].quantity) || 0, 0),10000);
			}
			return total
		},
	});
	
	// exports.Orderline = Backbone.Model.extend ...
	var OrderlineSuper = models.Orderline.prototype;
	models.Orderline = models.Orderline.extend({

		initialize: function(attr, options) {
			this.original_line_id = this.original_line_id || false;
			OrderlineSuper.initialize.call(this,attr,options);
		},

		set_original_line_id: function(original_line_id){
			this.original_line_id = original_line_id;
		},

		get_original_line_id: function(){
			return this.original_line_id;
		},

		export_as_JSON: function() {
			var json = OrderlineSuper.export_as_JSON.apply(this,arguments);
			json.original_line_id = this.original_line_id || false;
			return json;
		},
		
		init_from_JSON: function(json){
			OrderlineSuper.init_from_JSON.apply(this,arguments);
			this.original_line_id = json.original_line_id;
		},
	

		set_discount: function(discount){
			if (this.pos.config.discount_type == 'percentage')
			{
				var disc = Math.min(Math.max(parseFloat(discount) || 0, 0),100);
			}
			else if (this.pos.config.discount_type == 'fixed')
			{
				var disc = discount;
			}
			this.discount = disc;
			this.discountStr = '' + disc;
			this.trigger('change',this);
		},
	

		get_base_price:    function(){
			var rounding = this.pos.currency.rounding;
			if (this.pos.config.discount_type == 'percentage')
			{
				return round_pr(this.get_unit_price() * this.get_quantity() * (1 - this.get_discount()/100), rounding);
			}
			else if (this.pos.config.discount_type == 'fixed')
			{
				return round_pr((this.get_unit_price()- this.get_discount())* this.get_quantity(), rounding);	
			}
		},
		
		get_all_prices: function(){
			
			if (this.pos.config.discount_type == 'percentage')
			{
				var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
			}
			else if (this.pos.config.discount_type == 'fixed')
			{
				// var price_unit = this.get_unit_price() - this.get_discount();
				var price_unit = this.get_base_price()/this.get_quantity();		
			}	
			var taxtotal = 0;

			var product =  this.get_product();
			var taxes_ids = product.taxes_id;
			var taxes =  this.pos.taxes;
			var taxdetail = {};
			var product_taxes = [];

			_(taxes_ids).each(function(el){
				product_taxes.push(_.detect(taxes, function(t){
					return t.id === el;
				}));
			});

			var all_taxes = this.compute_all(product_taxes, price_unit, this.get_quantity(), this.pos.currency.rounding);
			_(all_taxes.taxes).each(function(tax) {
				taxtotal += tax.amount;
				taxdetail[tax.id] = tax.amount;
			});

			return {
				"priceWithTax": all_taxes.total_included,
				"priceWithoutTax": all_taxes.total_excluded,
				"tax": taxtotal,
				"taxDetails": taxdetail,
			};
		},
		
	});
	// End Orderline start

 


	// Start POSBarcodeReturnWidget
	
	var POSBarcodeReturnWidget = screens.ActionButtonWidget.extend({
		template: 'POSBarcodeReturnWidget',

		button_click: function() {
			var self = this;
			//this.gui.show_screen('see_all_orders_screen_widget', {});
			this.gui.show_popup('pos_barcode_popup_widget', {});
		},
		
	});

	screens.define_action_button({
		'name': 'POS Return Order with Barcode',
		'widget': POSBarcodeReturnWidget,
		'condition': function() {
			return true;
		},
	});
	// End POSBarcodeReturnWidget       

	screens.ReceiptScreenWidget.include({
		show: function () {
			this._super(); 
			var order = this.pos.get_order();                     
			$("#barcode_print").barcode(
				order.barcode, // Value barcode (dependent on the type of barcode)
				"code128" // type (string)
			);
			
			prd_list_count = 0;
			this.pos.set("is_sync",true);
		},
	});
	
	// ReceiptScreenWidgetNew start
	var ReceiptScreenWidgetNew = screens.ScreenWidget.extend({
		template: 'ReceiptScreenWidgetNew',
		
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},

		show: function(options) {
			var self = this;
			options = options || {};
			self._super(options);

			var order = this.pos.get_order();
			var order_screen_params = order.get_screen_data('params');

			this.render_reprint_receipt();

			$('.button.back').on("click", function() {
				self.gui.show_screen('see_all_orders_screen_widget');
			});
			$('.button.print').click(function() {
				var test = self.chrome.screens.receipt;
				setTimeout(function() { self.chrome.screens.receipt.lock_screen(false); }, 1000);
				if (!test['_locked']) {
					self.chrome.screens.receipt.print_web();
					self.chrome.screens.receipt.lock_screen(true);
				}
			});
			
			$("#barcode_print1").barcode(
				order_screen_params['barcode'], // Value barcode (dependent on the type of barcode)
				"code128" // type (string)
			);
			
			if (self.should_auto_print()) {
				// window.print();
				setTimeout(function(){
					window.print();
					return;
				}, 500);
			}
			
		},

		render_reprint_receipt: function() {
			this.$('.pos-receipt-container').html(QWeb.render('OrderReceipt1', this.get_reprint_receipt_render_env()));
		},

		should_auto_print: function() {
			return this.pos.config.iface_print_auto && !this.pos.get_order()._printed;
		},

		get_reprint_receipt_render_env: function() {
			var order = this.pos.get_order();
			var order_screen_params = order.get_screen_data('params');
			return {
				widget: order_screen_params['widget'],
				order:  order_screen_params['order'],
				paymentlines: order_screen_params['paymentlines'],
				orderlines:  order_screen_params['orderlines'],
				discount_total:  order_screen_params['discount_total'],
				change:  order_screen_params['change'],
				subtotal:  order_screen_params['subtotal'],
				tax:  order_screen_params['tax'],
				barcode: order_screen_params['barcode'],
				date_order : order_screen_params['date_order']
			};
		},
	});
	gui.define_screen({ name: 'ReceiptScreenWidgetNew', widget: ReceiptScreenWidgetNew });

	// SeeAllOrdersScreenWidget start
	var SeeAllOrdersScreenWidget = screens.ScreenWidget.extend({
		template: 'SeeAllOrdersScreenWidget',
		init: function(parent, options) {
			this._super(parent, options);
		},
		
		line_selects: function(event,$line,id){
			var self = this;
			var orders = this.pos.db.get_orders_by_id[id];
			this.$('.client-list .lowlight').removeClass('lowlight');
			if ( $line.hasClass('highlight') ){
				$line.removeClass('highlight');
				$line.addClass('lowlight');
			}else{
				this.$('.client-list .highlight').removeClass('highlight');
				$line.addClass('highlight');
				var y = event.pageY - $line.parent().offset().top;
				this.display_orders_detail('show',orders,y);
			}
		},
		
		display_orders_detail: function(visibility,order,clickpos){
			var self = this;
			var contents = this.$('.client-details-contents');
			var parent   = this.$('.orders-line ').parent();
			var scroll   = parent.scrollTop();
			var height   = contents.height();

			contents.off('click','.button.edit');
			contents.off('click','.button.save');
			contents.off('click','.button.undo');
			contents.on('click','.button.save',function(){ self.save_client_details(order); });
			contents.on('click','.button.undo',function(){ self.undo_client_details(order); });

			this.editing_client = false;
			this.uploaded_picture = null;

			if(visibility === 'show'){
				contents.empty();
				//Custom Code for passing the orderlines
				var orderline = [];
				for (var z = 0; z < order.lines.length; z++){
					orderline.push(self.pos.db.get_lines_by_id[order.lines[z]])
				}
				//Custom code ends
				contents.append($(QWeb.render('OrderDetails',{widget:this,order:order,orderline:orderline})));

				var new_height   = contents.height();
				if(!this.details_visible){
					if(clickpos < scroll + new_height + 20 ){
						parent.scrollTop( clickpos - 20 );
					}else{
						parent.scrollTop(parent.scrollTop() + new_height);
					}
				}else{
					parent.scrollTop(parent.scrollTop() - height + new_height);
				}
				this.details_visible = true;
			 } 
			 
			 else if (visibility === 'edit') {
			// Connect the keyboard to the edited field
			if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
				contents.off('click', '.detail');
				searchbox.off('click');
				contents.on('click', '.detail', function(ev){
					self.chrome.widget.keyboard.connect(ev.target);
					self.chrome.widget.keyboard.show();
				});
				searchbox.on('click', function() {
					self.chrome.widget.keyboard.connect($(this));
				});
			}

			this.editing_client = true;
			contents.empty();
			contents.append($(QWeb.render('ClientDetailsEdit',{widget:this})));
			//this.toggle_save_button();

			// Browsers attempt to scroll invisible input elements
			// into view (eg. when hidden behind keyboard). They don't
			// seem to take into account that some elements are not
			// scrollable.
			contents.find('input').blur(function() {
				setTimeout(function() {
					self.$('.window').scrollTop(0);
				}, 0);
			});

			contents.find('.image-uploader').on('change',function(event){
				self.load_image_file(event.target.files[0],function(res){
					if (res) {
						contents.find('.client-picture img, .client-picture .fa').remove();
						contents.find('.client-picture').append("<img src='"+res+"'>");
						contents.find('.detail.picture').remove();
						self.uploaded_picture = res;
					}
				});
			});
			} 
			 
			 
			 
			 else if (visibility === 'hide') {
				contents.empty();
				if( height > scroll ){
					contents.css({height:height+'px'});
					contents.animate({height:0},400,function(){
						contents.css({height:''});
					});
				}else{
					parent.scrollTop( parent.scrollTop() - height);
				}
				this.details_visible = false;
				//this.toggle_save_button();
			}
		},
		
		get_selected_partner: function() {
			var self = this;
			if (self.gui)
				return self.gui.get_current_screen_param('selected_partner_id');
			else
				return undefined;
		},
		
		render_list_orders: function(orders, search_input){
			var self = this;
			var selected_partner_id = this.get_selected_partner();
			var selected_client_orders = [];
			if (selected_partner_id != undefined) {
				for (var i = 0; i < orders.length; i++) {
					if (orders[i].partner_id[0] == selected_partner_id)
						selected_client_orders = selected_client_orders.concat(orders[i]);
				}
				orders = selected_client_orders;
			}
		   if (search_input != undefined && search_input != '') {
				var selected_search_orders = [];
				var search_text = search_input.toLowerCase()
				for (var i = 0; i < orders.length; i++) {
					if (orders[i].partner_id == '') {
						orders[i].partner_id = [0, '-'];
					}
					if (((orders[i].name.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].pos_reference.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].partner_id[1].toLowerCase()).indexOf(search_text) != -1)) {
						selected_search_orders = selected_search_orders.concat(orders[i]);
					}
				}
				orders = selected_search_orders;
			}
			
			
			var content = this.$el[0].querySelector('.orders-list-contents');
			content.innerHTML = "";
			var orders = orders;
			for(var i = 0, len = Math.min(orders.length,1000); i < len; i++){
				var order    = orders[i];
				var ordersline_html = QWeb.render('OrdersLine',{widget: this, order:orders[i], selected_partner_id: orders[i].partner_id[0]});
				var ordersline = document.createElement('tbody');
				ordersline.innerHTML = ordersline_html;
				ordersline = ordersline.childNodes[1];
				content.appendChild(ordersline);

			}
		},
		
		save_client_details: function(partner) {
			var self = this;
			
			var fields = {};
			this.$('.client-details-contents .detail').each(function(idx,el){
				fields[el.name] = el.value || false;
			});

			if (!fields.name) {
				this.gui.show_popup('error',_t('A Customer Name Is Required'));
				return;
			}
			
			if (this.uploaded_picture) {
				fields.image = this.uploaded_picture;
			}

			fields.id           = partner.id || false;
			fields.country_id   = fields.country_id || false;

			//new Model('res.partner').call('create_from_ui',[fields])
			rpc.query({
				model: 'res.partner',
				method: 'create_from_ui',
				args: [fields],
				
				}).then(function(partner_id){
				self.saved_client_details(partner_id);
			},function(err,event){
				event.preventDefault();
				self.gui.show_popup('error',{
					'title': _t('Error: Could not Save Changes'),
					'body': _t('Your Internet connection is probably down.'),
				});
			});
		},
		
		undo_client_details: function(partner) {
			this.display_orders_detail('hide');
			
		},
		
		saved_client_details: function(partner_id){
			var self = this;
			self.display_orders_detail('hide');
			alert('!! Customer Created Successfully !!')
			
		},
		
		should_auto_print: function() {
			return this.pos.config.iface_print_auto && !this.pos.get_order()._printed;
		},
		
		
		show: function(options) {
			var self = this;
			this._super(options);
			
			this.details_visible = false;
			
			var orders = self.pos.db.all_orders_list;
			var orders_lines = self.pos.db.all_orders_line_list;
			this.render_list_orders(orders, undefined);
			
			this.$('.back').click(function(){
				self.gui.show_screen('products');
			});

			
			//################################################################################################################
			this.$('.orders-list-contents').delegate('.orders-line-name', 'click', function(event) {
			   for(var ord = 0; ord < orders.length; ord++){
				   if (orders[ord]['id'] == $(this).data('id')){
					var orders1 = orders[ord];
				   }
			   }
			   var orderline = [];
			   for(var n=0; n < orders_lines.length; n++){
				   if (orders_lines[n]['order_id'][0] == $(this).data('id')){
					orderline.push(orders_lines[n])
				   }
			   }
				self.gui.show_popup('see_order_details_popup_widget', {'order': [orders1], 'orderline':orderline});
			});
			
			//################################################################################################################
			
			//################################################################################################################
			this.$('.orders-list-contents').delegate('.orders-line-ref', 'click', function(event) {
			   
			   
			   for(var ord = 0; ord < orders.length; ord++){
				   if (orders[ord]['id'] == $(this).data('id')){
					var orders1 = orders[ord];
				   }
			   }
			   //var orders1 = self.pos.db.get_orders_by_id[parseInt($(this).data('id'))];
				
				var orderline = [];
				for(var n=0; n < orders_lines.length; n++){
					if (orders_lines[n]['order_id'][0] == $(this).data('id')){
					 orderline.push(orders_lines[n])
					}
				}
				
				//Custom Code for passing the orderlines
				//var orderline = [];
				//for (var z = 0; z < orders1.lines.length; z++){
					//orderline.push(self.pos.db.get_lines_by_id[orders1.lines[z]])
				//}
				//Custom code ends
				
				self.gui.show_popup('see_order_details_popup_widget', {'order': [orders1], 'orderline':orderline});
			   
			   
			   // self.line_selects(event, $(this), parseInt($(this).data('id')));
			});
			
			//################################################################################################################
			
			//################################################################################################################
			this.$('.orders-list-contents').delegate('.orders-line-partner', 'click', function(event) {
			   
			   
			   for(var ord = 0; ord < orders.length; ord++){
				   if (orders[ord]['id'] == $(this).data('id')){
					var orders1 = orders[ord];
				   }
			   }
			   
			   //var orders1 = self.pos.db.get_orders_by_id[parseInt($(this).data('id'))];
				
				var orderline = [];
				for(var n=0; n < orders_lines.length; n++){
					if (orders_lines[n]['order_id'][0] == $(this).data('id')){
					 orderline.push(orders_lines[n])
					}
				}
				
				//Custom Code for passing the orderlines
				//var orderline = [];
				//for (var z = 0; z < orders1.lines.length; z++){
					//orderline.push(self.pos.db.get_lines_by_id[orders1.lines[z]])
				//}
				//Custom code ends
				
				self.gui.show_popup('see_order_details_popup_widget', {'order': [orders1], 'orderline':orderline});
			   
			   
			   // self.line_selects(event, $(this), parseInt($(this).data('id')));
			});
			
			//################################################################################################################
			
			//################################################################################################################
			this.$('.orders-list-contents').delegate('.orders-line-date', 'click', function(event) {
			   
			   for(var ord = 0; ord < orders.length; ord++){
				   if (orders[ord]['id'] == $(this).data('id')){
					var orders1 = orders[ord];
				   }
			   }
			   
			   //var orders1 = self.pos.db.get_orders_by_id[parseInt($(this).data('id'))];
				
				var orderline = [];
				for(var n=0; n < orders_lines.length; n++){
					if (orders_lines[n]['order_id'][0] == $(this).data('id')){
					 orderline.push(orders_lines[n])
					}
				}
				
				//Custom Code for passing the orderlines
				//var orderline = [];
				//for (var z = 0; z < orders1.lines.length; z++){
					//orderline.push(self.pos.db.get_lines_by_id[orders1.lines[z]])
				//}
				//Custom code ends
				
				self.gui.show_popup('see_order_details_popup_widget', {'order': [orders1], 'orderline':orderline});
			   
			   
			   // self.line_selects(event, $(this), parseInt($(this).data('id')));
			});
			
			//################################################################################################################
			
			//################################################################################################################
			this.$('.orders-list-contents').delegate('.orders-line-tot', 'click', function(event) {
			   
			   for(var ord = 0; ord < orders.length; ord++){
				   if (orders[ord]['id'] == $(this).data('id')){
					var orders1 = orders[ord];
				   }
			   }
			   
			   //var orders1 = self.pos.db.get_orders_by_id[parseInt($(this).data('id'))];
				
				var orderline = [];
				for(var n=0; n < orders_lines.length; n++){
					if (orders_lines[n]['order_id'][0] == $(this).data('id')){
					 orderline.push(orders_lines[n])
					}
				}
				
				
				//Custom Code for passing the orderlines
				//var orderline = [];
				//for (var z = 0; z < orders1.lines.length; z++){
					//orderline.push(self.pos.db.get_lines_by_id[orders1.lines[z]])
				//}
				//Custom code ends
				
				self.gui.show_popup('see_order_details_popup_widget', {'order': [orders1], 'orderline':orderline});
			   
			   
			   // self.line_selects(event, $(this), parseInt($(this).data('id')));
			});
			
			//################################################################################################################
			
			
			this.$('.orders-list-contents').delegate('.print-order', 'click', function(result) {
				var order_id = parseInt(this.id);
				var orderlines = [];
				var paymentlines = [];
				var discount = 0;
				var subtotal = 0;
				var tax = 0;
				var barcode;
				var date_order;
				var selectedOrder = null;
				for(var i = 0, len = Math.min(orders.length,1000); i < len; i++) {
					if (orders[i] && orders[i].id == order_id) {
						selectedOrder = orders[i];
					}
				}
				
				rpc.query({
					model: 'pos.order',
					method: 'print_pos_receipt',
					args: [order_id],
				
				}).then(function(output) {
					orderlines = output[0];
					paymentlines = output[2];
					discount = output[1];
					subtotal = output[4];
					tax = output[5];
					barcode = output[6];
					date_order = output[7];
					self.pos.set({'reprint_barcode' : barcode});
					self.gui.show_screen('ReceiptScreenWidgetNew',{
						'widget':self,
						'order': selectedOrder,
						'paymentlines': paymentlines,
						'orderlines': orderlines,
						'discount_total': discount,
						'change': output[3],
						'subtotal': subtotal,
						'tax': tax,
						'barcode':barcode,
						'date_order' : date_order
					});
					
				});
				return;
			});
			
			//Return Order
			this.$('.orders-list-contents').delegate('.return-order', 'click', function(result) {
				var order_id = parseInt(this.id);
				var selectedOrder = null;
				for(var i = 0, len = Math.min(orders.length,1000); i < len; i++) {
					if (orders[i] && orders[i].id == order_id) {
						selectedOrder = orders[i];
					}
				}
				
				var orderlines = [];
				var order_list = self.pos.db.all_orders_list;
				var order_line_data = self.pos.db.all_orders_line_list;

				selectedOrder.lines.forEach(function(line_id) {
					for(var y=0; y<order_line_data.length; y++){
						if(order_line_data[y]['id'] == line_id){
						   orderlines.push(order_line_data[y]); 
						}
					}
				});

				self.gui.show_popup('pos_return_order_popup_widget', { 'orderlines': orderlines, 'order': selectedOrder });
			});
			//End Return Order

			
			this.$('.orders-list-contents').delegate('.re-order', 'click', function(result) {				
				var order_id = parseInt(this.id);
				
				var selectedOrder = null;
				for(var i = 0, len = Math.min(orders.length,1000); i < len; i++) {
					if (orders[i] && orders[i].id == order_id) {
						selectedOrder = orders[i];
					}
				}
				
				var orderlines = [];
				var order_list = self.pos.db.all_orders_list;
				var order_line_data = self.pos.db.all_orders_line_list;

				selectedOrder.lines.forEach(function(line_id) {
					for(var y=0; y<order_line_data.length; y++){
						if(order_line_data[y]['id'] == line_id){
						   orderlines.push(order_line_data[y]); 
						}
					}
					
				});

				self.gui.show_popup('pos_re_order_popup_widget', { 'orderlines': orderlines, 'order': selectedOrder });
			});
			//this code is for Search Orders
			this.$('.search-order input').keyup(function() {
				self.render_list_orders(orders, this.value);
			});
			
			this.$('.new-customer').click(function(){
				self.display_orders_detail('edit',{
					'country_id': self.pos.company.country_id,
				});
			});
			
			
			
		},
		//
			   

	});
	gui.define_screen({
		name: 'see_all_orders_screen_widget',
		widget: SeeAllOrdersScreenWidget
	});

	// End SeeAllOrdersScreenWidget
	
	
	//==================================================================================================
	
	var SeeOrderDetailsPopupWidget = popups.extend({
		template: 'SeeOrderDetailsPopupWidget',
		
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		show: function(options) {
			var self = this;
			options = options || {};
			this._super(options);
			this.order = options.order || [];
			this.orderline = options.orderline || [];
		},
		
		events: {
			'click .button.cancel': 'click_cancel',
		},
		
		renderElement: function() {
			var self = this;
			this._super();
		},

	});

	
	gui.define_popup({
		name: 'see_order_details_popup_widget',
		widget: SeeOrderDetailsPopupWidget
	});
	


	// PosReOrderPopupWidget Popup start

	var PosReOrderPopupWidget = popups.extend({
		template: 'PosReOrderPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		//
		show: function(options) {
			options = options || {};
			var self = this;
			this._super(options);
			this.orderlines = options.orderlines || [];

		},
		//
		renderElement: function() {
			var self = this;
			this._super();
			var selectedOrder = this.pos.get_order();
			var orderlines = self.options.orderlines;
			var order = self.options.order;

			// When you click on apply button, Customer is selected automatically in that order
			var partner_id = false
			var client = false
			if (order && order.partner_id != null)
				partner_id = order.partner_id[0];
				client = this.pos.db.get_partner_by_id(partner_id);
				
			var reorder_products = {};

			this.$('#apply_reorder').click(function() {
				var entered_code = $("#entered_item_qty").val();
				var list_of_qty = $('.entered_item_qty');

				$.each(list_of_qty, function(index, value) {
					var entered_item_qty = $(value).find('input');
					var qty_id = parseFloat(entered_item_qty.attr('qty-id'));
					var line_id = parseFloat(entered_item_qty.attr('line-id'));
					var entered_qty = parseFloat(entered_item_qty.val());

					reorder_products[line_id] = entered_qty;
				});
				//return reorder_products;


				Object.keys(reorder_products).forEach(function(line_id) {
					var orders_lines = self.pos.db.all_orders_line_list;
					var orderline = [];
					   for(var n=0; n < orders_lines.length; n++){
						   if (orders_lines[n]['id'] == line_id){
								if(reorder_products[line_id]>0)
								{
									var product = self.pos.db.get_product_by_id(orders_lines[n].product_id[0]);
									selectedOrder.add_product(product, {
										quantity: parseFloat(reorder_products[line_id]),
										price: orders_lines[n].price_unit,
										discount: orders_lines[n].discount
									});
									selectedOrder.selected_orderline.original_line_id = orders_lines[n].id;
								}
						   }
					   }
				});
				selectedOrder.set_client(client);
				self.pos.set_order(selectedOrder);
				self.gui.show_screen('products');
			});
		},

	});
	gui.define_popup({
		name: 'pos_re_order_popup_widget',
		widget: PosReOrderPopupWidget
	});
	// End PosReOrderPopupWidget Popup start

	//Barcode Pop up start
	var PosBarcodePopupWidget = popups.extend({
		template: 'PosBarcodePopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		show: function(options) {
			options = options || {};
			var self = this;
			this._super(options);
		},
		
		events: {
			'click .button.cancel': 'click_cancel',
		},

		renderElement: function() {
			var self = this;
			this._super();
			var self = this;   
			var selectedOrder = this.pos.get_order();
			var orderlines = self.options.orderlines;
			var order = self.options.order;
			var return_products = {};
			var exact_return_qty = {};
			var exact_entered_qty = {};
			var orders = self.pos.db.all_orders_list;
			
			this.$('#apply_barcode_return_order').click(function() {
				var entered_barcode = $("#entered_item_barcode").val();
				var order_id = parseInt(this.id);
				var selectedOrder = null;
				for(var i = 0, len = Math.min(orders.length,1000); i < len; i++) {
					if (orders[i] && orders[i].barcode == entered_barcode) {
						selectedOrder = orders[i];
					}
				}
				if(selectedOrder){
					var orderlines = [];
					var order_list = self.pos.db.all_orders_list;
					var order_line_data = self.pos.db.all_orders_line_list;
					selectedOrder.lines.forEach(function(line_id) {
					for(var y=0; y<order_line_data.length; y++){
						if(order_line_data[y]['id'] == line_id){
						   orderlines.push(order_line_data[y]); 
						}
					}
					});
					self.gui.show_popup('pos_return_order_popup_widget', { 'orderlines': orderlines, 'order': selectedOrder });
				}
				else{
					self.pos.gui.show_popup('error', {
						'title': _t('Invalid Barcode'),
						'body': _t("The Barcode You are Entering is Invalid"),
					});
				}
			});
		},

	});

 	//Barcode Pop up end  

	// Popup start
	var PosReturnOrderPopupWidget = popups.extend({
		template: 'PosReturnOrderPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		show: function(options) {
			options = options || {};
			var self = this;
			this._super(options);
			this.orderlines = options.orderlines || [];

		},

		renderElement: function() {
			var self = this;
			this._super();
			var selectedOrder = this.pos.get_order();
			var orderlines = self.options.orderlines;
			var order = self.options.order;

			// When you click on apply button, Customer is selected automatically in that order 
			var partner_id = false
			var client = false
			if (order && order.partner_id != null)
				partner_id = order.partner_id[0];
				client = this.pos.db.get_partner_by_id(partner_id);
				
			var return_products = {};
			var exact_return_qty = {};
			var exact_entered_qty = {};

			this.$('#apply_return_order').click(function() {
				var entered_code = $("#entered_item_qty").val();
				var list_of_qty = $('.entered_item_qty');

				$.each(list_of_qty, function(index, value) {
					var entered_item_qty = $(value).find('input');
					var qty_id = parseFloat(entered_item_qty.attr('qty-id'));
					var returned_qty = parseFloat(entered_item_qty.attr('return-qty'));
					var line_id = parseFloat(entered_item_qty.attr('line-id'));
					var entered_qty = parseFloat(entered_item_qty.val());
					exact_return_qty = qty_id;
					exact_entered_qty = entered_qty || 0;
					let remained = qty_id - returned_qty;
					if(remained < entered_qty){
						alert("Cannot Return More quantity than purchased");
						return;
					}
					else{
						if(!exact_entered_qty){
						return;
						}
						else if (exact_return_qty >= exact_entered_qty){
						  return_products[line_id] = entered_qty;
						}
						else{
							alert("Cannot Return More quantity than purchased");
							return;
						}
					}

				});

				Object.keys(return_products).forEach(function(line_id) {
										
					var orders_lines = self.pos.db.all_orders_line_list;
					var orderline = [];
					   for(var n=0; n < orders_lines.length; n++){
						   if (orders_lines[n]['id'] == line_id){
							var product = self.pos.db.get_product_by_id(orders_lines[n].product_id[0]);
							selectedOrder.add_product(product, {
								quantity: - parseFloat(return_products[line_id]),
								price: orders_lines[n].price_unit,
								discount: orders_lines[n].discount
							});
							selectedOrder.set_return_order_ref(orders_lines[n].order_id[0]);
							selectedOrder.selected_orderline.set_original_line_id(orders_lines[n].id);
						   }
					   }
					
				});
				selectedOrder.set_client(client);
				self.pos.set_order(selectedOrder);
				self.gui.show_screen('products');

			});

		},

	});
	gui.define_popup({
		name: 'pos_return_order_popup_widget',
		widget: PosReturnOrderPopupWidget
	});
	
	gui.define_popup({
		name: 'pos_barcode_popup_widget',
		widget: PosBarcodePopupWidget
	});

	// End Popup start


	// Start SeeAllOrdersButtonWidget
	var SeeAllOrdersButtonWidget = screens.ActionButtonWidget.extend({
		template: 'SeeAllOrdersButtonWidget',
		button_click: function() {
			var self = this;
			this.gui.show_screen('see_all_orders_screen_widget', {});
		},

	});

	screens.define_action_button({
		'name': 'See All Orders Button Widget',
		'widget': SeeAllOrdersButtonWidget,
		'condition': function() {
			return true;
		},
	});
	// End SeeAllOrdersButtonWidget

	// Start ClientListScreenWidget
	gui.Gui.prototype.screen_classes.filter(function(el) { return el.name == 'clientlist'})[0].widget.include({
		show: function(){
			this._super();
			var self = this;
			this.$('.view-orders').click(function(){
				self.gui.show_screen('see_all_orders_screen_widget', {});
			});
			$('.selected-client-orders').on("click", function() {
				self.gui.show_screen('see_all_orders_screen_widget', {
					'selected_partner_id': this.id
				});
			});
		},
	});


	// Start CreateSalesOrderButtonWidget
	
	var CreateSalesOrderButtonWidget = screens.ActionButtonWidget.extend({
		template: 'CreateSalesOrderButtonWidget',
		
		renderElement: function(){
			var self = this;
			this._super();
			this.$el.click(function(){
				var order = self.pos.get('selectedOrder');
				var orderlines = order.orderlines;
				var partner_id = false
				if (order.get_client() != null)
					partner_id = order.get_client();

				if (!partner_id) {
					self.gui.show_popup('error', {
						'title': _t('Unknown customer'),
						'body': _t('You cannot Create Sales Order. Select customer first.'),
					});
					return;
				}
				if (orderlines.length === 0) {
					self.gui.show_popup('error', {
						'title': _t('Empty Order'),
						'body': _t('There must be at least one product in your order before Create Sales Order.'),
					});
					return;
				}
				
				var pos_product_list = [];
				for (var i = 0; i < orderlines.length; i++) {
					var product_items = {
						'id': orderlines.models[i].product.id,
						'quantity': orderlines.models[i].quantity,
						'uom_id': orderlines.models[i].product.uom_id[0],
						'price': orderlines.models[i].price
					};
					pos_product_list.push({'product': product_items });
				}
				
				rpc.query({
					model: 'pos.create.sales.order',
					method: 'create_sales_order',
					args: [partner_id, partner_id.id, pos_product_list],
					}).then(function(output) {
					self.pos.delete_current_order();
					alert('Sales Order Created !!!!');	
					self.gui.show_screen('products');
				});
			});
			//self.button_click();
		},
			button_click: function(){},
			highlight: function(highlight){
			this.$el.toggleClass('highlight',!!highlight);
		},
		
		
		
	});

	screens.define_action_button({
		'name': 'Create Sales Order Button Widget',
		'widget': CreateSalesOrderButtonWidget,
		'condition': function() {
			return true;
		},
	});
	// End CreateSalesOrderButtonWidget	
	


	// Start pos_invoice_auto_check
	screens.PaymentScreenWidget.include({
		// Include auto_check_invoice boolean condition in watch_order_changes method
		watch_order_changes: function() {
			var self = this;
			var order = this.pos.get_order();
			if(this.old_order){
				this.old_order.stop_electronic_payment();
				this.old_order.unbind(null, null, this);
				this.old_order.paymentlines.unbind(null, null, this);
			}			
			if(this.pos.config.auto_check_invoice && this.pos.config.module_account) // Condition True/False
			{
				var pos_order=this.pos.get_order();
				pos_order.set_to_invoice(true);
				this.$('.js_invoice').addClass('highlight');
			}
			
			if (!order) {
				return;
			}
			this.order_changes()
			order.bind('all',function(){
				self.order_changes();
			});
			order.paymentlines.bind('all', self.order_changes.bind(self));
			this.old_order = order;
		},

	    finalize_validation: function() {
	        var self = this;
	        var order = this.pos.get_order();

	        if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) { 

	                this.pos.proxy.open_cashbox();
	        }

	        order.initialize_validation_date();
	        order.finalized = true;

	        if (order.is_to_invoice()) {
	            if(order.get_total_with_tax()>0){
		            var invoiced = this.pos.push_and_invoice_order(order);
		            this.invoicing = true;

		            invoiced.catch(this._handleFailedPushForInvoice.bind(this, order, false));

		            invoiced.then(function (server_ids) {
		                self.invoicing = false;
		                var post_push_promise = [];
		                post_push_promise = self.post_push_order_resolve(order, server_ids);
		                post_push_promise.then(function () {
		                        self.gui.show_screen('receipt');
		                }).catch(function (error) {
		                    self.gui.show_screen('receipt');
		                    if (error) {
		                        self.gui.show_popup('error',{
		                            'title': "Error: no internet connection",
		                            'body':  error,
		                        });
		                    }
		                });
		            });               
	            }
	            else if(this.pos.config.credit_note != "not_create_note"){
	                var invoiced = this.pos.push_and_invoice_order(order);
		            this.invoicing = true;

		            invoiced.catch(this._handleFailedPushForInvoice.bind(this, order, false));

		            invoiced.then(function (server_ids) {
		                self.invoicing = false;
		                var post_push_promise = [];
		                post_push_promise = self.post_push_order_resolve(order, server_ids);
		                post_push_promise.then(function () {
		                        self.gui.show_screen('receipt');
		                }).catch(function (error) {
		                    self.gui.show_screen('receipt');
		                    if (error) {
		                        self.gui.show_popup('error',{
		                            'title': "Error: no internet connection",
		                            'body':  error,
		                        });
		                    }
		                });
		            });
	            }else{
	            var ordered = this.pos.push_order(order);
	            if (order.wait_for_push_order()){
	                var server_ids = [];
	                ordered.then(function (ids) {
	                  server_ids = ids;
	                }).finally(function() {
	                    var post_push_promise = [];
	                    post_push_promise = self.post_push_order_resolve(order, server_ids);
	                    post_push_promise.then(function () {
	                            self.gui.show_screen('receipt');
	                        }).catch(function (error) {
	                          self.gui.show_screen('receipt');
	                          if (error) {
	                              self.gui.show_popup('error',{
	                                  'title': "Error: no internet connection",
	                                  'body':  error,
	                              });
	                          }
	                        });
	                  });
	            }
	            else {
	              self.gui.show_screen('receipt');
	            }
	            }

	        } else {
	            var ordered = this.pos.push_order(order);
	            if (order.wait_for_push_order()){
	                var server_ids = [];
	                ordered.then(function (ids) {
	                  server_ids = ids;
	                }).finally(function() {
	                    var post_push_promise = [];
	                    post_push_promise = self.post_push_order_resolve(order, server_ids);
	                    post_push_promise.then(function () {
	                            self.gui.show_screen('receipt');
	                        }).catch(function (error) {
	                          self.gui.show_screen('receipt');
	                          if (error) {
	                              self.gui.show_popup('error',{
	                                  'title': "Error: no internet connection",
	                                  'body':  error,
	                              });
	                          }
	                        });
	                  });
	            }
	            else {
	              self.gui.show_screen('receipt');
	            }
	        }

	    },		
	
	});
	// End pos_invoice_auto_check	
	
	var PosBagWidget = screens.ActionButtonWidget.extend({
		template: 'PosBagWidget',
		renderElement: function(){
			var self = this;
			this._super();
			
			this.$el.click(function(){
				var selectedOrder = self.pos.get_order();
				var category = self.pos.config.pos_bag_category_id;
				var categ = self.pos.db.get_product_by_category(category[0])
				
				var products = self.pos.db.get_product_by_category(category[0])[0];
					
				//if (product.length == 1) {   
				if (self.pos.db.get_product_by_category(self.pos.config.pos_bag_category_id[0]).length == 1) { 
					selectedOrder.add_product(products);
					self.pos.set_order(selectedOrder);
					

					self.gui.show_screen('products');
				}else{
					var orderlines = self.pos.db.get_product_by_category(category[0]);
					for(var i = 0 ; i<orderlines.length ; i++){
						 orderlines[i]['image_url'] = window.location.origin + '/web/binary/image?model=product.product&field=image_medium&id=' + orderlines[i].id;
					 }
					self.gui.show_popup('pos_bag_popup_widget', {'orderlines': orderlines});
				}
				//self.gui.show_popup('pos_bag_popup_widget', {'orderlines': orderlines});

			});
		},
			button_click: function(){},
			highlight: function(highlight){
			this.$el.toggleClass('highlight',!!highlight);
		},  
	});

	screens.define_action_button({
		'name': 'Pos Bag Widget',
		'widget': PosBagWidget,
		'condition': function() {
			return true;
		},
	});

	// PosBagPopupWidget Popup start

	var PosBagPopupWidget = popups.extend({
		template: 'PosBagPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		events: {
			'click .product.bag-category': 'click_on_bag_product',
			'click .button.cancel': 'click_cancel',
		},
		
		click_on_bag_product: function(event) {
			var self = this;
			var bag_id = parseInt(event.currentTarget.dataset['productId'])
		   
			//var bag_id = parseInt($(this).parent().data('id'));
			self.pos.get_order().add_product(self.pos.db.product_by_id[bag_id]);
			self.pos.gui.close_popup();
		},
	});
	gui.define_popup({
		name: 'pos_bag_popup_widget',
		widget: PosBagPopupWidget
	});

	// End Popup start
	
	// Popup start

	var SelectExistingPopupWidget = popups.extend({
		template: 'SelectExistingPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		//
		renderElement: function() {
			var self = this;
			this._super();
			var order = this.pos.get_order();
			var selectedOrder = self.pos.get('selectedOrder');
			this.$('#apply_coupon_code').click(function() {
				var entered_code = $("#existing_coupon_code").val();
				var partner_id = false;
				var coupon_applied = true;
				var used = false;
				if (order.get_client() != null)
					partner_id = order.get_client();
				rpc.query({
					model: 'pos.gift.coupon',
					method: 'existing_coupon',
					args: [partner_id, entered_code],
				
				}).then(function(output) {
					var orderlines = order.orderlines;
					// Popup Occurs when no Customer is selected...
					if (!partner_id) {
						self.gui.show_popup('error', {
							'title': _t('Unknown customer'),
							'body': _t('You cannot use Coupons/Gift Voucher. Select customer first.'),
						});
						return;
					}

					// Popup Occurs when not a single product in orderline...
					if (orderlines.length === 0) {
						self.gui.show_popup('error', {
							'title': _t('Empty Order'),
							'body': _t('There must be at least one product in your order before it can be apply for voucher code.'),
						});
						return;
					}

					// Goes inside when atleast product in orderline...     
					if (orderlines.length) {                    
						if (output == true) {
							var selectedOrder = self.pos.get('selectedOrder');
							// selectedOrder.coupon_id = entered_code;
							var total_amount = selectedOrder.get_total_without_tax();
							rpc.query({
								model: 'pos.gift.coupon',
								method: 'search_coupon',
								args: [partner_id, entered_code],
							
							}).then(function(output) {
								if(self.pos.pos_coupons_setting.length == 0){
									self.gui.show_popup('error', {
										'title': _t('Error'),
										'body': _t('There is no gift coupon.'),
									});
									return;
								}
								var amount = output[1];
								used = output[2];
								var coupon_count = output[3];
								var coupon_times = output[4];
								var expiry = output[5];
								var partner_true = output[6];
								var gift_partner_id = output[7];
								var amount_type = output[8]
								var exp_dt_true = output[9];
								var max_amount = output[10];
								var apply_coupon_on = output[11];
								var current_date = new Date().toUTCString();
								var d = new Date();
								var month = '0' + (d.getMonth() + 1);
								var day = '0' + d.getDate();
								var year = d.getFullYear();
								var product_id = self.pos.pos_coupons_setting[0].product_id[0];
								
								expiry = new Date(expiry)
								var date = new Date(year,month,day);
								if(amount_type == 'per'){
									if(apply_coupon_on == 'taxed')
									{
										total_amount = self.pos.get_order().get_total_with_tax();
									}
									amount = (total_amount * output[1])/100
								}else{
									amount = amount
								}

								for (var i = 0; i < orderlines.models.length; i++) {
									if (orderlines.models[i].product.id == product_id){
										coupon_applied = false;
									}
								}
								if (exp_dt_true && d > expiry){
									self.gui.show_popup('error', {
										'title': _t('Expired'),
										'body': _t("The Coupon You are trying to apply is Expired"),
									});	
								}
								
								else if (coupon_applied == false) {
									self.gui.show_popup('error', {
										'title': _t('Coupon Already Applied'),
										'body': _t("The Coupon You are trying to apply is already applied in the OrderLines"),
									});
								}
								
								else if (coupon_count > coupon_times){ // maximum limit
									self.gui.show_popup('error', {
										'title': _t('Maximum Limit Exceeded !!!'),
										'body': _t("You already exceed the maximum number of limit for this Coupon code"),
									});
								}
								
								else if (partner_true == true && gift_partner_id != partner_id.id){
									self.gui.show_popup('error', {
										'title': _t('Invalid Customer !!!'),
										'body': _t("This Gift Coupon is not applicable for this Customer"),
									});
								}

								else if(order.get_total_with_tax() < amount){
									self.gui.show_popup('error', {
										'title': _t('Invalid Amount !!!'),
										'body': _t("Coupon Amount is greater than order amount"),
									});
								}
								
								else { // if coupon is not used
									if(max_amount >= amount){
										var update_coupon_amount = max_amount - amount
										order.coup_maxamount = update_coupon_amount;

										var total_val = total_amount - amount;
										var product_id = self.pos.pos_coupons_setting[0].product_id[0];
										var product = self.pos.db.get_product_by_id(product_id);
										var selectedOrder = self.pos.get('selectedOrder');
										selectedOrder.add_product(product, {
											price: -amount,
											quantity: 1.0,
										});
										order.coupon_id = output[0];
									}else{
										self.gui.show_popup('error', {
											'title': _t('Maximum Limit Exceeded !!!'),
											'body': _t("You already exceed the maximum limit for this Coupon code."),
										});
									}
									
								}

							});
							self.gui.show_screen('products');
						} else { //Invalid Coupon Code
							self.gui.show_popup('error', {
								'title': _t('Invalid Code !!!'),
								'body': _t("Voucher Code Entered by you is Invalid. Enter Valid Code..."),
							});
						}
					} else { // Popup Shows, you can't use more than one Voucher Code in single order.
						self.gui.show_popup('error', {
							'title': _t('Already Used !!!'),
							'body': _t("You have already use this Coupon code, at a time you can use one coupon in a Single Order"),
						});
					}


				});
			});


		},

	});

	gui.define_popup({
		name: 'select_existing_popup_widget',
		widget: SelectExistingPopupWidget
	});

	var CouponConfigPopupWidget = popups.extend({
		template: 'CouponConfigPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		show: function(options) {
			var self = this;
			this._super(options);

		},

		renderElement: function() {
			var self = this;
			this._super();
			var order = this.pos.get_order();
			var selectedOrder = self.pos.get('selectedOrder');
			this.$('.creat_coupon').click(function() {
				self.gui.close_popup();
				$('input[type="date"]').datepicker();
				self.gui.show_popup('create_coupon_popup_widget',{});
			})
			this.$('.select_coupon').click(function() {
				self.gui.close_popup();
				self.gui.show_popup('select_existing_popup_widget', {});
			})
		}
	})

	gui.define_popup({
		name: 'open_coupon_popup_widget',
		widget: CouponConfigPopupWidget
	});

	var CreateCouponPopupWidget = popups.extend({
		template: 'CreateCouponPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},

		renderElement: function() {
			var self = this;
			this._super();
			var order = this.pos.get_order();
			var selectedOrder = self.pos.get('selectedOrder');
			$('#coupon_exp_dt').hide();
			$('#coupon_customer').hide();
			$('#alertcustomer').hide();
			$('#alertamount').hide();
			$('#alertdate').hide();
			$('#alertamt').hide();
			$('#alertamtmax').hide();

			this.$('#coupon_cust_box').click(function() {
				if ($('#coupon_cust_box').is(':checked')) {
					$('#coupon_customer').show();
				} else {
					$('#coupon_customer').hide();
				}
			});

			this.$('#coupon_expdt_box').click(function() {
				if ($('#coupon_expdt_box').is(':checked')) {
					$('#coupon_exp_dt').show();
				} else {
					$('#coupon_exp_dt').hide();
				}
			});

			this.$('#create_coupon').click(function(ev) {
				
				if(self.pos.pos_coupons_setting.length < 1){
					ev.stopPropagation();
					ev.preventDefault(); 
					ev.stopImmediatePropagation();
					self.gui.show_popup('custom_error', {
						'title': _t('No gift coupon configuration'),
						'body': _t('Please configure product gift coupons .'),
					});
					return;
				}
				else{
					var c_name = $("#coupon_name").val();
					var c_limit = $("#coupon_limit").val();
					var c_amount = $("#coupon_amount").val();
					var c_am_type = $("#coup_amount_type").val();
					var c_customer = $("#coupon_customer").val();
					var c_issue_dt = $("#coupon_issue_dt").val();
					var c_exp_dt = $("#coupon_exp_dt").val();
					var c_max_amount = $("#coupon_max_amount").val();
					var c_expdt_box = $('#coupon_expdt_box').is(':checked');
					var c_cust_box = $("#coupon_cust_box").is(':checked');

					var exp_dt = new Date(c_exp_dt)
					var issu_dt = new Date(c_issue_dt)
					var max_exp_dt = false;
					if(self.pos.pos_coupons_setting[0].max_exp_date)
					{
						var max_exp_dt = new Date(self.pos.pos_coupons_setting[0].max_exp_date)
					}
					var max_coupan_value = self.pos.pos_coupons_setting[0].max_coupan_value
					var min_coupan_value = self.pos.pos_coupons_setting[0].min_coupan_value

					if(!(c_name && c_issue_dt)){
						self.gui.show_popup('create_coupon_popup_widget',{});
						$('#alertcustomer').show()
					}
					else if((c_max_amount) && (c_max_amount > max_coupan_value)){
						self.gui.show_popup('create_coupon_popup_widget',{});
						$('#alertamtmax').show()
					}
					else if(!(c_amount)){
						self.gui.show_popup('create_coupon_popup_widget',{});
						$('#alertamt').show()
					}
					else if((min_coupan_value > parseInt(c_amount) || parseInt(c_amount) > max_coupan_value) && (c_am_type != 'Percentage')){
						self.gui.show_popup('create_coupon_popup_widget',{});
						$('#alertamount').show()
					}
					else if(c_expdt_box && !max_exp_dt)
					{
						self.gui.show_popup('create_coupon_popup_widget',{});
						$('#alertdate').text('Please add expiry date in coupon configuration first.');
						$('#alertdate').show();
					}
					else if(max_exp_dt)
					{
						if(max_exp_dt.getTime() < issu_dt.getTime()){
							self.gui.show_popup('create_coupon_popup_widget',{});
							$('#alertdate').show()
						}
						else if(exp_dt.getTime() > max_exp_dt.getTime()){
							self.gui.show_popup('create_coupon_popup_widget',{});
							$('#alertdate').show()
						}
						else{
							self.gui.close_popup();
							var dict ={
								'c_name':c_name,
								'c_limit': c_limit,
								'c_amount':c_amount,
								'c_am_type':c_am_type,
								'c_customer':c_customer,
								'c_issue_dt':c_issue_dt,
								'c_exp_dt':c_exp_dt,
								'user_id':self.pos.get_cashier(),
								'coupon_max_amount':c_max_amount,
								'c_expdt_box':c_expdt_box,
								'c_cust_box':c_cust_box,
							}
							rpc.query({
								model: 'pos.gift.coupon',
								method: 'create_coupon_from_ui',
								args: [dict],
							}).then(function(output) {
								self.gui.close_popup();
								self.gui.show_popup('After_create_coupon_popup_widget',output)
							})
						} 
					}
					else{
						self.gui.close_popup();
						var dict ={
							'c_name':c_name,
							'c_limit': c_limit,
							'c_amount':c_amount,
							'c_am_type':c_am_type,
							'c_customer':c_customer,
							'c_issue_dt':c_issue_dt,
							'c_exp_dt':c_exp_dt,
							'user_id':self.pos.get_cashier(),
							'coupon_max_amount':c_max_amount,
							'c_expdt_box':c_expdt_box,
							'c_cust_box':c_cust_box,
						}
						rpc.query({
							model: 'pos.gift.coupon',
							method: 'create_coupon_from_ui',
							args: [dict],
						}).then(function(output) {
							self.gui.close_popup();
							self.gui.show_popup('After_create_coupon_popup_widget',output)
						})
					}
				}

				
			});
		},
	})

	gui.define_popup({
		name: 'create_coupon_popup_widget',
		widget: CreateCouponPopupWidget
	});

	var AfterCreateCouponPopup = screens.ScreenWidget.extend({
		template: 'AfterCreateCouponPopup',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
			this.coupon_data = {};
		},
		show: function(options) {
			var self = this;
			this._super(options);
			self.render_coupon(options)

			$(".close").click(function(){
				self.gui.close_popup();
			}) 
		},

		events: {
			"click .print_coupon": "print_gift_coupon",
		},

		print_gift_coupon: function (ev) {
			var self = this;
			ev.stopPropagation();
			ev.preventDefault();   
			self.pos.set('coupon_print_data', this.coupon_data);
			self.gui.show_screen('coupon_print',{'data' : this.coupon_data});
		},

		render_coupon: function(options) {
			var self = this;
			var partner_id = false;
			var order = this.pos.get_order();

			var coupon_datails = false;
			if (order.get_client() != null){
				partner_id = order.get_client();
			}

			coupon_datails =  options;
			var coup_id = options[0];
			var coup_name = options[1];
			var coup_exp_dt = false;
			if(options[2])
			{
				coup_exp_dt = options[2].split(" ")[0];
			}
			var coup_issue_dt = options[4];
			coup_issue_dt = coup_issue_dt.split(" ")[0];

			var coup_amount = options[3];
			var coup_img = options[7];
			var am_type = options[6];
			var coup_code = options[5];
			
			var coup_dict = {coup_id,coup_name,coup_exp_dt,coup_issue_dt,coup_amount,coup_img,am_type,coup_code}
			if(coup_dict){
				this.coupon_data = coup_dict
			}
		},

		print_web: function() {
			window.print();
		},

		renderElement: function() {
			var self = this;
			this._super();
		},
		
	})

	gui.define_popup({
		name: 'After_create_coupon_popup_widget',
		widget: AfterCreateCouponPopup
	});

	// End Popup start

	var PrintCouponButtonScreen = screens.ScreenWidget.extend({
		template: 'PrintCouponButtonScreen',
		
		init: function(parent,options){
			var self = this;
			this._super(parent,options);
		},
		

		get_coupon: function(){
			return this.gui.get_current_screen_param('data');
		},

		show: function(options){
			this._super();
			var self = this;
			this.coupon_render();
		},

		coupon_render_env: function() {
			// var order = this.pos.get_order();
			var data = this.pos.get('coupon_print_data');
			return {
				widget: this,
				pos: this.pos,
				summery: this.get_coupon(),
			};
		},

		coupon_render: function(){
			this.$('.print-coupon-receipt').html(QWeb.render('CouponPrint',this.coupon_render_env()));
		},
		print_xml_coupon: function() {
			var receipt = QWeb.render('CouponPrint', this.coupon_render_env());
			this.pos.proxy.print_receipt(receipt);
		},
		print_web_payment: function() {
			window.print();
		},
		print_coupon: function() {
			var self = this;
			if (!this.pos.config.iface_print_via_proxy) { 

				this.print_web_payment();
			} else {    
				this.print_xml_coupon();
			}
		},


		renderElement: function() {
			var self = this;
			this._super();
			
			this.$('.next').click(function(){
				// location.reload();
				self.gui.back();
			});
			
			this.$('.button.print-coupon').click(function(){
				self.print_coupon();
			});
			
		},

	});
	gui.define_screen({name:'coupon_print', widget: PrintCouponButtonScreen});

	var GiftButtonWidget = screens.ActionButtonWidget.extend({
		template: 'GiftButtonWidget',
		button_click: function() {
			var order = this.pos.get_order();
			var self = this;
			this.gui.show_popup('open_coupon_popup_widget', {});
		},
	});

	screens.define_action_button({
		'name': 'POS Coupens Gift Voucher',
		'widget': GiftButtonWidget,
		'condition': function() {
			return true;
		},
	});
	// End GiftPopupWidget start
	// End GiftPopupWidget start	



	// Total Items Count in exports.OrderWidget = Backbone.Model.extend ...
	screens.OrderWidget.include({
		update_summary: function(){
			this._super();
			var order = this.pos.get_order();
			if (!order.get_orderlines().length) {
				return;
			}
			var total_items    = order ? order.get_total_items() : 0;
			this.el.querySelector('.item_count .val').textContent = total_items.toFixed(2);
		},
	});

	// SeeAllSaleOrdersScreenWidget start

	var SeeAllSaleOrdersScreenWidget = screens.ScreenWidget.extend({
		template: 'SeeAllSaleOrdersScreenWidget',
		init: function(parent, options) {
			this._super(parent, options);
			//this.options = {};
		},

		render_list_orders: function(orders, search_input){
			var self = this;

			if(orders == undefined)
			{
				orders = self.pos.get('all_sale_orders_list');
			}			
			if(search_input != undefined && search_input != '') {
				var selected_search_orders = [];
				var search_text = search_input.toLowerCase()
				for (var i = 0; i < orders.length; i++) {
					if (orders[i].partner_id == '') {
						orders[i].partner_id = [0, '-'];
					}
					if (((orders[i].name.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].name.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].partner_id[1].toLowerCase()).indexOf(search_text) != -1)) {
						selected_search_orders = selected_search_orders.concat(orders[i]);
					}
				}
				orders = selected_search_orders;
			}
			
			
			var content = this.$el[0].querySelector('.client-list-contents');
			content.innerHTML = "";
			var orders = orders;
			for(var i = 0, len = Math.min(orders.length,1000); i < len; i++){
				var order    = orders[i];
				var ordersline_html = QWeb.render('SaleOrdersLine',{widget: this, order:orders[i]});
				var ordersline = document.createElement('tbody');
				ordersline.innerHTML = ordersline_html;
				ordersline = ordersline.childNodes[1];
				content.appendChild(ordersline);
			}
		},

		get_orders_fields: function () {
			var fields = ['name','partner_id','user_id','amount_untaxed','order_line','amount_tax','amount_total','company_id','date_order'];
			return fields;
		},


		get_sale_orders: function () {
			var self = this;
			var fields = self.get_orders_fields();
			var load_orders = [];
			var load_orders_line = [];
			var order_ids = [];
			rpc.query({
					model: 'sale.order',
					method: 'search_read',
					args: [null,fields],
			}, {async: false}).then(function(output) {
				load_orders = output;
				load_orders.forEach(function(order) {
					order_ids.push(order.id)
				});
				var fields_domain = [['order_id','in',order_ids]];
				rpc.query({
					model: 'sale.order.line',
					method: 'search_read',
					args: [fields_domain],
				}, {async: false}).then(function(output1) {
					self.pos.db.all_sale_orders_line_list = output1;
					self.pos.db.all_sale_orders_list = load_orders
					load_orders_line = output1;
					self.pos.all_sale_orders_list= load_orders;
					self.pos.all_sale_orders_line_list =  output1;
					self.render_list_orders(load_orders, undefined);
					return [load_orders,load_orders_line]
				});
			}); 
			
		},


		display_details: function (o_id) {
			var self = this;
			var orders =  self.pos.all_sale_orders_list;
			var orders_lines =  self.pos.all_sale_orders_line_list;
			var orders1 = [];
			for(var ord = 0; ord < orders.length; ord++){
				if (orders[ord]['id'] == o_id){
					 orders1 = orders[ord];
				}
			}
			var orderline = [];
			for(var n=0; n < orders_lines.length; n++){
				if (orders_lines[n]['order_id'][0] ==o_id){
					orderline.push(orders_lines[n])
				}
			}
			this.gui.show_popup('see_sale_order_details_popup_widget', {'order': [orders1], 'orderline':orderline});
		},

		import_widget: function (o_id) {
			var self = this;
			var orders =  self.pos.all_sale_orders_list;
			var orders_lines =  self.pos.all_sale_orders_line_list;
			var orders1 = [];
			for(var ord = 0; ord < orders.length; ord++){
				if (orders[ord]['id'] == o_id){
					 orders1 = orders[ord];
				}
			}
			var orderline = [];
			for(var n=0; n < orders_lines.length; n++){
				if (orders_lines[n]['order_id'][0] ==o_id){
					orderline.push(orders_lines[n])
				}
			}
			this.gui.show_popup('sale_order_popup_widget', {'order': orders1, 'orderlines':orderline});
		},

		orderline_click_events: function () {
			var self = this;
			this.$('.client-list-contents').delegate('.orders-line-name', 'click', function(event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
			
			this.$('.client-list-contents').delegate('.orders-line-ref', 'click', function(event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
						
			this.$('.client-list-contents').delegate('.orders-line-partner', 'click', function(event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
			
			this.$('.client-list-contents').delegate('.orders-line-date', 'click', function(event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
						
			this.$('.client-list-contents').delegate('.orders-line-tot', 'click', function(event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});

			this.$('.client-list-contents').delegate('.orders-line-saleperson', 'click', function(event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});

			this.$('.client-list-contents').delegate('.orders-line-subtotal', 'click', function(event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});


			this.$('.client-list-contents').delegate('.sale-order', 'click', function(event) {
				var o_id = $(this).data('id');
				self.import_widget(o_id);
			});
		},

		
		show: function(options) {
			var self = this;
			this._super(options);
			this.old_sale_order = null;
			this.details_visible = false;
			var flag = 0;
			var orders = self.pos.all_sale_orders_list;
			var orders_lines = self.pos.all_sale_orders_line_list;
			var selectedOrder;
			this.render_list_orders(orders, undefined);
			self.orderline_click_events();

			var selectedorderlines = [];
			var client = false
			
			this.$('.back').click(function(){
				self.gui.show_screen('products');
			});

			this.$('.refresh-order').on('click',function () {
				$('.search-order input').val('');
				self.get_sale_orders();
			});

			//this code is for Search Orders
			this.$('.search-order input').keyup(function() {
				self.render_list_orders(orders, this.value);
			});
			
		},	   

	});
	gui.define_screen({
		name: 'see_all_sale_orders_screen_widget',
		widget: SeeAllSaleOrdersScreenWidget
	});

	var SaleOrderPopupWidget = popups.extend({
		template: 'SaleOrderPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		//
		show: function(options) {
			options = options || {};
			var self = this;
			this._super(options);
			this.orderlines = options.orderlines || [];

		},
		//
		renderElement: function() {
			var self = this;
			this._super();
			var selectedOrder = this.pos.get_order();
			if(selectedOrder == null){
				return
			}
			var crnt_orderlines = selectedOrder.get_orderlines();

			var orderlines = self.options.orderlines;
			var order = self.options.order;
			// When you click on apply button, Customer is selected automatically in that order 
			var partner_id = false
			var client = false
			if (order && order.partner_id != null)
				partner_id = order.partner_id[0];
				client = this.pos.db.get_partner_by_id(partner_id);
				
			var reorder_products = {};

			this.$('#apply_saleorder').click(function() {
				var entered_code = $("#entered_item_qty").val();
				var list_of_qty = $('.entered_item_qty');

				$.each(list_of_qty, function(index,value) {
					var entered_item_qty = $(value).find('input');
					var qty_id = parseFloat(entered_item_qty.attr('qty-id'));
					var line_id = parseFloat(entered_item_qty.attr('line-id'));
					var entered_qty = parseFloat(entered_item_qty.val());

					reorder_products[line_id] = entered_qty;
				});

				for(var i in reorder_products)
				{	
					var orders_lines = self.pos.all_sale_orders_line_list;
					for(var n=0; n < orders_lines.length; n++)
					{
					   if (orders_lines[n]['id'] == i)
					   {
							var product = self.pos.db.get_product_by_id(orders_lines[n].product_id[0]);
							if(product)
							{
								if(reorder_products[i]>0)
								{
									selectedOrder.add_product(product, {
										quantity: parseFloat(reorder_products[i]),
										price: orders_lines[n].price_unit,
										discount: orders_lines[n].discount
									});
									selectedOrder.set_client(client);
									self.pos.set_order(selectedOrder);
								}
							}
							else{
									alert("please configure product for point of sale.");
									return;
							}
					   }
					}
				}
				
				self.gui.show_screen('products');

			});
		},

	});

	gui.define_popup({
		name: 'sale_order_popup_widget',
		widget: SaleOrderPopupWidget
	});

	var SeeSaleOrderDetailsPopupWidget = popups.extend({
		template: 'SeeSaleOrderDetailsPopupWidget',
		
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		show: function(options) {
			var self = this;
			options = options || {};
			this._super(options);
			
			
			this.order = options.order || [];
			this.orderline = options.orderline || [];
						
		},
		
		events: {
			'click .button.cancel': 'click_cancel',
		},

		renderElement: function() {
			var self = this;
			this._super();  
		},
	});

	gui.define_popup({
		name: 'see_sale_order_details_popup_widget',
		widget: SeeSaleOrderDetailsPopupWidget
	});

	var CustomErrorPopupWidget = popups.extend({
		template: 'CustomErrorPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		show: function(options) {
			var self = this;
			this._super(options);
		},

		renderElement: function() {
			var self = this;
			this._super();
		},
	});
	gui.define_popup({
		name: 'custom_error',
		widget: CustomErrorPopupWidget
	});
	
});
