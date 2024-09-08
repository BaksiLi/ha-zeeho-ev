import requests
import json
from .utils import get_cfmoto_x_param_str, get_epoch_time_str
from .const import API_BASE_URL
API_PATH_VEHICLE_HOME = "vehicleHomePage"
API_URL = f"{API_BASE_URL}/{API_PATH_VEHICLE_HOME}"

class ZeehoAccount:
    def __init__(self, authorization: str, cfmoto_x_sign: str, appid: str, nonce: str, signature: str, user_agent: str):
        self.authorization = authorization
        self.cfmoto_x_sign = cfmoto_x_sign
        self.appid = appid
        self.nonce = nonce
        self.signature = signature
        self.user_agent = user_agent

    def get_headers(self) -> dict:
        return {
            'Host': 'tapi.zeehoev.com',
            'Authorization': self.authorization,
            'Accept-Language': 'zh-CN',
            'Cfmoto-X-Sign': self.cfmoto_x_sign,
            'Cfmoto-X-Sign-Type': '0',
            'Appid': self.appid,
            'Nonce': self.nonce,
            'Signature': self.signature,
            'Timestamp': get_epoch_time_str(),
            'Cfmote-X-Param': get_cfmoto_x_param_str(self.appid, self.nonce),
            'X-App-Info': 'MOBILE|iOS|18.0|ZEEHO_APP|2.5.20|iPhone|iPhone 14 Pro Max|1290*2796|3EEE1D62-8E74-4A2D-8091-3008D758E980|WiFi|iOS',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': self.user_agent,
        }

    def get_data(self, url: str) -> dict:
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def post_data(self, url: str, data: dict) -> dict:
        response = requests.post(url, headers=self.get_headers(), data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    
    def unlock_vehicle(self, secret: str) -> dict:
        url = "https://tapi.zeehoev.com/v1.0/app/cfmotoserverapp/vehicleSet/network/unlock"
        headers = self.get_headers()
        headers.update({
            'content-type': 'application/json',
            'accept': '*/*',
            'interfaceversion': '2',
        })
        
        payload = {"secret": secret}
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
