import random

from django.shortcuts import render, redirect


def simulation_page(request, *args, **kwargs):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000_000, 999_999_999))[2:]
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_english.html", context)


def main_page(request, *args, **kwargs):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000_000, 999_999_999))[2:]
    context = {"username": request.session["username"]}
    return render(request, "sim/main_page_english.html", context=context)