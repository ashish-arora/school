__author__ = 'shoyeb'

from schoolapp.models import ProductPlan
ProductPlan.objects.create(name="Basic",duration_days="-1",features={"free_students":50,"attendance":1,"event_update":1})