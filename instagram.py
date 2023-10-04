from urllib.parse import urlencode, urlunparse
import requests, logging


class Instagram:

    #find the things that never change like the api endpoits and define them here
    AUTHORIZE_URL = "https://api.instagram.com/oauth/authorize"
    ACCESS_TOKEN_URL = "https://graph.instagram.com/access_token" #exchange an access token to a long duration one
    ME_URL = "https://graph.instagram.com/v18.0/me"
    GRAPH_URL = "https://graph.instagram.com/" #{media-id}/children
    OAUTH_ACCESS_TOKEN_URL = "https://api.instagram.com/oauth/access_token" #gets a short access token from IG
    OAUTH_AUTHORIZE_URL = "https://api.instagram.com/oauth/authorize"
    REFRESH_ACCESS_TOKEN_URL = "https://graph.instagram.com/refresh_access_token" #GET request
    USER_URL = "https://graph.instagram.com/v18.0/"  #{api-version}/{user-id}
    #USER_MEDIA_URL = "https://graph.instagram.com/{api-version}/{user-id}/media"


    def call_api(self, endpoint, mode, params):
        """Takes the API endpoint (selected or built from constants above), mode='GET or POST', expected api parameters"""
        #logging.basicConfig(level=logging.DEBUG)

        if mode.lower() == "get":
            response = requests.get(endpoint, params=params)
        elif mode.lower() == "post":
            response = requests.post(endpoint, data=params)
         


        # logging.debug(f"Request URL: {response.request.url}")
        # logging.debug(f"Request Headers: {response.request.headers}")
        # logging.debug(f"Request Body: {response.request.body}")
        # logging.debug(f"Response Status Code: {response.status_code}")
        # logging.debug(f"Response Headers: {response.headers}")
        # logging.debug(f"Response Text: {response.text}")

        return response


    def authenticate_user(self, redirect_uri=None):
        """takes an optional redirect_uri kwarg, if it's not passed, then it attempts to find it as an instance property.
        We have to actually authenticate a user on their website, so this only returns a URL to use redirect the app.
        """
        if redirect_uri is None:
            #a redirect uri is not passed, use the property value, if it's incorrectly set, the API call will fail
            redirect_uri = self.redirect_uri

        auth_params = {
            "client_id" : self.client_id,
            "redirect_uri" : redirect_uri,
            "scope": "user_profile, user_media",
            "response_type": "code"
        }
        request_url = f"{self.AUTHORIZE_URL}/?{urlencode(auth_params)}"
        return request_url

    def get_access_token(self, code):
        """exchanges the code returned from the OAuth request for a short lived access token.
        This code will have a #_ appended to it, the API expects it to be removed when the request is made. """

        #store the code in case the short lived token is invalid, this way we can error out, and re-try before failing
        #remove the apended #_ from the code that is passed as a query arg
        self.code = code.replace("#_", "")


        #short lived tokens are good for an hour. It's possible we already have one, but for now we're not storing any
        #information about when that particular token was acquired, so we just return and proceed to attempt to exchange
        #that token for a long-lived one. If the short lived token is invalid, it can error out during exchange, and we can
        #re-set it to none, and then use the self.code we just got to attempt to get a new one before proceeding.
        if self.short_lived_token is not None:
            # a short lived token has been set in this instance
            print ("\n\n\n\n A SHORT LIVED TOKEN ALREADY EXISTS \n\n\n\n")
            print(self.short_lived_token)
            return



        #after login and getting a code with OAuth, this request gets a short-lived auth token for our user
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri, #set at login so it matches exactly,
            "code": self.code
        }
        response = self.call_api(endpoint=self.OAUTH_ACCESS_TOKEN_URL,
                                 mode="post", #the Instagram/Facebook graph expects a post request
                                 params=params)



        if response.status_code == 200:
            response_data = response.json()
            self.user_id = response_data["user_id"] #will likely be more useful when a database with a user table is attached
            self.short_lived_token = response_data["access_token"] #valid for about 1 hour
        else:
            print(f'POST request failed for authenticate_user: {response.status_code}')
            print('Response content:')
            print(response.content.decode('utf-8'))  # Print the content as a string

        return

    def exchange_access_token(self, short_token=None):
        """exchanges a short lived token for a long lived one. If a short lived token is not passed,
        it checks to see if one is saved in this instance, if one is saved is it uses that one. If the 
        short token is missing altogether, the API will return an error code."""

        if short_token is None:
            #if it's not passed, try and see if the object already has it stored
            short_token = self.short_lived_token

        print("\n\n\n\n\n Attempting to echange this token:")
        print (short_token)
        print("\n\n\n\n\n")

        #API request stuff here

        params = {
            "grant_type":"ig_exchange_token",
            "client_id": self.client_id,
            "client_secret":self.client_secret,
            "access_token":short_token
        }

        response = self.call_api(mode="get", endpoint=self.ACCESS_TOKEN_URL, params=params)


        if response.status_code == 200:
            response_data = response.json()
            self.long_lived_access_token = response_data["access_token"]
            self.lla_token_details = response_data
        else:
            print(f'GET request failed for exchange_access_token: {response.status_code}')
            print('Response content:')
            print(response.content.decode('utf-8'))  # Print the content as a string

        #successful API request will return a long lived token, with a number of seconds for how long it's valid
        #figure out how to store the current time in seconds and when it's invalid, store it all
        #and then write the helper method to automatically check when it expires so we know to renew it when we load
        #the instagram content

        """
        {
          "access_token":"{long-lived-user-access-token}",
          "token_type": "bearer",
          "expires_in": 5183944  // Number of seconds until token expires
        }
        """


        return

    def get_user_media(self, limit=25):

        user_url_endpoint = f"{self.ME_URL}/media"

        params = {
            "fields" : "id,permalink,caption,media_url,timestamp,media_type,thumbnail_url, children{media_url, thumbnail_url, media_type}",
            "access_token" : self.long_lived_access_token,
            "limit": limit
        }

        response = self.call_api(endpoint=user_url_endpoint, mode="get", params=params)
        response_data = response.json()

        return response_data

    def __init__(self, client_id, client_secret, redirect_uri=None, sl_at = None, ll_at=None):
        #needs to initialize using the clientid and secret
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.short_lived_token = sl_at
        self.long_lived_access_token = ll_at