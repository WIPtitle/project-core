import inspect

_bindings = {}


def bind(interface, instance):
    _bindings[interface] = instance


def resolve(interface):
    return _bindings[interface]


def inject(cls):
    """Decorator: resolve constructor args by type-hint from bindings."""
    original_init = cls.__init__
    sig = inspect.signature(original_init)
    params = list(sig.parameters.values())[1:]  # skip self

    def new_init(self, **kwargs):
        resolved = {}
        for p in params:
            if p.annotation != inspect.Parameter.empty and p.annotation in _bindings:
                resolved[p.name] = _bindings[p.annotation]
        resolved.update(kwargs)
        original_init(self, **resolved)

    cls.__init__ = new_init
    return cls


# --- Bootstrap all singletons ---
from app.database.impl.database_connector_impl import DatabaseConnectorImpl
from app.database.database_connector import DatabaseConnector
from app.clients.auth_client import AuthClient
from app.clients.valve_controller_client import ValveControllerClient
from app.repositories.impl.irrigation_repository_impl import IrrigationRepositoryImpl
from app.repositories.irrigation_repository import IrrigationRepository
from app.services.impl.irrigation_service_impl import IrrigationServiceImpl
from app.services.irrigation_service import IrrigationService
from app.utils.valve_status_manager import ValveStatusManager
from app.jobs.irrigation_scheduler import IrrigationScheduler

db = DatabaseConnectorImpl()
auth_client = AuthClient()
valve_client = ValveControllerClient()
repo = IrrigationRepositoryImpl(db)
service = IrrigationServiceImpl(repo, valve_client)
status_manager = ValveStatusManager(valve_client)
scheduler = IrrigationScheduler(repo, valve_client)

# Restore valve_client URL from DB if already configured
_vs = repo.get_valve_server()
if _vs:
    valve_client.set_url(_vs.url)

bind(DatabaseConnector, db)
bind(AuthClient, auth_client)
bind(ValveControllerClient, valve_client)
bind(IrrigationRepository, repo)
bind(IrrigationService, service)
bind(ValveStatusManager, status_manager)
