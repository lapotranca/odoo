odoo.define('tf_balance_sheet_accounting.account_report', function (require) {
    'use strict';

    var core = require('web.core');
    var Context = require('web.Context');
    var AbstractAction = require('web.AbstractAction');
    var Dialog = require('web.Dialog');
    var datepicker = require('web.datepicker');
    var session = require('web.session');
    var field_utils = require('web.field_utils');
    var RelationalFields = require('web.relational_fields');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    var WarningDialog = require('web.CrashManager').WarningDialog;
    var Widget = require('web.Widget');
    var account_inherit = require('account_reports.account_report');

    var QWeb = core.qweb;
    var _t = core._t;

    var M2MFilters = Widget.extend(StandaloneFieldManagerMixin, {
        /**
         * @constructor
         * @param {Object} fields
         */
        init: function (parent, fields) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.fields = fields;
            this.widgets = {};
        },
        /**
         * @override
         */
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            _.each(this.fields, function (field, fieldName) {
                defs.push(self._makeM2MWidget(field, fieldName));
            });
            return Promise.all(defs);
        },
        /**
         * @override
         */
        start: function () {
            var self = this;
            var $content = $(QWeb.render("m2mWidgetTable", {fields: this.fields}));
            self.$el.append($content);
            _.each(this.fields, function (field, fieldName) {
                self.widgets[fieldName].appendTo($content.find('#'+fieldName+'_field'));
            });
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * This method will be called whenever a field value has changed and has
         * been confirmed by the model.
         *
         * @private
         * @override
         * @returns {Promise}
         */
        _confirmChange: function () {
            var self = this;
            var result = StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
            var data = {};
            _.each(this.fields, function (filter, fieldName) {
                data[fieldName] = self.widgets[fieldName].value.res_ids;
            });
            this.trigger_up('value_changed', data);
            return result;
        },
        /**
         * This method will create a record and initialize M2M widget.
         *
         * @private
         * @param {Object} fieldInfo
         * @param {string} fieldName
         * @returns {Promise}
         */
        _makeM2MWidget: function (fieldInfo, fieldName) {
            var self = this;
            var options = {};
            options[fieldName] = {
                options: {
                    no_create_edit: true,
                    no_create: true,
                }
            };
            return this.model.makeRecord(fieldInfo.modelName, [{
                fields: [{
                    name: 'id',
                    type: 'integer',
                }, {
                    name: 'display_name',
                    type: 'char',
                }],
                name: fieldName,
                relation: fieldInfo.modelName,
                type: 'many2many',
                value: fieldInfo.value,
            }], options).then(function (recordID) {
                self.widgets[fieldName] = new RelationalFields.FieldMany2ManyTags(self,
                    fieldName,
                    self.model.get(recordID),
                    {mode: 'edit',}
                );
                self._registerWidget(recordID, fieldName, self.widgets[fieldName]);
            });
        },
    });

    account_inherit.include({
        hasControlPanel: true,

        custom_events: {
            'value_changed': function(ev) {
                 var self = this;
                 self.report_options.partner_ids = ev.data.partner_ids;
                 self.report_options.partner_categories = ev.data.partner_categories;
                 self.report_options.analytic_accounts = ev.data.analytic_accounts;
                 self.report_options.analytic_tags = ev.data.analytic_tags;
                 self.report_options.v_cost_centers = ev.data.v_cost_centers;
                 self.report_options.v_departments = ev.data.v_departments;
                 return self.reload().then(function () {
                    ev.target.$el.parents('.o_dropdown').find('a.dropdown-toggle').click();
                 });
             },
        },

        render_searchview_buttons: function() {
            var self = this;
            // bind searchview buttons/filter to the correct actions
            var $datetimepickers = this.$searchview_buttons.find('.js_account_reports_datetimepicker');
            var options = { // Set the options for the datetimepickers
                locale : moment.locale(),
                format : 'L',
                icons: {
                    date: "fa fa-calendar",
                },
            };
            // attach datepicker
            $datetimepickers.each(function () {
                var name = $(this).find('input').attr('name');
                var defaultValue = $(this).data('default-value');
                $(this).datetimepicker(options);
                var dt = new datepicker.DateWidget(options);
                dt.replace($(this)).then(function () {
                    dt.$el.find('input').attr('name', name);
                    if (defaultValue) { // Set its default value if there is one
                        dt.setValue(moment(defaultValue));
                    }
                });
            });
            // format date that needs to be show in user lang
            _.each(this.$searchview_buttons.find('.js_format_date'), function(dt) {
                var date_value = $(dt).html();
                $(dt).html((new moment(date_value)).format('ll'));
            });
            // fold all menu
            this.$searchview_buttons.find('.js_foldable_trigger').click(function (event) {
                $(this).toggleClass('o_closed_menu o_open_menu');
                self.$searchview_buttons.find('.o_foldable_menu[data-filter="'+$(this).data('filter')+'"]').toggleClass('o_closed_menu');
            });
            // render filter (add selected class to the options that are selected)
            _.each(self.report_options, function(k) {
                if (k!== null && k.filter !== undefined) {
                    self.$searchview_buttons.find('[data-filter="'+k.filter+'"]').addClass('selected');
                }
            });
            _.each(this.$searchview_buttons.find('.js_account_report_bool_filter'), function(k) {
                $(k).toggleClass('selected', self.report_options[$(k).data('filter')]);
            });
            _.each(this.$searchview_buttons.find('.js_account_report_choice_filter'), function(k) {
                $(k).toggleClass('selected', (_.filter(self.report_options[$(k).data('filter')], function(el){return ''+el.id == ''+$(k).data('id') && el.selected === true;})).length > 0);
            });
            $('.js_account_report_group_choice_filter', this.$searchview_buttons).each(function (i, el) {
                var $el = $(el);
                var ids = $el.data('member-ids');
                $el.toggleClass('selected', _.every(self.report_options[$el.data('filter')], function (member) {
                    // only look for actual ids, discard separators and section titles
                    if(typeof member.id == 'number'){
                      // true if selected and member or non member and non selected
                      return member.selected === (ids.indexOf(member.id) > -1);
                    } else {
                      return true;
                    }
                }));
            });
            _.each(this.$searchview_buttons.find('.js_account_reports_one_choice_filter'), function(k) {
                $(k).toggleClass('selected', ''+self.report_options[$(k).data('filter')] === ''+$(k).data('id'));
            });
            // click events
            this.$searchview_buttons.find('.js_account_report_date_filter').click(function (event) {
                self.report_options.date.filter = $(this).data('filter');
                var error = false;
                if ($(this).data('filter') === 'custom') {
                    var date_from = self.$searchview_buttons.find('.o_datepicker_input[name="date_from"]');
                    var date_to = self.$searchview_buttons.find('.o_datepicker_input[name="date_to"]');
                    if (date_from.length > 0){
                        error = date_from.val() === "" || date_to.val() === "";
                        self.report_options.date.date_from = field_utils.parse.date(date_from.val());
                        self.report_options.date.date_to = field_utils.parse.date(date_to.val());
                    }
                    else {
                        error = date_to.val() === "";
                        self.report_options.date.date_to = field_utils.parse.date(date_to.val());
                    }
                }
                if (error) {
                    new WarningDialog(self, {
                        title: _t("Odoo Warning"),
                    }, {
                        message: _t("Date cannot be empty")
                    }).open();
                } else {
                    self.reload();
                }
            });
            this.$searchview_buttons.find('.js_account_report_bool_filter').click(function (event) {
                var option_value = $(this).data('filter');
                self.report_options[option_value] = !self.report_options[option_value];
                if (option_value === 'unfold_all') {
                    self.unfold_all(self.report_options[option_value]);
                }
                self.reload();
            });
            $('.js_account_report_group_choice_filter', this.$searchview_buttons).click(function () {
                var option_value = $(this).data('filter');
                var option_member_ids = $(this).data('member-ids') || [];
                var is_selected = $(this).hasClass('selected');
                _.each(self.report_options[option_value], function (el) {
                    // if group was selected, we want to uncheck all
                    el.selected = !is_selected && (option_member_ids.indexOf(Number(el.id)) > -1);
                });
                self.reload();
            });
            this.$searchview_buttons.find('.js_account_report_choice_filter').click(function (event) {
                var option_value = $(this).data('filter');
                var option_id = $(this).data('id');
                _.filter(self.report_options[option_value], function(el) {
                    if (''+el.id == ''+option_id){
                        if (el.selected === undefined || el.selected === null){el.selected = false;}
                        el.selected = !el.selected;
                    } else if (option_value === 'ir_filters') {
                        el.selected = false;
                    }
                    return el;
                });
                self.reload();
            });
            this.$searchview_buttons.find('.js_account_reports_one_choice_filter').click(function (event) {
                self.report_options[$(this).data('filter')] = $(this).data('id');
                self.reload();
            });
            this.$searchview_buttons.find('.js_account_report_date_cmp_filter').click(function (event) {
                self.report_options.comparison.filter = $(this).data('filter');
                var error = false;
                var number_period = $(this).parent().find('input[name="periods_number"]');
                self.report_options.comparison.number_period = (number_period.length > 0) ? parseInt(number_period.val()) : 1;
                if ($(this).data('filter') === 'custom') {
                    var date_from = self.$searchview_buttons.find('.o_datepicker_input[name="date_from_cmp"]');
                    var date_to = self.$searchview_buttons.find('.o_datepicker_input[name="date_to_cmp"]');
                    if (date_from.length > 0) {
                        error = date_from.val() === "" || date_to.val() === "";
                        self.report_options.comparison.date_from = field_utils.parse.date(date_from.val());
                        self.report_options.comparison.date_to = field_utils.parse.date(date_to.val());
                    }
                    else {
                        error = date_to.val() === "";
                        self.report_options.comparison.date_to = field_utils.parse.date(date_to.val());
                    }
                }
                if (error) {
                    new WarningDialog(self, {
                        title: _t("Odoo Warning"),
                    }, {
                        message: _t("Date cannot be empty")
                    }).open();
                } else {
                    self.reload();
                }
            });

            // partner filter
            if (this.report_options.partner) {
                if (!this.M2MFilters) {
                    var fields = {};
                    if ('partner_ids' in this.report_options) {
                        fields['partner_ids'] = {
                            label: _t('Partners'),
                            modelName: 'res.partner',
                            value: this.report_options.partner_ids.map(Number),
                        };
                    }
                    if ('partner_categories' in this.report_options) {
                        fields['partner_categories'] = {
                            label: _t('Tags'),
                            modelName: 'res.partner.category',
                            value: this.report_options.partner_categories.map(Number),
                        };
                    }
                    if (!_.isEmpty(fields)) {
                        this.M2MFilters = new M2MFilters(this, fields);
                        this.M2MFilters.appendTo(this.$searchview_buttons.find('.js_account_partner_m2m'));
                    }
                } else {
                    this.$searchview_buttons.find('.js_account_partner_m2m').append(this.M2MFilters.$el);
                }
            }

            // analytic filter
            if (this.report_options.analytic) {
                if (!this.M2MFilters) {
                    var fields = {};
                    if (this.report_options.analytic_accounts) {
                        fields['analytic_accounts'] = {
                            label: _t('Accounts'),
                            modelName: 'account.analytic.account',
                            value: this.report_options.analytic_accounts.map(Number),
                        };
                    }
                    if (this.report_options.analytic_tags) {
                        fields['analytic_tags'] = {
                            label: _t('Tags'),
                            modelName: 'account.analytic.tag',
                            value: this.report_options.analytic_tags.map(Number),
                        };
                    }
                    if (!_.isEmpty(fields)) {
                        this.M2MFilters = new M2MFilters(this, fields);
                        this.M2MFilters.appendTo(this.$searchview_buttons.find('.js_account_analytic_m2m'));
                    }
                } else {
                    this.$searchview_buttons.find('.js_account_analytic_m2m').append(this.M2MFilters.$el);
                }
            }

            if (this.report_options.v_cost_center) {
                if (!this.VCostCenterFilters) {
                    var fields = {};
                    fields['v_cost_centers'] = {
                        label: _t('Cost Center'),
                        modelName: 'tf.cost.center',
                        value: this.report_options.v_cost_centers.map(Number),
                    };
                    this.VCostCenterFilters = new M2MFilters(this, fields);
                    this.VCostCenterFilters.appendTo(this.$searchview_buttons.find('.js_v_cost_center_m2m'));
                } else {
                    this.$searchview_buttons.find('.js_v_cost_center_m2m').append(this.VCostCenterFilters.$el);
                }
                if (!this.VDepartmentFilters) {
                    var fields = {};
                    fields['v_departments'] = {
                        label: _t('Department'),
                        modelName: 'tf.department',
                        value: this.report_options.v_departments.map(Number),
                    };
                    this.VDepartmentFilters = new M2MFilters(this, fields);
                    this.VDepartmentFilters.appendTo(this.$searchview_buttons.find('.js_v_department_m2m'));
                } else {
                    this.$searchview_buttons.find('.js_v_department_m2m').append(this.VDepartmentFilters.$el);
                }
           }
        },

    });



});
