## Gandi v5 API provider for octoDNS

An [octoDNS](https://github.com/octodns/octodns/) provider that targets [Gandi](https://docs.gandi.net/en/domain_names/common_operations/dns_records.html).

### Installation

#### Command line

```
pip install octodns-gandi
```

#### requirements.txt/setup.py

Pinning specific versions or SHAs is recommended to avoid unplanned upgrades.

##### Versions

```
# Start with the latest versions and don't just copy what's here
octodns==0.9.14
octodns-gandi==0.0.1
```

##### SHAs

```
# Start with the latest/specific versions and don't just copy what's here
-e git+https://git@github.com/octodns/octodns.git@9da19749e28f68407a1c246dfdf65663cdc1c422#egg=octodns
-e git+https://git@github.com/octodns/octodns-gandi.git@ec9661f8b335241ae4746eea467a8509205e6a30#egg=octodns_gandi
```

### Configuration

```yaml
providers:
  gandi:
    class: octodns_gandi.GandiProvider
    # Your API key (required)
    token: env/GANDI_TOKEN
```

### Support Information

#### Records

GandiProvider suports AAAA, ALIAS, CAA, CNAME, DNAME, MX, NS, PTR, SPF, SRV, SSHFP, and TXT

#### Dynamic

GandiProvider does not support dynamic records.

### Development

See the [/script/](/script/) directory for some tools to help with the development process. They generally follow the [Script to rule them all](https://github.com/github/scripts-to-rule-them-all) pattern. Most useful is `./script/bootstrap` which will create a venv and install both the runtime and development related requirements. It will also hook up a pre-commit hook that covers most of what's run by CI.
