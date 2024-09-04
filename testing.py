import requests
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

def generate_pdf(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Hello, World!")
    c.save()
    buffer.seek(0) 
    return buffer

def get_access_token():
    token_url = 'https://accounts.zoho.com/oauth/v2/token'
    client_id = '1000.G3X5I57SWHT75F7LTYOYIAMELEBZCU'
    client_secret = '66c51517e1fcc097e8ea84ec4da8aff23f2db1095c'
    refresh_token = '1000.a209b7cc3fd66681b82712c6f76443fc.c58a139c51b92f8226b908fe646f8808'
    scope = 'ZohoSign.documents.ALL,ZohoSign.templates.ALL'

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'scope': scope
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
        response_data = response.json()
        if 'access_token' in response_data:
            return response_data['access_token']
        else:
            print('Access token not found in response:', response_data)
            return None
    except requests.exceptions.RequestException as e:
        print('Error fetching access token:', e)
        return None

def create_document(access_token):
    recipientName = "John Raymark LLavanes"
    recipientEmail = "john.llavanes@dexterton.com"
    pdf_buffer = generate_pdf({'example_data': 'value'})

    requestPayload = {
        "request_name": "test doc",
        "expiration_days": 10,
        "is_sequential": True,
        "notes": "Sign the document"
    }

    request = {
        "requests": requestPayload
    }

    data = json.dumps(request)
    files = {'file': ('output.pdf', pdf_buffer, 'application/pdf')}

    url = "https://sign.zoho.com/api/v1/requests"
    headers = {
        'Authorization': 'Zoho-oauthtoken ' + access_token,
    }

    try:
        response = requests.post(url, headers=headers, files=files, data={'data': data})
        jsonbody = response.json()
        print('jsonbody: ', jsonbody)

        if jsonbody['status'] == "success":
            requestId = jsonbody['requests']['request_id']
            document_id = jsonbody['requests']['document_ids'][0]['document_id']
            print('document_id: ', document_id)
            print('requestId: ', requestId)

            actionsJson = {
                "action_type": "SIGN",
                "recipient_name": recipientName,
                "recipient_email": recipientEmail,
                "verify_recipient": False,
                "verification_type": "EMAIL",
                "signing_order": 0,
                "fields": [
                    {
                        "field_name": "TextField",
                        "field_label": "Text - 1",
                        "field_type_name": "Textfield",
                        "field_category": "Textfield",
                        "document_id": document_id,
                        "action_id": requestId,
                        "is_mandatory": True,
                        "x_coord": 100,
                        "y_coord": 100,
                        "abs_width": 40,
                        "abs_height": 30,
                        "page_no": 0,
                        "default_value": True,
                        "is_read_only": False,
                    }
                ]
            }

            dataJson = {
                "actions": [actionsJson]
            }

            request = {
                "requests": dataJson
            }

            data = json.dumps(request)

            submit_url = f"https://sign.zoho.com/api/v1/requests/{requestId}/submit"
            submit_headers = {
                'Authorization': 'Zoho-oauthtoken ' + access_token,
                'Content-Type': 'application/json'
            }

            submit_response = requests.post(submit_url, headers=submit_headers, data=data)
            submit_jsonbody = submit_response.json()
            print('submit_jsonbody: ', submit_jsonbody)

            if submit_jsonbody['status'] == "success":
                created_request_id = submit_jsonbody['requests']['request_id']
                status = submit_jsonbody['requests']['request_status']
                signing_url = submit_jsonbody['requests']['signing_url']
                print(f"Signing URL: {signing_url}")
                print(status)
                print('if')
            else:
                print(submit_jsonbody['message'])
                print('else')
        else:
            print(jsonbody['message'])

    except requests.exceptions.RequestException as e:
        print('Error creating document:', e)

def main():
    access_token = get_access_token()
    if access_token:
        print('Access token:', access_token)
        create_document(access_token)
    else:
        print('Failed to obtain access token.')

if __name__ == '__main__':
    main()
