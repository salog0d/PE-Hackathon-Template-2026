from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.network import Nginx
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.logging import FluentBit
from diagrams.programming.framework import Flask
from diagrams.onprem.client import Users
from diagrams.generic.storage import Storage
from diagrams.onprem.ci import GithubActions

with Diagram(
    "URL Shortener Service — Architecture",
    filename="docs/architecture",
    outformat="png",
    show=False,
    direction="LR",
    graph_attr={"fontsize": "14", "pad": "0.5", "splines": "ortho"},
):
    clients = Users("Clients")

    with Cluster("Ingress"):
        lb = Nginx("Load Balancer\n(Nginx)")

    with Cluster("Application Layer"):
        with Cluster("Flask App"):
            api = Flask("REST API\n/users  /urls  /events")
            health = Server("Health Probes\n/health  /health/db")
            swagger = Server("Swagger UI\n/apidocs")
            seed_api = Server("Bulk Seed\n/seed/*")

        with Cluster("Middleware"):
            metrics_mw = Server("Metrics\nMiddleware")
            logging_mw = Server("Request Tracing\n(UUID + JSON logs)")

    with Cluster("Data Layer"):
        db = PostgreSQL("PostgreSQL 16\nhackathon_db")
        with Cluster("Repositories"):
            repo = Storage("User / URL / Event\nRepositories")
        with Cluster("Services"):
            svc = Server("Validation &\nBusiness Logic")

    with Cluster("Observability"):
        prometheus = Prometheus("Prometheus\n/metrics")
        grafana = Grafana("Grafana\nDashboards")
        logs = FluentBit("Stdout\nJSON Logs")

    with Cluster("CI / CD"):
        ci = GithubActions("GitHub Actions\nLint → Test → Deploy")

    # Request flow
    clients >> Edge(label="HTTPS") >> lb
    lb >> Edge(label="HTTP") >> api
    api >> metrics_mw >> logging_mw

    # App internals
    api >> svc >> repo >> db
    api >> health >> db
    api >> swagger
    api >> seed_api >> db

    # Observability
    metrics_mw >> Edge(label="scrape") >> prometheus
    prometheus >> grafana
    logging_mw >> Edge(label="stdout") >> logs

    # CI/CD
    ci >> Edge(label="deploy") >> api
