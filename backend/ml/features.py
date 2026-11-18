"""One feature contract shared by training, API explanations and live search.

Adapted from the supplied ml.zip. Reuses the planner's canonical extractor so
course counts do not divide elective credits by a semester credit cap, and OR
nodes are counted only while unsatisfied. No separate legacy curriculum model.
"""

from backend.astar.features import extract_state_features

FEATURE_NAMES = [
    "outstanding_credits",
    "outstanding_courses",
    "max_chain_depth",
    "parity_locked_count",
    "terms_remaining",
    "unsatisfied_disjunctions",
]
FEATURE_VERSION = "graphmind-six-features-v1"


def extract_features_vector(problem, placed, next_term):
    return extract_state_features(problem, placed, next_term)


def extract_features_dict(problem, placed, next_term):
    return dict(zip(FEATURE_NAMES, extract_features_vector(problem, placed, next_term)))
