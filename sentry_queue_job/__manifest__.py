{
    "name": "Sentry - Queue Job Integration",
    "category": "OpenSPP",
    "version": "15.0.0.0.1",
    "sequence": 1,
    "author": "Newlogic",
    "website": "https://github.com/openspp/",
    "license": "LGPL-3",
    "development_status": "Alpha",
    "maintainers": ["jeremi", "gonzalesedwin1123"],
    "depends": [
        "sentry",
        "queue_job",
    ],
    "external_dependencies": {
        "python": [
            "sentry_sdk",
        ]
    },
    "application": False,
    "installable": True,
    "auto_install": True,
}
