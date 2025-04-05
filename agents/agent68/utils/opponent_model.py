import math
from collections import defaultdict

from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.DiscreteValueSet import DiscreteValueSet
from geniusweb.issuevalue.Domain import Domain
from geniusweb.issuevalue.Value import Value


class OpponentModel:
    def __init__(self, domain: Domain):
        self.offers = []
        self.domain = domain

        self.issue_estimators = {
            i: IssueEstimator(v) for i, v in domain.getIssuesValues().items()
        }

    def update(self, bid: Bid):
        # to keep track of all bids received
        self.offers.append(bid)

        # calculating the weight that will be assigned to the current bid
        # based on the number of bids received so far
        decay_lambda = 0.2
        time_weight = math.exp(-decay_lambda * (len(self.offers) - 1))

        for issue_id, issue_estimator in self.issue_estimators.items():
            value = bid.getValue(issue_id)
            issue_estimator.update(value, time_weight)

    def get_predicted_utility(self, bid: Bid):
        if len(self.offers) == 0 or bid is None:
            return 0.0

        # calculate the total weight of all issues
        total_weight = sum(est.weight for est in self.issue_estimators.values())
        if total_weight == 0:
            total_weight = len(self.issue_estimators)

        predicted_utility = 0.0

        # go over each issue to calculate the overall weighted utility
        for issue_id, issue_estimator in self.issue_estimators.items():
            value = bid.getValue(issue_id)
            issue_weight = issue_estimator.weight / total_weight
            value_utility = issue_estimator.get_value_utility(value)
            predicted_utility += issue_weight * value_utility

        return predicted_utility


class IssueEstimator:
    def __init__(self, value_set: DiscreteValueSet):
        if not isinstance(value_set, DiscreteValueSet):
            raise TypeError("This issue estimator only supports discrete value sets")

        self.bids_received = 0  # the number of times this issue has been updated
        self.num_values = value_set.size()  # the total number of values for current issue
        self.value_trackers = defaultdict(ValueEstimator)  # we have one estimator per value
        self.weight = 0  # how important this issue seems to be

    def update(self, value: Value, time_weight: float):
        self.bids_received += 1

        # update the weighted count of the given issue value
        self.value_trackers[value].update(time_weight)

        # get the total weight of all values for this issue
        total_weighted = sum(vt.weighted_count for vt in self.value_trackers.values())

        # recalculate the utilities of all values with the new total weight
        for vt in self.value_trackers.values():
            vt.recalculate_utility(total_weighted)

        # this issue is more important if one value persists (the opponent does not concede easily)
        if total_weighted > 0:
            max_count = max(vt.weighted_count for vt in self.value_trackers.values())
            self.weight = max_count / total_weighted
        else:
            self.weight = 0

    def get_value_utility(self, value: Value):
        if value in self.value_trackers: return self.value_trackers[value].utility 
        else: return 0


class ValueEstimator:
    def __init__(self):
        self.weighted_count = 0
        self.utility = 0

    def update(self, time_weight: float):
        self.weighted_count += time_weight

    def recalculate_utility(self, total_weighted_bids: float):
        if total_weighted_bids > 0: self.utility = self.weighted_count / total_weighted_bids
        else: self.utility = 0
