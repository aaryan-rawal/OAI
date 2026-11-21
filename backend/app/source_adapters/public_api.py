"""Placeholder guard for public freight APIs; no verified listing API is configured."""
class PublicCargoAPIUnavailable(RuntimeError):
    pass

class UNCTADPublicAPI:
    def fetch(self, request):
        raise PublicCargoAPIUnavailable(
            "UNCTAD transport-cost indicators are not freight cargo listings. A verified API "
            "contract and mapping are required before this adapter can be enabled."
        )
