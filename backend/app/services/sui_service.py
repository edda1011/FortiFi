import json
import subprocess

from app.config import settings


class SuiNotConfiguredError(RuntimeError):
    pass


class SuiSubmissionError(RuntimeError):
    pass


class SuiService:
    CLOCK_OBJECT = "0x6"

    def record(
        self,
        report_hash: str,
        base_wallet: str,
        signature: str,
        record_type: str,
        base_transaction: str = "",
    ) -> tuple[str, str | None]:
        if not settings.sui_package_id or not settings.sui_registry_id:
            raise SuiNotConfiguredError(
                "Sui recording is not configured. Publish the Move package and set "
                "SUI_PACKAGE_ID and SUI_REGISTRY_ID."
            )

        # EVM addresses are left-padded to Sui's 32-byte address representation.
        sui_wallet = "0x" + base_wallet.removeprefix("0x").zfill(64)
        command = [
            settings.sui_cli_path,
            "client", "call",
            "--package", settings.sui_package_id,
            "--module", "protection_policy",
            "--function", "create_record",
            "--args", settings.sui_registry_id, report_hash, sui_wallet,
            signature, "0x" + record_type.encode().hex(), base_transaction or "0x", self.CLOCK_OBJECT,
            "--gas-budget", str(settings.sui_gas_budget),
            "--json",
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, check=True, timeout=60
            )
            result = json.loads(completed.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise SuiNotConfiguredError("Sui CLI is not installed or available.") from exc
        except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            raise SuiSubmissionError(f"Sui transaction failed: {detail.strip()}") from exc

        digest = result.get("digest")
        if not digest:
            raise SuiSubmissionError("Sui CLI returned no transaction digest.")
        created = next(
            (
                change.get("objectId")
                for change in result.get("objectChanges", [])
                if change.get("type") == "created"
                and change.get("objectType", "").endswith("::ProtectionRecord")
            ),
            None,
        )
        return digest, created
