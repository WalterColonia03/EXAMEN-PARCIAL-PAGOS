from django.db import connection
from django.test import TestCase

from payments.models import Payable, PaymentCommitment


class PaymentSchemaTests(TestCase):
    def test_supply_code_columns_are_present(self):
        with connection.cursor() as cursor:
            payable_columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, Payable._meta.db_table)
            }
            commitment_columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, PaymentCommitment._meta.db_table
                )
            }

        self.assertIn("supply_code", payable_columns)
        self.assertIn("supply_code", commitment_columns)
