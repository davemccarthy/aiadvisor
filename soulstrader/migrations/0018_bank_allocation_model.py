from django.db import migrations, models
import decimal


class Migration(migrations.Migration):

    dependencies = [
        ('soulstrader', '0017_safety_bank_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankAllocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allocated_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('proceeds_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('allocation_rate_percent', models.DecimalField(decimal_places=2, max_digits=5)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('portfolio', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='bank_allocations', to='soulstrader.portfolio')),
                ('trade', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='bank_allocation', to='soulstrader.trade')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]


