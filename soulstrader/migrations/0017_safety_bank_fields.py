from django.db import migrations, models
import decimal


class Migration(migrations.Migration):

    dependencies = [
        ('soulstrader', '0016_increase_day_change_percent_limit'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfolio',
            name='safety_bank_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='portfolio',
            name='safety_bank_balance',
            field=models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='portfolio',
            name='bank_divisor',
            field=models.IntegerField(default=10, help_text='Divisor controlling taper rate; higher = slower saving'),
        ),
        migrations.AddField(
            model_name='portfolio',
            name='bank_rate_ceiling_percent',
            field=models.DecimalField(decimal_places=2, default=decimal.Decimal('20.00'), help_text='Maximum allocation rate (%) of net SELL proceeds to Bank', max_digits=5),
        ),
    ]


