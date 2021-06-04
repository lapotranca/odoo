import logging

from odoo.tests.common import TransactionCase, post_install, at_install

_logger = logging.getLogger(__name__)


@post_install(True)
@at_install(False)
class TestAccessMenu(TransactionCase):

    def setUp(self):
        super(TestAccessMenu, self).setUp()
        self.admin_user = self.env.ref('base.user_root')
        self.demo_user = self.env.ref('base.user_demo')
        self.group_employee = self.env.ref('base.group_user')
        self.menu_settings = self.env.ref('base.menu_administration')
        self.menu_ir_property = self.env.ref('base.menu_ir_property')
        self.Menu = self.env['ir.ui.menu']

    def test_access_menu(self):
        #  demo user menus
        menu = self.Menu.with_user(self.demo_user.id).search([])

        #  ensure menu 'Settings' invisible
        self.assertNotIn(self.menu_settings, menu)

        #  add group employee to menu 'Settings'
        self.menu_settings.write({
            'groups_id': [(6, 0, [self.group_employee.id])]
        })

        #  demo user menus
        menu = self.Menu.with_user(self.demo_user.id).search([])

        #  ensure menu 'Settings' visible
        self.assertIn(self.menu_settings, menu)

        #  add group employee to restrict menu 'Settings'
        self.menu_settings.write({
            'restrict_group_ids': [(6, 0, [self.group_employee.id])]
        })

        #  demo user menus
        menu = self.Menu.with_user(self.demo_user.id).search([])

        #  ensure menu 'Settings' invisible
        self.assertNotIn(self.menu_settings, menu)

        # check menu 'Settings/Technical/Parameters' visible to demo_user
        self.assertIn(self.menu_ir_property, menu)

        # hide menu 'Settings/Technical/Parameters' from demo_user
        self.demo_user.write({
            'hidden_menu_ids': [(6, 0, [self.menu_ir_property.id])]
        })

        menu = self.Menu.with_user(self.demo_user.id).search([])

        # check menu 'Settings/Technical/Parameters' hidden for demo_user
        self.assertNotIn(self.menu_ir_property, menu)
        self.assertEqual(
            self.menu_ir_property.hide_from_user_ids.id, self.demo_user.id)

        # check menu 'Settings/Technical/Parameters' visible for user_root
        menu_admin = self.Menu.with_user(self.admin_user.id).search([])
        self.assertIn(self.menu_ir_property, menu_admin)
