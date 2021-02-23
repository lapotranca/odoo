odoo.define('l10n_mx_hr_expense.checks_widget', function(require){
    'use strict';

    var core = require('web.core');
    var AbstractField = require('web.AbstractField');
    var field_registry = require('web.field_registry');
    var Qweb = core.qweb;

    var ChecksWidget = AbstractField.extend({
        template: 'ExpenseChecks',
        className: 'js_expense_checks',
        events: {
            'click .text-success': '_onClickSucceeded',
            'click .text-danger': '_onClickSucceeded',
        },
        _onClickSucceeded: function(){
            this.animate();
        },
        animate: function(){
            this.get_html();
        },
        get_html: function(){
            this._rpc({
                model: this.model,
                method: 'json2qweb',
                args: ['json_input', this.value],
            }).then(function(rendered_view){
                this.modal = Qweb.render('ExpenseChecksModal',{ 'html_field': rendered_view});
                var rendered_modal = $(this.modal).modal();
                rendered_modal.find('li').each(function(i) {
                    $(this).delay(300 * i).fadeIn(800);
                });
            });
        },
        init: function () {
            this._super.apply(this, arguments);
            this.messages = JSON.parse(this.value) || {};
            this.failed = 0;
            this.succeeded = 0;
            if (this.value) {
                this.failed = Object.keys(this.messages.fail).length || 0;
                this.succeeded = Object.keys(this.messages.ok).length || 0;
            }
        },
    });
field_registry.add('expenses_checks', ChecksWidget);
return ChecksWidget;
});
