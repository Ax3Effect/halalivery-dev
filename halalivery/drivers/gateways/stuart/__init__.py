import requests
import json
from halalivery.static import STUART_API_KEY, STUART_BASE_URL

class StuartClient:
    api_key = STUART_API_KEY
    base_url = STUART_BASE_URL
    headers = {
        'authorization': "Bearer " + api_key,
        'content-type': "application/json"
    }

    def create_job(self, order):
        url = self.base_url + "/jobs"

        # payload = {
        #     "job": {
        #         "assignment_code": "ORDER #1",
        #         "pickups": [
        #             {
        #                 "address": "188 Ilkeston Rd, NG7 3HF, Nottingham",
        #                 "comment": "Ask order for Halalivery",
        #                 "contact": {
        #                     "firstname": "Mogul",
        #                     "lastname": "Express",
        #                     "phone": "+44 115 924 4800",
        #                     "email": "",
        #                     "company": "Mogul Express"
        #                 }
        #             }
        #         ],
        #         "dropoffs": [
        #             {
        #                 "package_type": "small",
        #                 "package_description": "The yellow one.",
        #                 "client_reference": "ORDER #1",
        #                 "address": "Apartment 82, Park West, NG71LU",
        #                 "comment": "Please call upon coming.",
        #                 "contact": {
        #                     "firstname": "Amur",
        #                     "lastname": "Murmur",
        #                     "phone": "+447845618104",
        #                     "email": "",
        #                     "company": ""
        #                 }
        #             }
        #         ]
        #     }
        # }

        payload = {
            "job": {
                "pickups": [
                    {
                        "address": "{},{},{},{}".format(order.vendor.address.street_address_1, order.vendor.address.street_address_2, order.vendor.address.city, order.vendor.address.postcode),
                        "assignment_code": "ORDER #{}".format(order.id),
                        "comment": "Ask order for order from Celery.",
                        "contact": {
                            "firstname": order.vendor.user.first_name,
                            "lastname": order.vendor.user.last_name,
                            "phone": order.vendor.address.phone,
                            "email": "",
                            "company": order.vendor.vendor_name
                        }
                    }
                ],
                "dropoffs": [
                    {
                        "package_type": "small",
                        "package_description": "Bag of groceries.",
                        "client_reference": "ORDER #{}".format(order.id),
                        "address":  "{},{},{},{}".format(order.delivery_address.street_address_1, order.delivery_address.street_address_2, order.delivery_address.city, order.delivery_address.postcode),
                        "comment": order.delivery_address.delivery_instructions,
                        "contact": {
                            "firstname": order.customer.user.first_name,
                            "lastname": order.customer.user.last_name,
                            "phone": order.delivery_address.phone,
                            "email": "",
                            "company": ""
                        }
                    }
                ]
            }
        }

        response = requests.request("POST", url, data=json.dumps(payload), headers=self.headers)
        result = json.loads(response.text)
        return result

    def validate_address(self, address, delivery_type='delivering'):
        url = self.base_url + "/addresses/validate"
        params = {'address' : '{},{},{},{}'.format(address.street_address_1, address.street_address_2, address.city, address.postcode), 'phone': '{}'.format(address.phone), 'type': delivery_type}

        result = requests.get(url, params=params, headers=self.headers)

        if result.status_code == 200:
            return True
        else:
            return False

    def job_pricing(self, vendor, customer, basket_address):
        url = self.base_url + "/jobs/pricing"
        # payload = {
        #     "job": {
        #         "assignment_code": "ORDER #1",
        #         "pickups": [
        #             {
        #                 "address": "187 Cromwell Rd, Kensington, London SW5 0SF",
        #                 "comment": "Ask order for Halalivery",
        #                 "contact": {
        #                     "firstname": "Mogul",
        #                     "lastname": "Express",
        #                     "phone": "+44 115 924 4800",
        #                     "email": "",
        #                     "company": "Mogul Express"
        #                 }
        #             }
        #         ],
        #         "dropoffs": [
        #             {
        #                 "package_type": "small",
        #                 "package_description": "The yellow one.",
        #                 "client_reference": "ORDER #1",
        #                 "address": "84 Strand, London WC2R 0DW",
        #                 "comment": "Please call upon coming.",
        #                 "contact": {
        #                     "firstname": "Amur",
        #                     "lastname": "Murmur",
        #                     "phone": "+447845618104",
        #                     "email": "",
        #                     "company": ""
        #                 }
        #             }
        #         ]
        #     }
        # }

        payload = {
            "job": {
                "pickups": [
                    {
                        "address": "{},{},{},{}".format(vendor.address.street_address_1, vendor.address.street_address_2, vendor.address.city, vendor.address.postcode),
                        "comment": "Ask order for Halalivery",
                        "contact": {
                            "firstname": vendor.user.first_name,
                            "lastname": vendor.user.last_name,
                            "phone": vendor.address.phone,
                            "email": "",
                            "company": vendor.vendor_name
                        }
                    }
                ],
                "dropoffs": [
                    {
                        "package_type": "small",
                        "address":  "{},{},{},{}".format(basket_address.street_address_1, basket_address.street_address_2, basket_address.city, basket_address.postcode),
                        "comment": basket_address.delivery_instructions,
                        "contact": {
                            "firstname": customer.user.first_name,
                            "lastname": customer.user.last_name,
                            "phone": basket_address.phone,
                            "email": "",
                            "company": ""
                        }
                    }
                ]
            }
        }
        
        response = requests.request("POST", url, data=json.dumps(payload), headers=self.headers)
        result = json.loads(response.text)
        return result.get('amount')
