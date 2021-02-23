Mexican Expenses
================

This module allows to generate a supplier invoice (vendor bill) from an expense
which has an XML file related in your documents.

When an expense is approved, if it contains an XML file in their attachments,
the system tries to generate a new supplier invoice based on the CFDI, automatically filling
automatically some fields.

**What are the steps?**


- Create an expense for an employee who has already configured an associated
  journal (see the Configuration section for more information about how
  journals should be set up). Pay special attention to the field `Payment By`
  because the behavior will vary depending on whether the employee needs to
  be reimbursed.

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step1.png
      :width: 400pt
      :alt: Creating an expense

- Attach an XML file corresponding to the CFDI.

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step2.png
      :width: 400pt
      :alt: Attaching a CFDI

- Submit the expense to manager

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step3.png
      :width: 400pt
      :alt: Submitting expense to manager

- If we have several expenses to send, we can mark the desired expenses, 
  go to Actions, and select Expense: Submit to manager

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step_alternative.png
      :width: 400pt
      :alt: Submitting group of expense to manager

- Approve the expense, this task is done by the manager. If the CFDI attached
  is all right, a new supplier invoice is created using the information of the
  CFDI. You may look at the messages to ensure the invoice was created
  correctly. If any error occurs, please check the section
  `Posible errors in the invoice creation` to know about most common causes.

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step4.png
      :width: 400pt
      :alt: Message list

- Once the manager has approved the expense, the invoice is automatically
  created. To check the newly created invoice, click on the button `Invoices`.

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step5.png
      :width: 400pt
      :alt: Created invoices

- At this point, the behavior will depend on what the field `Payment By` was
  filled with: `Employee (to reimburse)` or `Company`. In other words, it will
  depend on wheter the payment method used to pay the expense belongs to the
  employee or belongs to the company.

    - If the payment method belongs to the company, then the invoice is created
      in draft mode. No additional steps are required, because the invoice is
      created as a regular supplier invoice and may be treated as such.

      .. image:: l10n_mx_edi_hr_expense/static/src/img/step6a.png
        :width: 400pt
        :alt: Created invoice, payment by company

    - If the payment method belongs to the employee, the invoice is created and
      validated; and then is automatically paid registering a new payment from
      the employee's journal.

      .. image:: l10n_mx_edi_hr_expense/static/src/img/step6b.png
        :width: 400pt
        :alt: Created invoice, payment by employee

- Since the employee has to be reimbursed, then the journal assigned to the
  employee will have a negative amount, which represents the exact amount the
  company owes to that employee.

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step7.png
      :width: 400pt
      :alt: Negative valance

- The employee is reimbursed as a petty cash replenishment, i.e. with an
  internal transfer from one of the company's accounts. To do so, click on 
  `More` -> `Internal Transfer` -> `Create`

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step8.png
      :width: 400pt
      :alt: Creating transfer to reimburse

- Finally, make a transfer from one of the company's accounts to the
  employee's journal and click `Confirm`. After doing so, the valance of the
  employee's journal should go to Cero

    .. image:: l10n_mx_edi_hr_expense/static/src/img/step9.png
      :width: 400pt
      :alt: Valance cero

  *Considerations:*

  - If the product in the CFDI is not found in the system when the invoice
    is created, it will be taken from the product assigned in the expense.

  - Taxes defined in the CFDI are automatically searched in Odoo by their
    rates. If there are more than one resulting tax for a given rate, it will
    be taken from the one configured in the product as a vendor tax, or the
    first available one if there is not any configured.

  - In the expense sheet the expenses that are not valid in the SAT system
    are yellow.

**Posible errors in the invoice creation**

- *The Receptor's RFC in the XML does not match with your Company's RFC*

  This error is produced when the Receiver's VAT in the CFDI is different from
  the VAT assigned in the company. The document is incorrect, because it menas
  it does not belong to your company.

- *The XML UUID belongs to other invoice.*

  This error is produced when another invoice with the same UUID is found,
  because UUIDs are  unique, which means the invoice is duplicated.

- *The invoice reference belongs to other invoice of the same partner.*

  Each invoice has a `Vendor Reference`. This field is filled when the invoice
  is created, but there should not be two invoices created with the same value.

- *The invoice refused in group of expenses*

  The expenses with errors, when they are grouped, can be identified by 
  the color red, these can be edited to retry the approval.

    .. image:: l10n_mx_edi_hr_expense/static/src/img/expense_refund_group.png
      :width: 400pt
      :alt: Partially processed expenses

Extra Features:
---------------

- Allowed to replenishment a petty cash from the kanban view with amount needed
  for that replenishment.

- Payments to be checked

  The use case is: The employee needs to make the service to the company car,
  but to make the work, the supplier request the payment in advance. And after
  they send the CFDI for the service.

  In this case, is necessary the next flow:

  1. The employee creates a new expense, with the amount total of the service,
     for the supplier, and mark the record ``To be check``.
  2. The employee creates the report and sends to their manager.
  3. The manager approves and sends to the accountant.
  4. The accountant creates the invoice and makes the payment. (The payment
     has a field to select the employee that will check that expense.)
  5. When the CFDI is received, is generated a new expense, that must be for
     the same supplier and employee.
  6. In this expense is necessary to press the button ``Merge Expense``
     that opens a wizard, where must be selected the expense created in step 1.

  Whit this, the expense in step 1 is archived, and the last expense takes
  its place.

- Case for airlines.

  In the next cases:

  ``Concept: Total = 4497.00``

  ``Taxes: 0%  - Base = 1125.00 | 16% - Base = 3372.00``

  The concept has 2 taxes, but the total is not applied to all the total, in
  this case, must be split the line (one by each tax). To this, must be added
  the label "Is Airline" in the supplier.

Exceptions supported:
---------------------

- The expense is deductible but not have a CFDI
  (CFE or foreign supplier for example).

  In this case, is necessary adds the category `Force Invoice Generation` in
  the partners with this case, and generate a normal expense.

  For this, will be generated a supplier invoice in draft with the
  expense data.

  Note:

  If the expense is a credit note. Generate a normal expense specifying
  that the type of document is a Credit Note. This will generate a
  Draft Supplier Credit Note with the expense data.

- Is necessary edit the invoice created from an expense.

  In this case, is better do not validate the invoice generated and with this
  omit the payment generation. For this is necessary adds the label
  `Create Invoices Draft` in the supplier.

- It is necessary that a user who is not the manager of a department or
  responsible for the expenses of an employee, approves expenses.

  In this case, the user who will approve the expense is added to the group
  `Allow to approve expenses without being responsible` and is assigned as
  responsible for the expense to be approved.

Installation
============

  - Download this module from `Vauxoo/mexico
    <https://github.com/vauxoo/mexico>`_
  - Add the repository folder into your odoo addons-path.
  - Go to ``Settings > Module list``, search for the current name and click in
    ``Install`` button.

Configuration
=============

Since this module addresses employees's reimbursements as petty cash
replenishments, it requires a journal for each employee who makes expenses.

This module provides an automated action to create a journal whenever an
employee is created. Such action, named
`hr_expense: Auto create journal on all employees`
is disabled by default. You may enable it, or create all journals yourself.

If you choose to use the automated action, you may also configure an account to
be used as template, so that the created journal's debit/credit account takes
its code, by setting the config parameter
`l10n_mx_edi_hr_expense.template_account_employee`
with the desired account ID. If you choose to create the journals manually, you
may do so configuring them as follows:

- `Journal Name`: This should be a representative name that identifies the
  employee, e.g. Expenses of John Doe
- `Type`: `Cash` or `Bank`, accordingly
- `Default debit account`: The wage account which the employee is paid from.
- `Default Credit Account`: Same as `Default Debit Account`

  .. image:: l10n_mx_edi_hr_expense/static/src/img/config1.png
    :width: 400pt
    :alt: Journal configuration

Then, edit the involved employee, and under the tab `Public Information`, set the field `Journal` with the journal just created.

  .. image:: l10n_mx_edi_hr_expense/static/src/img/config2.png
    :width: 400pt
    :alt: Employee configuration

Tip: if there are too many journals on the dashboard, they may be hidden
following one of these equivalent alternatives:

- On the accounting dashboard, locate the journal you'd like to hide, click the
  `More` button and unmark the option `Favorite`.

  .. image:: l10n_mx_edi_hr_expense/static/src/img/tip1.png
    :width: 400pt
    :alt: Hiding a journal, option 1

- When creating a new journal, uncheck the option `Show journal on dashboard`,
  located in the `Advanced options` tab.

  .. image:: l10n_mx_edi_hr_expense/static/src/img/tip2.png
    :width: 400pt
    :alt: Hiding a journal, option 2

  **Note**: the Debug mode must be enabled for that option to show up.

How to select the accountant?
-----------------------------

When is generated an expense sheet is assigned an accountant, that is the
user that will accrue the expenses. If the company has many accountants,
could be assigned a different for each case.

Expenses from a supplier:
-------------------------

  In this case, is necessary to assign the label "Vendor" in the supplier, and
  assign the accountant for each currency. If the label is not found will
  be assigned the accountant in the employee or by default. If the label
  is found but is not assigned an accountant will be used the default values.

Expenses from an employee:
--------------------------

  In this case, first, check that the supplier does not has the label
  "Vendor", and if is empty, is used the employee accountant or if is
  empty take the default values according to the expense currency.

Bug Tracker
===========

Bugs are tracked on
`GitHub Issues <https://github.com/Vauxoo/mexico/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and
welcomed feedback
`here <https://github.com/Vauxoo/mexico/issues/new?body=module:%20
l10n_mx_bedi_hr_expense%0Aversion:%20
10.0.1.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_

Credits
=======

**Contributors**

* Nhomar Hernández <nhomar@vauxoo.com> (Planner/Auditor)
* Luis Torres <luis_t@vauxoo.com> (Developer)

Maintainer
==========

.. image:: https://s3.amazonaws.com/s3.vauxoo.com/description_logo.png
   :alt: Vauxoo
