from typing import Any
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View
from django.core.handlers.wsgi import WSGIRequest



class IndexView(View):

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        return super().setup(request, *args, **kwargs)

    def get(self, request: WSGIRequest, *args, **kwargs):
        return HttpResponse(f'hey, {request.user}, bizare poker is here 🤡')
