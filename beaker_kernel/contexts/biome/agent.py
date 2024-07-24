import json
import logging
import re
import requests
from time import sleep
import asyncio

from archytas.tool_utils import AgentRef, LoopControllerRef, tool

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
        if status != "finished":
            self.context.send_response("iopub", 
                "job_response", {
                    "response": f"# JOB {job_id} FAILED" 
                },
            ) 
        result = response["result"] # TODO: Bubble up better cell type
        self.context.send_response("iopub", 
            "job_response", {
                "response": format_result(result)
            },
        ) 


    @tool(autosummarize=True)
    async def search(self, query: str) -> list:
        """
        Search for data sources in the Biome app. Results will be matched semantically
        and string distance. Use this to find a data source. You don't need live
        web searches.

        Args:
            query (str): The query used to find the datasource.
        Returns:
            list: The data sources found ordered from most relevant to least relevant.
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
                "base_url": source.get("base_url", None),
            } for source in raw_sources
        ]
        return str(sources)

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

        This kicks off a long-running job so you'll have to use the ID to check on the job later. 

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

        This kicks off a long-running job so you'll have to use the ID to check on the job later. 

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