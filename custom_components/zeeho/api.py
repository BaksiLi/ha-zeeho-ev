import requests
from .utils import get_cfmoto_x_param_str, get_epoch_time_str
from .const import API_BASE_URL

class ZeehoAPIClient:
    def __init__(self, authorization: str, appid: str, user_agent: str):
        self.authorization = authorization
        self.appid = appid
        self.user_agent = user_agent

    def get_base_headers(self) -> dict:
        return {
            'Host': 'tapi.zeehoev.com',
            'Authorization': self.authorization,
            'Accept-Language': 'zh-CN',
            'Appid': self.appid,
            'X-App-Info': 'MOBILE|iOS|18.0|ZEEHO_APP|2.5.20|iPhone|iPhone 14 Pro Max|1290*2796|3EEE1D62-8E74-4A2D-8091-3008D758E980|WiFi|iOS',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': self.user_agent,
        }

class ZeehoVehicleHomePageClient(ZeehoAPIClient):
    API_PATH = "vehicleHomePage"

    def __init__(self, authorization: str, cfmoto_x_sign: str, appid: str, nonce: str, signature: str, user_agent: str):
        super().__init__(authorization, appid, user_agent)
        self.cfmoto_x_sign = cfmoto_x_sign
        self.nonce = nonce
        self.signature = signature

    def get_headers(self) -> dict:
        headers = self.get_base_headers()
        headers.update({
            'Cfmoto-X-Sign': self.cfmoto_x_sign,
            'Cfmoto-X-Sign-Type': '0',
            'Nonce': self.nonce,
            'Signature': self.signature,
            'Timestamp': get_epoch_time_str(),
            'Cfmote-X-Param': get_cfmoto_x_param_str(self.appid, self.nonce),
        })
        return headers

    def get_data(self) -> dict:
        url = f"{API_BASE_URL}/{self.API_PATH}"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

class ZeehoVehicleUnlockClient(ZeehoAPIClient):
    API_PATH = "vehicleSet/network/unlock"

    def __init__(self, authorization: str, appid: str, user_agent: str):
        super().__init__(authorization, appid, user_agent)

    def get_headers(self) -> dict:
        headers = self.get_base_headers()
        headers.update({
            'content-type': 'application/json',
            'accept': '*/*',
            'interfaceversion': '2',
        })
        return headers

    def unlock_vehicle(self, secret: str) -> dict:
        url = f"{API_BASE_URL}/{self.API_PATH}"
        payload = {"secret": secret}
        response = requests.post(url, headers=self.get_headers(), json=payload)
        response.raise_for_status()
        return response.json()
