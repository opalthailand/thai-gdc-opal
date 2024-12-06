import requests

def noti():
    url = 'https://notify-api.line.me/api/notify'
    token = "cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Bearer ' + token
    }
    msg = f'CKAN'
    response = requests.post(url, headers=headers, data={'message': msg})


class MyLogic():

    def do_something():
        noti()
        return "OOOOOPPPPPPAAAALLLLLLL"