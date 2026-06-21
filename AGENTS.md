# Developer Agent Guide for octoDNS Gandi Provider

This repository contains the Gandi LiveDNS provider for octoDNS. It enables planning, syncing, and applying DNS record states directly to Gandi's LiveDNS API.

> [!IMPORTANT]
> **Core Workflow and Guidelines**
>
> All agents working on this repository must read and follow the general instructions and workflow guidelines defined in the core octoDNS `AGENTS.md` file.
> - **Local check**: Look for the file at `../octodns/AGENTS.md`.
> - **Remote check**: If the local file is not available, fetch it from GitHub: [octoDNS Core AGENTS.md](https://github.com/octodns/octodns/raw/refs/heads/main/AGENTS.md).
>
> You must align your code structure, style, pull request guidelines, and overall development workflows with the instructions specified there.

## Repository & Module Information

### Key Components

- **Provider Class**: [GandiProvider](file:///home/ross/octodns/octodns-gandi/octodns_gandi/__init__.py#L155-L479) (defined in [octodns_gandi/__init__.py](file:///home/ross/octodns/octodns-gandi/octodns_gandi/__init__.py)). This is the primary provider orchestrating requests.
- **Client Class**: [GandiClient](file:///home/ross/octodns/octodns-gandi/octodns_gandi/__init__.py#L48-L153) wraps HTTP sessions to the Gandi LiveDNS API (`https://api.gandi.net/v5`), handling paginated domain and record fetches, authentication headers, and standard Gandi API error code conversions (400 BadRequest, 401 Unauthorized, 403 Forbidden, 404 NotFound).

### Key Workflows & Features

1. **Supported Record Types**: `A`, `AAAA`, `ALIAS`, `CAA`, `CNAME`, `DNAME`, `MX`, `NS`, `PTR`, `SRV`, `SSHFP`, `TLSA`, `TXT`.
2. **Authentication**: Uses bearer token authentication configured via the `token` argument.
3. **FQDN Normalization**: The provider automatically detects relative record targets (e.g. for `ALIAS`, `CNAME`, `DNAME`, `MX`, `NS`, `SRV` records) returned by Gandi's API and appends trailing dots and the zone name to absolute-normalize them for octoDNS.
4. **Dynamic Routing**: Not supported (`SUPPORTS_DYNAMIC=False`, `SUPPORTS_GEO=False`).
5. **Dynamic Subnets**: Not supported (`SUPPORTS_DYNAMIC_SUBNETS=False`).
6. **Pool Value Status**: Not supported (`SUPPORTS_POOL_VALUE_STATUS=False`).

## Development & Testing

- **Setup Script**: Run `./script/bootstrap` to create a virtual environment, install runtime and development dependencies (including `black`, `isort`, `pyflakes`, and `pytest`), and configure pre-commit hooks.
- **Test Suite**: Run unit tests using `pytest` via `./script/test` (or `pytest tests/`). Test files are located in [tests/](file:///home/ross/octodns/octodns-gandi/tests).
- **Code Coverage**: Verify code coverage using `./script/coverage`.

## Key Constraints & Behaviors

- **Python Version**: Targets Python `>=3.9`.
- **Formatting**: Code formatting is enforced via `black` (version `>=26.0.0,<27.0.0`) and `isort`.
