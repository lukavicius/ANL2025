import json
import os
from pathlib import Path
import time

from utils.runners import run_tournament

RESULTS_DIR = Path("results", time.strftime('%Y%m%d-%H%M%S'))

# create results directory if it does not exist
if not RESULTS_DIR.exists():
    RESULTS_DIR.mkdir(parents=True)

# Settings to run a negotiation session:
#   You need to specify the classpath of 2 agents to start a negotiation. Parameters for the agent can be added as a dict (see example)
#   You need to specify the preference profiles for both agents. The first profile will be assigned to the first agent.
#   You need to specify a time deadline (is milliseconds (ms)) we are allowed to negotiate before we end without agreement.
tournament_settings = {
    "agents": [
        {
            "name" : "Agent007",
            "class": "agents_test.agent007.agent007.Agent007",
            "parameters": {"storage_dir": "agents_test/storage_dir/Agent007"},
        },
        {
            "name" : "Agent24",
            "class": "agents_test.agent24.agent24.Agent24",
            "parameters": {"storage_dir": "agents_test/storage_dir/Agent24"},
        },
        {
            "name" : "Agent68",
            "class": "agents_test.agent68.agent68.Agent68",
            "parameters": {"storage_dir": "agents_test/storage_dir/Agent68"},
        },
        {
            "name" : "BoulwareAgent",
            "class": "agents_test.boulware_agent.boulware_agent.BoulwareAgent",
            "parameters": {"storage_dir": "agents_test/storage_dir/BoulwareAgent"},
        },
        {
            "name" : "ConcederAgent",
            "class": "agents_test.conceder_agent.conceder_agent.ConcederAgent",
            "parameters": {"storage_dir": "agents_test/storage_dir/ConcederAgent"},
        },
        {
            "name" : "DreamTeam109Agent",
            "class": "agents_test.dreamteam109_agent.dreamteam109_agent.DreamTeam109Agent",
            "parameters": {"storage_dir": "agents_test/storage_dir/DreamTeam109Agent"},
        },
        {
            "name" : "LinearAgent",
            "class": "agents_test.linear_agent.linear_agent.LinearAgent",
            "parameters": {"storage_dir": "agents_test/storage_dir/LinearAgent"},
        },
        {
            "name" : "RandomAgent",
            "class": "agents_test.random_agent.random_agent.RandomAgent",
            "parameters": {"storage_dir": "agents_test/storage_dir/RandomAgent"},
        },
        {
            "name" : "StupidAgent",
            "class": "agents_test.stupid_agent.stupid_agent.StupidAgent",
            "parameters": {"storage_dir": "agents_test/storage_dir/StupidAgent"},
        },
        {
            "name" : "ChargingBoul",
            "class": "agents_test.charging_boul.charging_boul.ChargingBoul",
            "parameters": {"storage_dir": "agents_test/storage_dir/ChargingBoul"},
        }
    ],
    "profile_sets": [
        ["domains/domain00/profileA.json", "domains/domain00/profileB.json"],
        ["domains/domain01/profileA.json", "domains/domain01/profileB.json"],
    ],
    "deadline_time_ms": 10000,
}

# run a session and obtain results in dictionaries
tournament_steps, tournament_results, tournament_results_summary = run_tournament(tournament_settings)

# save the tournament settings for reference
with open(RESULTS_DIR.joinpath("tournament_steps.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(tournament_steps, indent=2))
# save the tournament results
with open(RESULTS_DIR.joinpath("tournament_results.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(tournament_results, indent=2))
# save the tournament results summary
tournament_results_summary.to_csv(RESULTS_DIR.joinpath("tournament_results_summary.csv"))
