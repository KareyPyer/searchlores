"""
Module de compatibilité V1 → V2.

Permet aux plugins V1 existants de continuer à fonctionner
dans le moteur V2 via un adaptateur.
"""
from searchlores.compat.v1_adapter import V1PluginWrapper

__all__ = ["V1PluginWrapper"]