import logging
from random import randint
from time import time
from typing import cast

from geniusweb.actions.Accept import Accept
from geniusweb.actions.Action import Action
from geniusweb.actions.Offer import Offer
from geniusweb.actions.PartyId import PartyId
from geniusweb.bidspace.AllBidsList import AllBidsList
from geniusweb.inform.ActionDone import ActionDone
from geniusweb.inform.Finished import Finished
from geniusweb.inform.Inform import Inform
from geniusweb.inform.Settings import Settings
from geniusweb.inform.YourTurn import YourTurn
from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.Domain import Domain
from geniusweb.party.Capabilities import Capabilities
from geniusweb.party.DefaultParty import DefaultParty
from geniusweb.profile.utilityspace.LinearAdditiveUtilitySpace import (
    LinearAdditiveUtilitySpace,
)
from geniusweb.profileconnection.ProfileConnectionFactory import (
    ProfileConnectionFactory,
)
from geniusweb.progress.ProgressTime import ProgressTime
from geniusweb.references.Parameters import Parameters
from tudelft_utilities_logging.ReportToLogger import ReportToLogger

from .utils.opponent_model import OpponentModel


class Agent68(DefaultParty):
    """
    Template of a Python geniusweb agent.
    """

    def __init__(self):
        super().__init__()
        self.pareto_bids = []
        self.logger: ReportToLogger = self.getReporter()

        self.domain: Domain = None
        self.parameters: Parameters = None
        self.profile: LinearAdditiveUtilitySpace = None
        self.progress: ProgressTime = None
        self.me: PartyId = None
        self.other: str = None
        self.settings: Settings = None
        self.storage_dir: str = None
        self.current_bid: Bid = None

        self.last_received_bid: Bid = None
        self.opponent_model: OpponentModel = None
        self.logger.log(logging.INFO, "party is initialized")

    def notifyChange(self, data: Inform):
        """MUST BE IMPLEMENTED
        This is the entry point of all interaction with your agent after is has been initialised.
        How to handle the received data is based on its class type.

        Args:
            info (Inform): Contains either a request for action or information.
        """

        # a Settings message is the first message that will be send to your
        # agent containing all the information about the negotiation session.
        if isinstance(data, Settings):
            self.settings = cast(Settings, data)
            self.me = self.settings.getID()

            # progress towards the deadline has to be tracked manually through the use of the Progress object
            self.progress = self.settings.getProgress()

            self.parameters = self.settings.getParameters()
            self.storage_dir = self.parameters.get("storage_dir")

            # the profile contains the preferences of the agent over the domain
            profile_connection = ProfileConnectionFactory.create(
                data.getProfile().getURI(), self.getReporter()
            )
            self.profile = profile_connection.getProfile()
            self.domain = self.profile.getDomain()
            profile_connection.close()
            self.determine_good_utility()

        # ActionDone informs you of an action (an offer or an accept)
        # that is performed by one of the agents (including yourself).
        elif isinstance(data, ActionDone):
            action = cast(ActionDone, data).getAction()
            actor = action.getActor()

            # ignore action if it is our action
            if actor != self.me:
                # obtain the name of the opponent, cutting of the position ID.
                self.other = str(actor).rsplit("_", 1)[0]

                # process action done by opponent
                self.opponent_action(action)
        # YourTurn notifies you that it is your turn to act
        elif isinstance(data, YourTurn):
            # execute a turn
            self.my_turn()

        # Finished will be send if the negotiation has ended (through agreement or deadline)
        elif isinstance(data, Finished):
            self.save_data()
            # terminate the agent MUST BE CALLED
            self.logger.log(logging.INFO, "party is terminating:")
            super().terminate()
        else:
            self.logger.log(logging.WARNING, "Ignoring unknown info " + str(data))

    def getCapabilities(self) -> Capabilities:
        """MUST BE IMPLEMENTED
        Method to indicate to the protocol what the capabilities of this agent are.
        Leave it as is for the ANL 2022 competition

        Returns:
            Capabilities: Capabilities representation class
        """
        return Capabilities(
            set(["SAOP"]),
            set(["geniusweb.profile.utilityspace.LinearAdditive"]),
        )

    def send_action(self, action: Action):
        """Sends an action to the opponent(s)

        Args:
            action (Action): action of this agent
        """
        self.getConnection().send(action)

    # give a description of your agent
    def getDescription(self) -> str:
        """MUST BE IMPLEMENTED
        Returns a description of your agent. 1 or 2 sentences.

        Returns:
            str: Agent description
        """
        return "Template agent for the ANL 2022 competition"

    def opponent_action(self, action):
        """Process an action that was received from the opponent.

        Args:
            action (Action): action of opponent
        """
        # if it is an offer, set the last received bid
        if isinstance(action, Offer):
            # create opponent model if it was not yet initialised
            if self.opponent_model is None:
                self.opponent_model = OpponentModel(self.domain)

            bid = cast(Offer, action).getBid()

            # update opponent model with bid
            self.opponent_model.update(bid)
            # set bid as last received
            self.last_received_bid = bid

    def my_turn(self):
        """This method is called when it is our turn. It should decide upon an action
        to perform and send this action to the opponent.
        """
        self.current_bid = self.find_bid()
        # check if the last received offer is good enough
        if self.accept_condition(self.last_received_bid):
            # if so, accept the offer
            action = Accept(self.me, self.last_received_bid)
        else:
            # if not, find a bid to propose as counter offer
            action = Offer(self.me, self.current_bid)

        # send the action
        self.send_action(action)

    def save_data(self):
        """This method is called after the negotiation is finished. It can be used to store data
        for learning capabilities. Note that no extensive calculations can be done within this method.
        Taking too much time might result in your agent being killed, so use it for storage only.
        """
        data = "Data for learning (see README.md)"
        with open(f"{self.storage_dir}/data.md", "w") as f:
            f.write(data)

    ###########################################################################################
    ################################## Example methods below ##################################
    ###########################################################################################

    def determine_good_utility(self):
        """Determines the quantile utility by selecting the utility of the 75th highest bid out of 500 random bids."""
        
        domain = self.profile.getDomain()
        all_bids = AllBidsList(domain)

        utilities = []
        # Take random 10% of all bids
        all_bids_size = int(all_bids.size() * 0.1)
        for _ in range(all_bids_size):
            bid = all_bids.get(randint(0, all_bids.size() - 1))
            utilities.append(float(self.profile.getUtility(bid))) 
        
        utilities.sort(reverse=True)

        top_5 = int(all_bids_size*0.02)
        top_10_percent = utilities[:top_5] 
        self.good_utility_threshold = top_10_percent[-1]


    def accept_condition(self, bid: Bid) -> bool:
        if bid is None:
            return False

        ## get progress
        progress = self.progress.get(time() * 1000)

        ## get reservation value, if none, then 0.4
        reservation_bid = self.profile.getReservationBid()
        reservation_value = float(self.profile.getUtility(reservation_bid)) if reservation_bid is not None else 0.4

        ## get utilities
        bid_utility = float(self.profile.getUtility(bid))  
        current_bid_utility = float(self.profile.getUtility(self.current_bid))  

        conditions = [
            ## first period: accept next or accept if better than the calculated 90th percentile
            progress < 0.5 and current_bid_utility < bid_utility,
            progress < 0.5 and bid_utility > self.good_utility_threshold,
            ## second period: accept next, accept if social welfare is more than 0.8 * 90th percentile * 2,
            ## or accept if self utility is more than 0.8 * 90th percentile
            progress < 0.995 and current_bid_utility < bid_utility,
            progress < 0.995 and self.score_bid(bid) > self.good_utility_threshold * 0.8 * 2,
            progress < 0.995 and bid_utility > self.good_utility_threshold * 0.8,
            ##  third period: accept if bid utility is more than the reservation value (last second deal)
            progress > 0.995 and bid_utility > reservation_value,
        ]
        return any(conditions)

    
    def find_bid(self) -> Bid:
        domain = self.profile.getDomain()
        all_bids = AllBidsList(domain)

        # Initialize lists to store candidate bids and new Pareto-efficient bids
        candidate_bids = []
        pareto_bids = []
        # Generate 10% of the total bids random bids and evaluate their utility for both the agent and the opponent
        for _ in range(int(all_bids.size() * 0.1)):  
            bid = all_bids.get(randint(0, all_bids.size() - 1))
            our_utility = self.profile.getUtility(bid)
            opponent_utility = self.opponent_model.get_predicted_utility(bid) if self.opponent_model is not None else 0
            candidate_bids.append((bid, our_utility, opponent_utility))

        # Filter out non-Pareto-efficient bids
        for bid, our_utility, opponent_utility in candidate_bids:
            # A bid is Pareto-efficient if there is no other bid that dominates it in both utilities
            if not any(
                (other_our_utility >= our_utility and other_opponent_utility > opponent_utility) or
                (other_our_utility > our_utility and other_opponent_utility >= opponent_utility)
                for _, other_our_utility, other_opponent_utility in candidate_bids
            ):
                # If the bid is Pareto-efficient, add it to the new Pareto frontier
                pareto_bids.append((bid, our_utility, opponent_utility))

        # If there are Pareto-efficient bids, select the one with the highest score
        if pareto_bids:
            return max(pareto_bids, key=lambda x: self.score_bid(x[0]))[0]

        # If no Pareto-efficient bids are found, return the first candidate bid
        return candidate_bids[0][0]


    def score_bid(self, bid: Bid, alpha: float = 0.95, eps: float = 0.1) -> float:
        """Calculate heuristic score for a bid

        Args:
            bid (Bid): Bid to score
            alpha (float, optional): Trade-off factor between self interested and
                altruistic behaviour. Defaults to 0.95.
            eps (float, optional): Time pressure factor, balances between conceding
                and Boulware behaviour over time. Defaults to 0.1.

        Returns:
            float: score
        """
        ## get progress
        progress = self.progress.get(time() * 1000)

        ## get utility
        our_utility = float(self.profile.getUtility(bid))

        ## calculate the time pressure 
        time_pressure = 1.0 - progress ** (1 / eps)

        ## calculate the self bid score depending on the time pressure
        score = alpha * time_pressure * our_utility

        ## if there is opponent modelling, calculate the score including the time 
        ## pressure and add it to the score
        if self.opponent_model is not None:
            opponent_utility = self.opponent_model.get_predicted_utility(bid)
            opponent_score = (1.0 - alpha * time_pressure) * opponent_utility
            score += opponent_score
        return score
