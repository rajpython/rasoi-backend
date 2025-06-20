# Generated by Django 4.2.21 on 2025-06-07 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurante", "0012_alter_order_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="delivery_time_slot",
            field=models.CharField(
                choices=[
                    ("ASAP", "ASAP"),
                    ("11:00", "11:00"),
                    ("11:30", "11:30"),
                    ("12:00", "12:00"),
                    ("12:30", "12:30"),
                    ("13:00", "13:00"),
                    ("13:30", "13:30"),
                    ("14:00", "14:00"),
                    ("14:30", "14:30"),
                    ("15:00", "15:00"),
                    ("15:30", "15:30"),
                    ("16:00", "16:00"),
                    ("16:30", "16:30"),
                    ("17:00", "17:00"),
                    ("17:30", "17:30"),
                    ("18:00", "18:00"),
                    ("18:30", "18:30"),
                    ("19:00", "19:00"),
                    ("19:30", "19:30"),
                    ("20:00", "20:00"),
                ],
                default="ASAP",
                max_length=20,
            ),
        ),
    ]
