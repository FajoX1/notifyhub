from django.shortcuts import render
from django.http import HttpRequest, HttpResponse

from asgiref.sync import sync_to_async


async def home(request: HttpRequest) -> HttpResponse:
    user = await request.auser()

    return await sync_to_async(render)(request, "landing.html", {"user": user})
