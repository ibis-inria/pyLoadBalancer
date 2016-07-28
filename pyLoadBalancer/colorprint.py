class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def cprint(text,color=None):
    if color == "HEADER" :
        color = bcolors.HEADER
    elif color == "OKBLUE":
        color = bcolors.OKBLUE
    elif color == "OKGREEN":
        color = bcolors.OKGREEN
    elif color == "WARNING":
        color = bcolors.WARNING
    elif color == "FAIL":
        color = bcolors.FAIL
    elif color == "BOLD":
        color = bcolors.BOLD
    elif color == "UNDERLINE":
        color = bcolors.UNDERLINE
    else:
        return print(text)

    return print(color + text + bcolors.ENDC)
