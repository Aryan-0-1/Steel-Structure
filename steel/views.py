from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse


def index(request):
    return render(request,"index.html")