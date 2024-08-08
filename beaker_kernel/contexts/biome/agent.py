import json
import logging
import re
import requests
from time import sleep
import asyncio

from archytas.tool_utils import AgentRef, LoopControllerRef, tool
from typing import Any

from beaker_kernel.lib.agent import BaseAgent
from beaker_kernel.lib.context import BaseContext


logger = logging.getLogger(__name__)

BIOME_URL = "http://biome_api:8082"


class BiomeAgent(BaseAgent):
    """
    You are a chat assistant that helps the analyst user with their questions. You are running inside of the Analyst UI which is a chat application
    sitting on top of a Jupyter notebook. This means the user will not be looking at code and will expect you to run code under the hood. Of course,
    power users may end up inspecting the code you you end up running and editing it.

    You have the ability to look up information regarding the environment via the tools that are provided. You should use these tools whenever are not able to
    satisfy the request to a high level of reliability. You should avoid guessing at how to do something in favor of using the provided tools to look up more
    information. Do not make assumptions, always check the documentation instead of assuming.

    You are currently working in the Biome app. The Biome app is a collection of data sources where a data source is a profiled website targeted specifically
    at cancer research. The user can add new data sources or may ask you to browser the data sources and return relevant datasets or other info. An example
    of a flow could be looking through all the data sources, picking one, finding a dataset using the URL, and then finally loading that dataset into a pandas
    dataframe.
    """
    def __init__(self, context: BaseContext = None, tools: list = None, **kwargs):
        libraries = {
        }
        super().__init__(context, tools, **kwargs)
    

    # TODO: Formatting of these messages should be left to the Analyst-UI in the future. 
    async def poll_query(self, job_id: str, format_result):
        # Poll result
        status = "queued"
        result = None
        while status == "queued" or status == "started":
            response = requests.get(f"{BIOME_URL}/jobs/{job_id}").json()
            status = response["status"]
            sleep(1)

        # Handle result
        # if status != "finished":
        #     self.context.send_response("iopub", 
        #         "job_response", {
        #             "response": f"# JOB {job_id} {status} FAILED" 
        #         },
        #     ) 
        # result = response["result"] # TODO: Bubble up better cell type
        # self.context.send_response("iopub", 
        #     "job_response", {
        #         "response": format_result(result)
        #     },
        # ) 


    @tool(autosummarize=True)
    async def search(self, query: str) -> list[dict[str, Any]]:
        """
        Search for data sources in the Biome app. Results will be matched semantically
        and string distance. Use this to find a data source. You don't need live
        web searches. If the user asks about data sources, use this tool.

        Be sure to use the `display_search` tool for the output. Ensure you always use `display_search` after.

        Args:
            query (str): The query used to find the datasource.
        Returns:
            list: A JSON-formatted string containing a list of strings.
                  The list should contain only the `name` field and no other field
                  of the data sources found, ordered from most relevant to least relevant.
                  Ensure that only the name field is present.
                  An example is provided surrounded in backticks.
                  ```
                  ["Proteomics Data Commons", ""Office of Cancer Clinical Proteomics Research", "UniProt"]
                  ```
        """

        endpoint = f"{BIOME_URL}/sources"
        response = requests.get(endpoint, params={"query": query})
        raw_sources = response.json()['sources']
        sources = [
            # Include only necessary fields to ensure LLM context length is not exceeded.
            {
                "id": source["id"],
                "name": source["content"]["Web Page Descriptions"]["name"],
                "initials": source["content"]["Web Page Descriptions"]["initials"],
                "purpose": source["content"]["Web Page Descriptions"]["purpose"],
                "links": source["content"]["Information on Links on Web Page"],
                "base_url": source.get("base_url", None)
            } for source in raw_sources
        ]
        return sources

    @tool(autosummarize=True)
    async def display_search(self, results: list[str], agent:AgentRef, loop: LoopControllerRef):
        """
        Once search has been performed, this tool will display it to the user.
        Args:
            results (list[str]): The query used to find the datasource.
        """
        # sometimes it wraps the output
        if isinstance(results, dict):
            results = results.get("results", results)
        endpoint = f"{BIOME_URL}/sources"
        response = requests.get(endpoint, params={
            "simple_query_string": {
                "fields": ["content.Web Page Descriptions.name"],
                "query": "|".join(results)
            }
        })
        raw_sources = response.json()['sources']
        sources = [
            {
                "id": source["id"],
                "name": source["content"]["Web Page Descriptions"]["name"],
                "initials": source["content"]["Web Page Descriptions"]["initials"],
                "purpose": source["content"]["Web Page Descriptions"]["purpose"],
                "links": source["content"]["Information on Links on Web Page"],
                "base_url": source.get("base_url", None),
                "logo": source.get("logo", None)
            } for source in raw_sources
        ]
        # match sources to ordering from previous llm step by dict to avoid n^2

        sources_map = { source.get("name", ""): source for source in sources }
        ordered_sources = [sources_map[name] for name in results]
        self.context.send_response("iopub",
            "data_sources", {
                "sources": ordered_sources
            },
        )
        loop.set_state(loop.STOP_SUCCESS)

    # TODO(DESIGN): Deal with long running jobs in tools
    #
    # Option 1: We can return the job id and the agent can poll for the result.
    # This will require a job status tool. Once the status is done, we can either
    # check the result if it's a query or check the data source if it's a scan.
    # This feels a bit messy though that the job creation has a similar return
    # output on queue but getting the result is very different for each job.
    #
    # Option 2: We can wait for the job and return it to the agent when it's done
    #
    # Option 3: We can maybe leverage new widgets in the Analyst UI??
    #

    # CHOOSING OPTION 1 FOR THE TIME BEING
    @tool()
    async def query_page(self, task: str, base_url: str) -> str:
        """
        Run an action over a *specific* source in the Biome app and return the results.
        Find the url from a data source by using `search` tool first and
        picking the most relevant one.

        This kicks off a long-running job so you'll have to just return the ID to the user
        instead of the result. 

        This can be used to ask questions about a data source or download some kind
        of artifact from it. This tool just kicks off a job where an AI crawls the website
        and performs the task.

        Args:
            task (str): Task given in natural language to perform over URL.
            base_url (str): URL to run query over.
        Returns:
            str: Job ID to poll for the result. 
        """
        response = requests.post( f"{BIOME_URL}/jobs/query", json={"user_task": task, "url": base_url})
        job_id = response.json()["job_id"]
        def format_result(result):
            return (
                "## Query Response\n"
                f"{result['answer']}\n\n"
                f"#### ID: {job_id}"
            )
        asyncio.create_task(self.poll_query(job_id, format_result))
        return job_id


    @tool()
    async def scan(self, base_url: str, agent:AgentRef, loop: LoopControllerRef) -> str:
        """
        Profiles the given web page and adds it to the data sources in the Biome app.

        This kicks off a long-running job so you'll have to just return the ID to the user
        instead of the result. 

        Args:
            base_url (str): The url to scan and add as a data source.
        Returns:
            str: Job ID to poll for the result. 
        """
        response = requests.post( f"{BIOME_URL}/jobs/scan", json={"uris": [base_url]})
        job_id = response.json()["job_id"]
        def format_result(_result):
            return (
                "## Scan Response\n"
                f"SUCCESS\n\n"
                f"#### ID: {job_id}"
            )
        asyncio.create_task(self.poll_query(job_id, format_result))
        return job_id