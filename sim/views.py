import random

from django.shortcuts import render, redirect


def gen_username(request):
    if "username" not in request.session:
        request.session["username"] = hex(random.randint(1_000, 999_999_999_999))[2:]


def simulation_page_dutch(request, *args, **kwargs):
    gen_username(request)
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_dutch.html", context)


def simulation_page_english(request, *args, **kwargs):
    gen_username(request)
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_english.html", context)


def simulation_page_fpsb(request, *args, **kwargs):
    gen_username(request)
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_fpsb.html", context)


def simulation_page_spsb(request, *args, **kwargs):
    gen_username(request)
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_spsb.html", context)


def simulation_page_cda(request, *args, **kwargs):
    gen_username(request)
    context = {"username": request.session["username"]}
    return render(request, "sim/sim_page_cda.html", context)


def main_page(request, *args, **kwargs):
    gen_username(request)

    context = {"username": request.session["username"]}
    return render(request, "sim/room_page.html", context=context)

def join_page(request, *args, **kwargs):
    gen_username(request)
    context = {"username": request.session["username"]}
    return render(request, "sim/join_page.html", context=context)