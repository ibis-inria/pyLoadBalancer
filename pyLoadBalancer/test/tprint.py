from colorama import Fore, Back, Style, init
init()


def tprint(text, color='', nexttext=''):
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

    return print(Fore.YELLOW + Style.BRIGHT, "- TEST -", color, text, Style.RESET_ALL)
