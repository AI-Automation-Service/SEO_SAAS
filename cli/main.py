import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="seo-os",
    help="SEO Operating System — manage client SEO at scale.",
    no_args_is_help=True,
)
console = Console()


@app.command("list-projects")
def list_projects():
    """List all configured client projects."""
    from core.project import ProjectLoader
    from shared.exceptions import SEOOSError

    try:
        loader = ProjectLoader()
        projects = loader.list_projects()
    except SEOOSError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not projects:
        console.print("[yellow]No projects found in the projects/ directory.[/yellow]")
        raise typer.Exit()

    table = Table(title="Client Projects")
    table.add_column("Name", style="cyan")
    for p in projects:
        table.add_row(p)
    console.print(table)


@app.command("list-skills")
def list_skills():
    """List all available SEO skills."""
    from skills.base import SkillLoader

    loader = SkillLoader()
    skill_names = loader.list_skills()

    if not skill_names:
        console.print("[yellow]No skills found in the skills/ directory.[/yellow]")
        raise typer.Exit()

    table = Table(title="Available Skills")
    table.add_column("Skill", style="green")
    for s in skill_names:
        table.add_row(s)
    console.print(table)


@app.command("info")
def project_info(project: str = typer.Argument(..., help="Project name")):
    """Show configuration summary for a project."""
    from core.project import ProjectLoader
    from shared.exceptions import SEOOSError

    loader = ProjectLoader()
    try:
        config = loader.load(project)
    except SEOOSError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"\n[bold]{config.business_name}[/bold]")
    console.print(f"  Website   : {config.website}")
    console.print(f"  CMS       : {config.cms}")
    console.print(f"  Country   : {config.country}")
    console.print(f"  Language  : {config.language}")
    console.print(f"  Active    : {config.active}")
    console.print(f"  SEO Goals : {', '.join(config.seo_goals)}\n")


if __name__ == "__main__":
    app()
