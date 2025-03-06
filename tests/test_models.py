from django.test import TestCase
from restaurante.models import Menu

#TestCase class
class MenuItemTest(TestCase):
    def test_get_item(self):
        item = Menu.objects.create(name="IceCream", price=80, inventory=100)
        self.assertEqual(str(item), "IceCream : 80; 100 available")