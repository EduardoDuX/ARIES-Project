"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or srcnstrate a feature.
"""

import asyncio
import json
from dataclasses import dataclass
from os import getenv
from secrets import token_hex

from acapy_controller import Controller
from acapy_controller.controller import Minimal
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import V20PresExRecord, V20PresExRecordList
from acapy_controller.protocols import (
    DIDResult,
    didexchange,
    indy_issue_credential_v2,
    indy_present_proof_v2,
    params,
)
from aiohttp import ClientSession

ALICE = getenv("ALICE", "http://eduardo:3001")
BOB = getenv("BOB", "http://bob:3001")


def summary(presentation: V20PresExRecord) -> str:
    """Summarize a presentation exchange record."""
    request = presentation.pres_request
    return "Summary: " + json.dumps(
        {
            "state": presentation.state,
            "verified": presentation.verified,
            "presentation_request": request.dict(by_alias=True) if request else None,
        },
        indent=2,
        sort_keys=True,
    )


@dataclass
class SchemaResult(Minimal):
    """Schema result."""

    schema_state: dict


@dataclass
class CredDefResult(Minimal):
    """Credential definition result."""

    credential_definition_state: dict


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as eduardo, Controller(base_url=BOB) as bob:
        # Connecting
        eduardo_conn, bob_conn = await didexchange(eduardo, bob)

        # Issuance prep
        config = (await eduardo.get("/status/config"))["config"]
        genesis_url = config.get("ledger.genesis_url")
        public_did = (await eduardo.get("/wallet/did/public", response=DIDResult)).result
        if not public_did:
            public_did = (
                await eduardo.post(
                    "/wallet/did/create",
                    json={"method": "sov", "options": {"key_type": "ed25519"}},
                    response=DIDResult,
                )
            ).result
            assert public_did

            async with ClientSession() as session:
                register_url = genesis_url.replace("/genesis", "/register")
                async with session.post(
                    register_url,
                    json={
                        "did": public_did.did,
                        "verkey": public_did.verkey,
                        "alias": None,
                        "role": "ENDORSER",
                    },
                ) as resp:
                    assert resp.ok

            await eduardo.post("/wallet/did/public", params=params(did=public_did.did))

        schema = await eduardo.post(
            "/anoncreds/schema",
            json={
                "schema": {
                    "name": "anoncreds-test-" + token_hex(8),
                    "version": "1.0",
                    "attrNames": ["firstname", "lastname"],
                    "issuerId": public_did.did,
                }
            },
            response=SchemaResult,
        )
        cred_def = await eduardo.post(
            "/anoncreds/credential-definition",
            json={
                "credential_definition": {
                    "issuerId": schema.schema_state["schema"]["issuerId"],
                    "schemaId": schema.schema_state["schema_id"],
                    "tag": token_hex(8),
                },
                "options": {
                    "revocation_registry_size": 2000,
                    "support_revocation": True,
                },
            },
            response=CredDefResult,
        )

        # Issue a credential
        eduardo_cred_ex, _ = await indy_issue_credential_v2(
            eduardo,
            bob,
            eduardo_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_state["credential_definition_id"],
            {"firstname": "Bob", "lastname": "Builder"},
        )

        # Present the the credential's attributes
        await indy_present_proof_v2(
            bob,
            eduardo,
            bob_conn.connection_id,
            eduardo_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )

        # Revoke credential
        await eduardo.post(
            url="/anoncreds/revocation/revoke",
            json={
                "connection_id": eduardo_conn.connection_id,
                "rev_reg_id": eduardo_cred_ex.indy.rev_reg_id,
                "cred_rev_id": eduardo_cred_ex.indy.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )

        await bob.record(topic="revocation-notification")

        # Request proof, no interval
        await indy_present_proof_v2(
            bob,
            eduardo,
            bob_conn.connection_id,
            eduardo_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [
                        {
                            "cred_def_id": cred_def.credential_definition_state[
                                "credential_definition_id"
                            ]
                        }
                    ],
                }
            ],
        )

        # Query presentations
        presentations = await eduardo.get(
            "/present-proof-2.0/records",
            response=V20PresExRecordList,
        )

        # Presentation summary
        for i, pres in enumerate(presentations.results):
            print(summary(pres))


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
