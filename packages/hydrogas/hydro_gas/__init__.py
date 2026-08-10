"""Fondations scientifiques du domaine gaz PETROLE.

Le paquet est volontairement séparé de ``hydroliquid`` : un réseau gaz ne doit
pas être modélisé en remplaçant simplement la densité d'un liquide.
"""

from hydro_gas.properties import GasState, gas_density_from_z, linepack_mass

__all__ = ["GasState", "gas_density_from_z", "linepack_mass"]
