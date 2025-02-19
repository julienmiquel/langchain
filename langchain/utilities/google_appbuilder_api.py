import json
import logging
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, Extra, root_validator

from langchain.utils import get_from_dict_or_env


class GoogleAppBuilderAPIWrapper(BaseModel):
    """Wrapper around Google AppBuilder API.

    To use, you should have
     **an API key for the google AppBuilder platform**,
     and the enviroment variable ''GAPP_BUILDER_API_KEY''
     set with your API key , or pass 'gappbuilders_api_key'
     as a named parameter to the constructor.

    By default, this will return the all the results on the input query.
     You can use the top_k_results argument to limit the number of results.

    Example:
        .. code-block:: python


            from langchain import GoogleAppBuilderAPIWrapper
            gappbuilderapi = GoogleAppBuilderAPIWrapper()
    """

    gappbuilders_api_key: Optional[str] = None
    google_map_client: Any  #: :meta private:
    top_k_results: Optional[int] = 5
    gappbuilders_ds_url = ""

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid
        arbitrary_types_allowed = True

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that api key is in your environment variable."""
        gappbuilders_ds_url = get_from_dict_or_env(
            values, "gappbuilders_ds_url", "GAPP_BUILDER_DS_URL"
        )
        values["gappbuilders_ds_url"] = gappbuilders_ds_url

        return values

    def get_token(self) -> str:
        import google.auth
        import google.auth.transport.requests

        creds, project = google.auth.default()

        # creds.valid is False, and creds.token is None
        # Need to refresh credentials to populate those

        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        return creds.token

    def run(self, query: str) -> str:
        """Run appbuilders search and get k number of appbuilders that exists that match."""

        token = self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

        num_to_return = 2
        page_size = num_to_return

        data = {"query": query, "page_size": f"{page_size}", "offset": 0}

        response = requests.post(
            self.gappbuilders_ds_url, data=json.dumps(data), headers=headers
        )

        search_results = json.loads(response.text)
        search_results = search_results.get("results", {})

        num_to_return = len(search_results)
        print(f"num_to_return:{num_to_return}")
        appbuilders = []

        if num_to_return == 0:
            return "Google appbuilders did not find any appbuilders that match the description"

        for i in range(num_to_return):
            result = search_results[id == i]
            details = self.fetch_appbuilder_details(result)

            if details is not None:
                appbuilders.append(details)

        answer = "\n".join([f"{i+1}. {item}" for i, item in enumerate(appbuilders)])
        if len(answer) > 1024:
            answer = answer[:1024]

        return f"""
                thought: I have find: 
                {answer}
                action: summarize answer and provide url link 
                action_input:  """

    def fetch_appbuilder_details(self, prediction: str) -> Optional[str]:
        try:
            derivedStructData = prediction.get("document", {}).get(
                "derivedStructData", {}
            )

            return self.format_appbuilder_details(derivedStructData)
        except Exception as e:
            logging.error(f"An Error occurred while fetching appbuilder details: {e}")
            return None

    def format_appbuilder_details(
        self, appbuilder_details: Dict[str, Any]
    ) -> Optional[str]:
        try:
            title = appbuilder_details.get("title", "")

            formatted_details = title + " \n " + self.format_array(appbuilder_details)

            return formatted_details
        except Exception as e:
            logging.error(f"An error occurred while formatting appbuilder details: {e}")
            return None

    def format_array(self, appbuilder_details) -> str:
        formatted_details = ""

        try:
            if isinstance(appbuilder_details, str):
                return appbuilder_details
            if isinstance(appbuilder_details, Dict):
                keys = appbuilder_details.keys()
                for key in keys:
                    value = appbuilder_details[key]

                    if isinstance(value, str):
                        if "http" in value:
                            print(value)
                        else:
                            formatted_details = (
                                f"{formatted_details} \n {key} : {value}"
                            )
                    else:
                        # formatted_details_sub =  self.format_array(value)
                        formatted_details = f"{formatted_details} \n {key} : {value}"

                return formatted_details
            else:
                if isinstance(appbuilder_details, list):
                    values = []
                    for value in appbuilder_details:
                        value_str = self.format_array(value)
                        values.append(value_str)

                    return f"{', '.join(values)}"

                return ""
        except Exception as e:
            print(f"ERROR format_array  {e}")
            return appbuilder_details
        except:
            print(f"FATAL format_array  {e}")
            return appbuilder_details
