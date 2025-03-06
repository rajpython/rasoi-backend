from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from restaurante.models import Menu
from restaurante.serializers import MenuSerializer

class MenuViewTest(APITestCase):
    def setUp(self):
        # self.client = APIClient()

        # Create a user
        self.user = User.objects.create_user(username='testuser', password='testpassword')

        # Create an authentication token for the user
        self.token = Token.objects.create(user=self.user)

        # Set up the client credentials
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)


        self.menu1 = Menu.objects.create(name="IceCream", price=80, inventory=100)
        self.menu2 = Menu.objects.create(name="Cake", price=15, inventory=50)
        self.menu3 = Menu.objects.create(name="Pie", price=12, inventory=75)

    def test_get_all_menus(self):
        response = self.client.get(reverse('restaurante:menu-list'))
        menus = Menu.objects.all()
        serializer = MenuSerializer(menus, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(response.data['results'], serializer.data)
        self.assertEqual(response.data, serializer.data)
