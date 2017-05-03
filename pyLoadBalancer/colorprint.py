#!/usr/bin/env python
# -*- coding: utf-8 -*-

from colorama import Fore, Back, Style, init
init()


def cprint(text, color='', nexttext=''):
    if color == "OKBLUE":
        color = Fore.BLUE + Style.BRIGHT
    elif color == "OKGREEN":
        color = Fore.GREEN + Style.BRIGHT
    elif color == "WARNING":
        color = Fore.YELLOW + Style.BRIGHT
    elif color == "FAIL":
        color = Fore.RED + Style.BRIGHT
    else:
        return print(text, nexttext)

    return print(color, text, Style.RESET_ALL, nexttext)
