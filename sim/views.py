import random

from django.shortcuts import render, redirect


def simulation_page_dutch(request, *args, **kwargs):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000, 999_999_999_999))[2:]
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_dutch.html", context)


def simulation_page_english(request, *args, **kwargs):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000, 999_999_999_999))[2:]
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_english.html", context)


def simulation_page_fpsb(request, *args, **kwargs):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000, 999_999_999_999))[2:]
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_fpsb.html", context)


def simulation_page_spsb(request, *args, **kwargs):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000, 999_999_999_999))[2:]
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_spsb.html", context)


def simulation_page_cda(request, *args, **kwargs):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000, 999_999_999_999))[2:]
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_cda.html", context)


def main_page(request, *args, **kwargs):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000, 999_999_999_999))[2:]
    context = {"username": request.session["username"]}
    return render(request, "sim/main_page.html", context=context)
