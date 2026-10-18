from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from identity.models import Account, AccountRecoveryCode, Role
from identity.services import RecoveryEmailDeliveryError


class InitialManagerProvisioningTests(TestCase):
    @patch("identity.management.commands.provision_initial_manager.send_email_recovery_code")
    def test_creates_passwordless_manager_and_issues_email_code(self, mocked_send):
        output = StringIO()

        call_command(
            "provision_initial_manager",
            email="gerente.real@gmail.com",
            display_name="Gerente Real",
            stdout=output,
        )

        manager = Account.objects.get(email_normalized="gerente.real@gmail.com")
        self.assertEqual(manager.role.code, Role.Code.MANAGER)
        self.assertTrue(manager.must_change_password)
        self.assertFalse(manager.has_usable_password())
        self.assertTrue(
            AccountRecoveryCode.objects.filter(
                account=manager,
                kind=AccountRecoveryCode.Kind.EMAIL,
            ).exists()
        )
        mocked_send.assert_called_once()
        self.assertIn("Gerente inicial creado", output.getvalue())

    @patch(
        "identity.management.commands.provision_initial_manager.send_email_recovery_code",
        side_effect=RecoveryEmailDeliveryError,
    )
    def test_rolls_back_when_activation_email_cannot_be_sent(self, _mocked_send):
        with self.assertRaisesMessage(CommandError, "la cuenta no fue creada"):
            call_command(
                "provision_initial_manager",
                email="gerente.real@gmail.com",
                display_name="Gerente Real",
            )

        self.assertFalse(Account.objects.exists())
