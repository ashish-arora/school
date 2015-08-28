from django.shortcuts import render
from .models import User
from rest_framework import status
from schoolapp.helpers.json_response import JSONResponse
from rest_framework.views import APIView
import time, traceback, json
from helpers import utils
from mongoengine.errors import NotUniqueError
from mongoengine.errors import DoesNotExist
import math
# Create your views here.

class AccountSignUp:

    def post(self, request):
        username = request.data.get('node_id1','')
         = request.data.get('node_id2','')