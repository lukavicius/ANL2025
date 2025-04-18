import logging
import numpy as np

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

from agents.agent68.utils.opponent_model import OpponentModel


class RGAgent(DefaultParty):
    """
    @brief: Raviv-Gavriely negotiation agent of a Python GeniusWeb agent.
    """

    def __init__(self) -> None:
        super().__init__()
        self.logger: ReportToLogger = self.getReporter()

        self.domain: Domain = None
        self.parameters: Parameters = None
        self.profile: LinearAdditiveUtilitySpace = None
        self.progress: ProgressTime = None
        self.me: PartyId = None
        self.other: str = None
        self.settings: Settings = None
        self.storage_dir: str = None

        self.last_received_bid: Bid = None
        self.opponent_model: OpponentModel = None
        self.logger.log(logging.INFO, "party is initialized")

        # Our parameters:
        self.max_acceptance_threshold = 0.9  # From optimal
        self.min_acceptance_threshold = 0.5  # From optimal
        self.compromising_factor = 4  # Higher value means compromise later
        self.bids_to_consider = 800
        self.optimal_bid = None
        self.best_opponent_bid = None
        self.all_previous_bids = []

    def notifyChange(self, data: Inform) -> None:
        """
        @brief: Notify on a change.

        This is the entry point of all interaction with your agent after is has been initialized.
        How to handle the received data is based on its class type.

        @param info: Contains either a request for action or information.

        @return: None.
        """

        # A Settings message is the first message that will be send to your
        # agent containing all the information about the negotiation session.
        if isinstance(data, Settings):
            self.settings = cast(Settings, data)
            self.me = self.settings.getID()

            # Progress towards the deadline has to be tracked manually through the use of the Progress object
            self.progress = self.settings.getProgress()

            self.parameters = self.settings.getParameters()
            self.storage_dir = self.parameters.get("storage_dir")

            # The profile contains the preferences of the agent over the domain
            profile_connection = ProfileConnectionFactory.create(
                data.getProfile().getURI(), self.getReporter()
            )
            self.profile = profile_connection.getProfile()
            self.domain = self.profile.getDomain()
            # Calculate best bid and threshold:
            all_bids = AllBidsList(self.profile.getDomain())
            optimal_bid = (None, 0)
            for current_bid in all_bids:
                current_bid_utility = self.profile.getUtility(current_bid)
                if current_bid_utility > optimal_bid[1]:
                    optimal_bid = (current_bid, current_bid_utility)
            self.optimal_bid = optimal_bid[0]
            self.max_acceptance_threshold *= float(optimal_bid[1])
            self.min_acceptance_threshold *= float(optimal_bid[1])

            profile_connection.close()

        # ActionDone informs you of an action (an offer or an accept)
        # that is performed by one of the agents (including yourself).
        elif isinstance(data, ActionDone):
            action = cast(ActionDone, data).getAction()
            actor = action.getActor()

            # Ignore action if it is our action
            if actor != self.me:
                # Obtain the name of the opponent, cutting of the position ID.
                self.other = str(actor).rsplit("_", 1)[0]

                # Process action done by opponent
                self.opponent_action(action)
        # YourTurn notifies you that it is your turn to act
        elif isinstance(data, YourTurn):
            # Execute a turn
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
        """
        @brief: Returns the capability of the agent.

        Method to indicate to the protocol what the capabilities of this agent are.

        @return: Capabilities representation class.
        """
        return Capabilities(
            set(["SAOP"]),
            set(["geniusweb.profile.utilityspace.LinearAdditive"]),
        )

    def send_action(self, action: Action) -> None:
        """
        @brief: Sends an action to the opponent(s).

        @param action: action of this agent

        @return: None.
        """
        self.getConnection().send(action)

    def getDescription(self) -> str:
        """
        @brief: Returns a description of your agent.

        @return: Agent description.
        """
        return "Raviv-Gavriely description for the ANL 2022 competition"

    def opponent_action(self, action: Action) -> None:
        """
        @brief: Process an action that was received from the opponent.

        @param: Action of opponent.

        @return: None.
        """
        # If it is an offer, set the last received bid:
        if isinstance(action, Offer):
            # Create opponent model if it was not yet initialized
            if self.opponent_model is None:
                self.opponent_model = OpponentModel(self.domain)

            bid = cast(Offer, action).getBid()

            # Update opponent model with bid
            self.opponent_model.update(bid)
            # Set bid as last received
            self.last_received_bid = bid
            # Keep track of all the bids and which bid is the best
            self.all_previous_bids.append(bid)
            if self.best_opponent_bid is None:
                self.best_opponent_bid = bid
            if self.profile.getUtility(bid) > self.profile.getUtility(self.best_opponent_bid):
                self.best_opponent_bid = bid

    def my_turn(self) -> None:
        """
        @brief: My turn.

        This method is called when it is our turn. It should decide upon an action
        to perform and send this action to the opponent.

        @return: None.
        """
        # Check if the last received offer is good enough
        if self.accept_condition(self.last_received_bid):
            # If so, accept the offer
            action = Accept(self.me, self.last_received_bid)
        else:
            # If not, find a bid to propose as counter offer
            bid = self.find_bid()
            action = Offer(self.me, bid)

        # Send the action
        self.send_action(action)

    def save_data(self) -> None:
        """
        @brief: Saves data.

        This method is called after the negotiation is finished. It can be used to store data
        for learning capabilities. Note that no extensive calculations can be done within this method.
        Taking too much time might result in your agent being killed, so use it for storage only.

        @return: None.
        """
        data = "Data for learning (see README.md)"
        with open(f"{self.storage_dir}/data.md", "w") as f:
            f.write(data)

    def accept_condition(self, bid: Bid) -> bool:
        """
        @brief: Accept the given bid.

        @return: Boolean indicator if to accept/reject the bid.
        """
        if bid is None:
            return False

        # Progress of the negotiation session between 0 and 1 (1 is deadline)
        progress = self.progress.get(time() * 1000)

        acceptance_threshold = -np.exp(self.compromising_factor * progress)
        acceptance_threshold /= np.exp(self.compromising_factor) - 1  # scale to 1
        acceptance_threshold *= self.max_acceptance_threshold - self.min_acceptance_threshold
        acceptance_threshold += self.max_acceptance_threshold

        return self.profile.getUtility(bid) >= acceptance_threshold

    def find_bid(self) -> Bid:
        """
        @brief: Finds the bid.

        @return: The chosen bid.
        """
        # Compose a list of all possible bids
        domain = self.profile.getDomain()
        all_bids = AllBidsList(domain)

        best_bid_score = 0.0
        best_bid = None

        # Take X attempts to find a bid according to a heuristic score
        for _ in range(self.bids_to_consider):
            bid = all_bids.get(randint(0, all_bids.size() - 1))
            bid_score = self.score_bid(bid)
            if bid_score > best_bid_score:
                best_bid_score, best_bid = bid_score, bid
        if self.accept_condition(best_bid):
            return best_bid
        else:
            return self.optimal_bid

    def score_bid(self, bid: Bid, alpha: float = 0.95, eps: float = 0.1) -> float:
        """
        @brief: Calculate heuristic score for a bid.

        @param bid: Bid to score
        @param alpha: Trade-off factor between self interested and
                     altruistic behavior. Defaults to 0.95.
        @param eps: Time pressure factor, balances between conceding
                    and Boulware behavior over time. Defaults to 0.1.

        Returns:
            float: score
        """
        progress = self.progress.get(time() * 1000)

        our_utility = float(self.profile.getUtility(bid))

        time_pressure = 1.0 - progress ** (1 / eps)
        score = alpha * time_pressure * our_utility

        if self.opponent_model is not None:
            opponent_utility = self.opponent_model.get_predicted_utility(bid)
            opponent_score = (1.0 - alpha * time_pressure) * opponent_utility
            score += opponent_score

        return score
