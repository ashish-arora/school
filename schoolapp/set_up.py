__author__ = 'ashish'
from schoolapp.models import ProductType, PRODUCT_TYPE_NAMES, PRODUCT_TYPES


ProductType.objects.create(name=PRODUCT_TYPE_NAMES[0], type=PRODUCT_TYPES[0], free_students=100, features=[])

ProductType.objects.create(name=PRODUCT_TYPE_NAMES[1], type=PRODUCT_TYPES[1], free_students=100, features=[])
