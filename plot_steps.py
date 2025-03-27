import json
import matplotlib.pyplot as plt

def plot_bids(filename, output_file="bids_plot.png"):
    print(f"Processing file: {filename}")
    print(f"Saving plot as: {output_file}")
    
    # Load JSON data
    with open(filename, 'r') as file:
        data = json.load(file)
    
    agents = set()
    for action in data["actions"]:
        if "Offer" in action:
            agents.update(action["Offer"]["utilities"].keys())
    
    agent1, agent2 = list(agents)[:2]  # Extract first two agents dynamically
    
    agent1_utilities_Agent1 = []
    agent2_utilities_Agent1 = []
    agent1_utilities_Agent2 = []
    agent2_utilities_Agent2 = []
    
    # Extract utilities from each offer
    for action in data["actions"]:
        if "Offer" in action:
            utilities = action["Offer"]["utilities"]
            agent = action["Offer"]["actor"]
            
            if agent == agent1:
                agent1_utilities_Agent1.append(utilities[agent1])
                agent2_utilities_Agent1.append(utilities[agent2])
            else:
                agent1_utilities_Agent2.append(utilities[agent1])
                agent2_utilities_Agent2.append(utilities[agent2])
    
    # Plot the utilities
    plt.figure(figsize=(8, 6))
    
    # Connect dots with lines for Agent1
    plt.plot(agent1_utilities_Agent1, agent2_utilities_Agent1, color='blue', label=f'{agent1} Bids', marker='o')
    # Connect dots with lines for Agent2
    plt.plot(agent1_utilities_Agent2, agent2_utilities_Agent2, color='red', label=f'{agent2} Bids', marker='o')
    
    # Highlight last bid and connect it to both sides
    if agent1_utilities_Agent1 or agent1_utilities_Agent2:
        last_agent1 = agent1_utilities_Agent1[-1] if agent1_utilities_Agent1 else agent1_utilities_Agent2[-1]
        last_agent2 = agent2_utilities_Agent1[-1] if agent2_utilities_Agent1 else agent2_utilities_Agent2[-1]
        
        # Draw line to connect last bid to both sides
        if agent1_utilities_Agent1:
            plt.plot([agent1_utilities_Agent1[-2], last_agent1], [agent2_utilities_Agent1[-2], last_agent2], color='blue')
        if agent1_utilities_Agent2:
            plt.plot([agent1_utilities_Agent2[-2], last_agent1], [agent2_utilities_Agent2[-2], last_agent2], color='red')
        
        # Plot the last bid with a larger circle
        plt.scatter(last_agent1, last_agent2, color='green', s=100, edgecolors='black', label='Last Bid')
    
    plt.xlabel(f"{agent1} Utility")
    plt.ylabel(f"{agent2} Utility")
    plt.title("Bids Over Time")
    plt.legend(loc='lower left')
    plt.grid()
    
    # Save plot to file
    plt.savefig(output_file)
    plt.show()

# Use this to divert the path
plot_bids("results/20250327-163512/session_results_trace.json")
