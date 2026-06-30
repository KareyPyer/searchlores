"""
Module des Observers V2.

Les observers remplacent les plugins V1 en produisant des
observations brutes (faits, citations, relations) au lieu
de conclusions directes.
"""
from searchlores.observers.base import Observation, Observer
from searchlores.observers.authority import AuthorityObserver
from searchlores.observers.contradictions import ContradictionObserver
from searchlores.observers.assumptions import AssumptionObserver

__all__ = [
    "Observation",
    "Observer",
    "AuthorityObserver",
    "ContradictionObserver",
    "AssumptionObserver",
]