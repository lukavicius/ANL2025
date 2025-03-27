from collections import defaultdict
import csv
import glob
import json
import os
import random
import shutil
import time
from pathlib import Path

from matplotlib import pyplot as plt
import pandas as pd

from utils.plot_trace import plot_trace
from utils.runners import run_session

RESULTS_DIR = Path("regular_results", time.strftime('%Y%m%d-%H%M%S'))

# create results directory if it does not exist
if not RESULTS_DIR.exists():
    RESULTS_DIR.mkdir(parents=True)

# Settings to run a negotiation session:
#   You need to specify the classpath of 2 agents to start a negotiation. Parameters for the agent can be added as a dict (see example)
#   You need to specify the preference profiles for both agents. The first profile will be assigned to the first agent.
#   You need to specify a time deadline (is milliseconds (ms)) we are allowed to negotiate before we end without agreement

our_agent = {
        "name" : "Agent68",
        "class": "agents.agent68.agent68.Agent68",
        "parameters": {"storage_dir": "agents_test/storage_dir/Agent68"},
    }
agents = [
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
        "name" : "Agent55",
        "class": "agents_test.agent55.agent55.Agent55",
        "parameters": {"storage_dir": "agents_test/storage_dir/Agent55"},
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
]

numbers = [f"{i:02}" for i in range(50)]
random_selection = random.sample(numbers, 2)

overall_results = []
for i in range(len(agents)):
    for j in range(len(random_selection)):
        settings = {
            "agents": [
                our_agent,
                agents[i],
            ],
            "profiles": ["domains/domain" + random_selection[j] + "/profileA.json", "domains/domain" + random_selection[j] + "/profileB.json"],
            "deadline_time_ms": 10000,
        }

        session_results_trace, session_results_summary = run_session(settings)
        last_round_results = {
            "agent_1": session_results_summary["agent_" + str(i * 4 + j * 2 + 1)],
            "agent_2": session_results_summary["agent_" + str(i * 4 + j * 2 + 2)],
            "utility_1": session_results_summary["utility_" + str(i * 4 + j * 2 + 1)],
            "utility_2": session_results_summary["utility_" + str(i * 4 + j * 2 + 2)],
            "nash_product": session_results_summary["nash_product"],
            "social_welfare": session_results_summary["social_welfare"],
            "agreement": session_results_summary["result"],
        }
        overall_results.append(last_round_results)

aggregated_results = defaultdict(lambda: {
    "utility_1": 0, "utility_2": 0, "nash_product": 0,
    "social_welfare": 0, "agreement_count": 0, "count": 0
})

# Aggregate values
for result in overall_results:
    key = (result["agent_1"], result["agent_2"])
    aggregated_results[key]["utility_1"] += result["utility_1"]
    aggregated_results[key]["utility_2"] += result["utility_2"]
    aggregated_results[key]["nash_product"] += result["nash_product"]
    aggregated_results[key]["social_welfare"] += result["social_welfare"]
    aggregated_results[key]["agreement_count"] += 1 if result["agreement"] == "agreement" else 0  # Convert to int for counting
    aggregated_results[key]["count"] += 1

# Compute averages and format final results
final_results = []
for (agent_1, agent_2), values in aggregated_results.items():
    count = values["count"]
    final_results.append({
        "agent_1": agent_1,
        "agent_2": agent_2,
        "utility_1": values["utility_1"] / count,
        "utility_2": values["utility_2"] / count,
        "nash_product": values["nash_product"] / count,
        "social_welfare": values["social_welfare"] / count,
        "agreement_count": values["agreement_count"],  # Total agreements
    })

# write results to file

df = pd.DataFrame(final_results)

average_row = df.mean(numeric_only=True).to_dict()
average_row["agent_1"] = "Average"
average_row["agent_2"] = "Average"

# Append the average row to the DataFrame
df = pd.concat([df, pd.DataFrame([average_row])], ignore_index=True)

# Save DataFrame to CSV
df.to_csv(RESULTS_DIR.joinpath("regular_results_summary.csv"), index=False)


