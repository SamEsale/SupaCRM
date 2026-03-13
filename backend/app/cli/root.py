import typer

from app.cli.bootstrap import app as tenant_app
from app.cli.user import app as user_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(tenant_app, name="tenant")
app.add_typer(user_app, name="user")
