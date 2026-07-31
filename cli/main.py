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
    console.print(f"  Website      : {config.website}")
    console.print(f"  CMS          : {config.cms}")
    console.print(f"  SEO Plugin   : {config.seo_plugin or 'none'}")
    console.print(f"  Image Source : {config.image_source}")
    console.print(f"  Country      : {config.country}")
    console.print(f"  Language     : {config.language}")
    console.print(f"  Active       : {config.active}")
    console.print(f"  SEO Goals    : {', '.join(config.seo_goals)}\n")


@app.command("add-project")
def add_project(name: str = typer.Argument(..., help="Project slug (lowercase, hyphens)")):
    """Scaffold a new client project with all required folders and template files."""
    from core.config import load_config
    from core.scaffold import ProjectScaffolder
    from shared.exceptions import SEOOSError

    if not name.replace("-", "").isalnum():
        console.print("[red]Error:[/red] Project name must be lowercase letters, numbers, and hyphens only.")
        raise typer.Exit(1)

    try:
        config = load_config()
        scaffolder = ProjectScaffolder(config.projects_dir)
        project_dir = scaffolder.scaffold(name)
    except SEOOSError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"\n[green]Project '{name}' created at {project_dir}[/green]")
    console.print("Next steps:")
    console.print(f"  1. Edit [cyan]projects/{name}/config/project.yaml[/cyan] with client details")
    console.print(f"  2. Fill in [cyan]projects/{name}/knowledge/*.md[/cyan] with client knowledge")
    console.print(f"  3. Add secrets to [cyan].env[/cyan] using the key names in project.yaml")
    console.print(f"  4. Run [cyan]seo-os validate-project {name}[/cyan] to check config\n")


@app.command("validate-project")
def validate_project(name: str = typer.Argument(..., help="Project name to validate")):
    """Validate a project's configuration and report any issues."""
    from core.project import ProjectLoader
    from core.validation import validate_config
    from shared.exceptions import ProjectNotFoundError, ProjectConfigError

    loader = ProjectLoader()

    try:
        config = loader.load(name)
    except ProjectNotFoundError as e:
        console.print(f"[red]Not found:[/red] {e}")
        raise typer.Exit(1)
    except ProjectConfigError as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(1)

    report = validate_config(name, config)
    errors = report.errors
    warnings = report.warnings

    if errors:
        console.print(f"\n[red]INVALID[/red] — {name}\n")
        for e in errors:
            console.print(f"  [red]✗[/red] {e}")
    else:
        console.print(f"\n[green]VALID[/green] — {name}\n")

    if warnings:
        console.print("  Warnings:")
        for w in warnings:
            console.print(f"  [yellow]⚠[/yellow]  {w}")
    else:
        console.print("  [green]No warnings.[/green]")

    console.print()


if __name__ == "__main__":
    app()
