"""UNCTADstat integration is intentionally disabled until its OData contract is verified.

The previous implementation called placeholder URLs under unctad.org/api/v1, which are not
supported by the project handover. Do not silently fall back to those endpoints.
"""
class UNCTADIntegrationNotConfigured(RuntimeError):
    pass

async def fetch_unctad_data(*args, **kwargs):
    raise UNCTADIntegrationNotConfigured(
        "UNCTADstat ingestion is not enabled. Implement against the verified user-supplied "
        "OData endpoint and field mapping before exposing this source."
    )
